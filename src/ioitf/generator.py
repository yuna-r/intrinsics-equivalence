"""Deterministic generation of canonical input artifacts."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import copy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import TYPE_CHECKING, Callable, Iterable, Iterator

from .canonical import (
    JSONValue,
    atomic_write,
    dump_bytes,
    remove_completion_marker,
    utf16_sort_key,
    write_jsonl,
)
from .cases import CaseDefinition, CaseRegistry, resolve_case_registry
from .development import SplitMix64, load_development_case, rounding_modes
from .errors import ValidationError
from .isa import ISARegistry, UsedISAContract, project_used_isa
from .records import derive_input_id, validate_input_record

if TYPE_CHECKING:
    from .artifacts import InputArtifact


DEFAULT_SEED = "0x6a09e667f3bcc909"
PROFILE_COUNTS = {"smoke": 32, "standard": 1_000, "exhaustive-small": 256, "stress": 100_000}


@dataclass(frozen=True)
class GenerateResult:
    output_directory: Path
    vectors_path: Path
    manifest_path: Path
    record_count: int
    sha256: str
    case_definitions_sha256: str
    used_isa_contract: UsedISAContract
    manifest: dict[str, JSONValue]
    records: tuple[dict[str, JSONValue], ...] | None = None

    def as_validated_artifact(self) -> InputArtifact:
        """Return records already validated while this artifact was generated."""

        from .artifacts import InputArtifact

        if self.records is None:
            raise ValidationError("generated records were not retained")
        case_ids = tuple(
            sorted(
                {str(record["case_id"]) for record in self.records},
                key=utf16_sort_key,
            )
        )
        return InputArtifact(
            manifest_path=self.manifest_path,
            vectors_path=self.vectors_path,
            manifest=self.manifest,
            records=self.records,
            record_count=self.record_count,
            sha256=self.sha256,
            case_ids=case_ids,
            case_definitions_sha256=self.case_definitions_sha256,
            used_isa_contract=self.used_isa_contract,
            isa_registry_matches_local=True,
        )


def _candidate_records(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    yield from load_development_case(case).candidates(case, seed_text=seed_text)


def _all_records(
    registry: Iterable[CaseDefinition],
    *,
    count_per_case: int,
    seed_text: str,
    sequence_start: int = 0,
) -> Iterator[dict[str, JSONValue]]:
    sequence = sequence_start
    seen: set[str] = set()
    for case in registry:
        raw_regressions = case.data.get("regressions", {})
        assert isinstance(raw_regressions, dict)
        regression_by_input: dict[str, str] = {}
        for regression_id, raw_regression in raw_regressions.items():
            assert isinstance(raw_regression, dict)
            regression_by_input[str(raw_regression["input_id"])] = regression_id
        found_regressions: set[str] = set()
        found_regression_modes: set[str] = set()
        emitted = 0

        def materialize(
            candidate: dict[str, JSONValue],
        ) -> dict[str, JSONValue]:
            record: dict[str, JSONValue] = {
                "case_id": case.id,
                "environment": candidate["environment"],
                "generation": candidate["generation"],
                "operands": candidate["operands"],
                "schema_version": 1,
                "sequence": 1,
            }
            if "immediates" in candidate:
                record["immediates"] = candidate["immediates"]
            record["input_id"] = derive_input_id(record)
            regression_id = regression_by_input.get(str(record["input_id"]))
            if regression_id is not None:
                record["generation"] = {
                    "class": "regression",
                    "regression_id": regression_id,
                }
                found_regressions.add(regression_id)
                environment = record["environment"]
                assert isinstance(environment, dict)
                found_regression_modes.add(str(environment["rounding"]))
            return record

        for candidate in _candidate_records(case, seed_text=seed_text):
            record = materialize(candidate)
            input_id = str(record["input_id"])
            if input_id in seen:
                continue

            pending = [record]
            generation = record["generation"]
            environment = record["environment"]
            assert isinstance(generation, dict) and isinstance(environment, dict)
            if (
                generation["class"] == "regression"
                and environment["rounding"] != "nearest_even"
            ):
                nearest_candidate = copy.deepcopy(candidate)
                nearest_environment = nearest_candidate["environment"]
                assert isinstance(nearest_environment, dict)
                nearest_environment["rounding"] = "nearest_even"
                nearest_record = materialize(nearest_candidate)
                nearest_id = str(nearest_record["input_id"])
                if nearest_id != input_id and nearest_id not in seen:
                    pending.append(nearest_record)

            unique_pending: list[dict[str, JSONValue]] = []
            pending_ids: set[str] = set()
            for pending_record in pending:
                pending_id = str(pending_record["input_id"])
                if pending_id not in seen and pending_id not in pending_ids:
                    pending_ids.add(pending_id)
                    unique_pending.append(pending_record)
            if emitted + len(unique_pending) > count_per_case:
                raise ValidationError(
                    f"count_per_case is too small to include the nearest-even pair "
                    f"for a rounding witness in {case.id}"
                )
            for pending_record in unique_pending:
                pending_id = str(pending_record["input_id"])
                seen.add(pending_id)
                sequence += 1
                pending_record["sequence"] = sequence
                validate_input_record(
                    pending_record, case, expected_sequence=sequence
                )
                yield pending_record
                emitted += 1
            if emitted == count_per_case:
                break
        missing_regressions = set(raw_regressions) - found_regressions
        if missing_regressions:
            raise ValidationError(
                f"generator did not materialize mandatory regressions for {case.id}: "
                + ", ".join(sorted(missing_regressions))
            )
        required_regression_modes = {
            mode for mode in rounding_modes(case) if mode != "nearest_even"
        }
        missing_modes = required_regression_modes - found_regression_modes
        if missing_modes:
            raise ValidationError(
                f"generator did not materialize rounding witnesses for {case.id}: "
                + ", ".join(sorted(missing_modes))
            )


def _case_record_batch(
    work: tuple[CaseDefinition, int, str, int],
) -> list[dict[str, JSONValue]]:
    case, count_per_case, seed_text, sequence_start = work
    return list(
        _all_records(
            (case,),
            count_per_case=count_per_case,
            seed_text=seed_text,
            sequence_start=sequence_start,
        )
    )


def _parallel_records(
    registry: CaseRegistry,
    *,
    count_per_case: int,
    seed_text: str,
    jobs: int,
    progress: Callable[[int], None] | None,
) -> list[dict[str, JSONValue]]:
    work = [
        (case, count_per_case, seed_text, index * count_per_case)
        for index, case in enumerate(registry)
    ]
    ordered: list[list[dict[str, JSONValue]] | None] = [None] * len(work)
    completed_records = 0
    with ProcessPoolExecutor(max_workers=min(jobs, len(work))) as executor:
        pending = {
            executor.submit(_case_record_batch, batch): index
            for index, batch in enumerate(work)
        }
        for future in as_completed(pending):
            batch = future.result()
            ordered[pending[future]] = batch
            completed_records += len(batch)
            if progress is not None:
                progress(completed_records)

    return [
        record
        for batch in ordered
        if batch is not None
        for record in batch
    ]


def _records_with_progress(
    records: Iterator[dict[str, JSONValue]], progress: Callable[[int], None]
) -> Iterator[dict[str, JSONValue]]:
    for count, record in enumerate(records, 1):
        yield record
        progress(count)


def generate_artifact(
    *,
    cases: str | Path | CaseRegistry,
    isa_registry: ISARegistry,
    output: str | Path,
    profile: str = "smoke",
    count_per_case: int | None = None,
    seed: str = DEFAULT_SEED,
    jobs: int = 1,
    progress: Callable[[int], None] | None = None,
    retain_records: bool = False,
) -> GenerateResult:
    registry = resolve_case_registry(cases, isa_registry=isa_registry)
    if profile not in PROFILE_COUNTS:
        raise ValidationError(f"unsupported profile: {profile}")
    if not re.fullmatch(r"0x[0-9a-f]{16}", seed):
        raise ValidationError("seed must be 0x followed by 16 lowercase hex digits")
    count = PROFILE_COUNTS[profile] if count_per_case is None else count_per_case
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1_000_000:
        raise ValidationError("count_per_case must be from 1 through 1000000")
    if jobs < 1:
        raise ValidationError("generator jobs must be at least 1")
    for case in registry:
        minimum = load_development_case(case).minimum_counts.get(profile, 1)
        if count < minimum:
            raise ValidationError(
                f"{profile} profile requires at least {minimum} records for {case.id}"
            )
    used = project_used_isa(isa_registry, registry)
    output_directory = Path(output)
    output_directory.mkdir(parents=True, exist_ok=True)
    vectors_path = output_directory / "test-vectors.jsonl"
    manifest_path = output_directory / "test-vectors.manifest.json"
    contracts = output_directory / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    remove_completion_marker(manifest_path)
    retained: list[dict[str, JSONValue]] | None = None
    if jobs > 1 and len(registry) > 1:
        retained = _parallel_records(
            registry,
            count_per_case=count,
            seed_text=seed,
            jobs=jobs,
            progress=progress,
        )
        records: Iterator[dict[str, JSONValue]] | list[dict[str, JSONValue]] = retained
    else:
        serial_records = _all_records(
            registry, count_per_case=count, seed_text=seed
        )
        if progress is not None:
            serial_records = _records_with_progress(serial_records, progress)
        if retain_records:
            retained = list(serial_records)
            records = retained
        else:
            records = serial_records
    record_count, byte_length, vectors_sha = write_jsonl(vectors_path, records)
    if record_count != len(registry) * count:
        raise ValidationError("generator did not produce the requested unique inputs")
    case_sha = registry.projected_sha256(set(registry.ids))
    atomic_write(
        contracts / "case-definitions.json",
        dump_bytes(registry.projected_data(set(registry.ids)), newline=True),
    )
    atomic_write(contracts / "isa-used.json", dump_bytes(used.data, newline=True))
    manifest: dict[str, JSONValue] = {
        "artifact_type": "ioitf.test-vectors",
        "case_definitions_sha256": case_sha,
        "complete": True,
        "isa_registry_sha256": isa_registry.sha256,
        "profile": profile,
        "schema_version": 1,
        "test_vectors": {
            "byte_length": byte_length,
            "file": "test-vectors.jsonl",
            "record_count": record_count,
            "sha256": vectors_sha,
        },
        "used_isa_contract_sha256": used.sha256,
    }
    atomic_write(manifest_path, dump_bytes(manifest, newline=True))
    return GenerateResult(
        output_directory,
        vectors_path,
        manifest_path,
        record_count,
        vectors_sha,
        case_sha,
        used,
        manifest,
        tuple(retained) if retain_records and retained is not None else None,
    )
