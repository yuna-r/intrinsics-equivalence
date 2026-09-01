"""Deterministic generation of canonical input artifacts."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterator

from .canonical import JSONValue, atomic_write, dump_bytes, remove_completion_marker, write_jsonl
from .cases import CaseDefinition, CaseRegistry, resolve_case_registry
from .errors import ValidationError
from .isa import ISARegistry, UsedISAContract, project_used_isa
from .records import derive_input_id, validate_input_record


DEFAULT_SEED = "0x6a09e667f3bcc909"
PROFILE_COUNTS = {"smoke": 32, "standard": 1_000, "exhaustive-small": 256, "stress": 100_000}
MASK64 = (1 << 64) - 1


@dataclass(frozen=True)
class GenerateResult:
    output_directory: Path
    vectors_path: Path
    manifest_path: Path
    record_count: int
    sha256: str
    case_definitions_sha256: str
    used_isa_contract: UsedISAContract


class SplitMix64:
    def __init__(self, seed: int):
        self.state = seed & MASK64

    def next(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return (value ^ (value >> 31)) & MASK64


def _bits(value: int, digits: int) -> str:
    return f"0x{value:0{digits}x}"


def _vector(element: str, values: tuple[int, ...]) -> dict[str, JSONValue]:
    digits = {"f64": 16, "i32": 8}[element]
    return {"element": element, "lanes": [_bits(value, digits) for value in values]}


def _scalar(element: str, value: int) -> dict[str, JSONValue]:
    return {"bits": _bits(value, {"f64": 16}[element]), "element": element}


F64_BOUNDARY = (
    0x0000000000000000,
    0x8000000000000000,
    0x0000000000000001,
    0x8000000000000001,
    0x000FFFFFFFFFFFFF,
    0x800FFFFFFFFFFFFF,
    0x0010000000000000,
    0x8010000000000000,
    0x7FEFFFFFFFFFFFFF,
    0xFFEFFFFFFFFFFFFF,
    0x7FF0000000000000,
    0xFFF0000000000000,
    0x7FF8000000000001,
    0x7FF0000000000001,
    0x3FF0000000000000,
    0xBFF0000000000000,
    0x4000000000000000,
    0x4024000000000000,
    0x4034000000000000,
    0x3FEFFFFFFFFFFFFF,
)


def _rounding_modes(case: CaseDefinition) -> list[str]:
    modes = case.environment["fp_rounding_modes"]
    assert isinstance(modes, list)
    return [str(mode) for mode in modes]


def _random_finite_bits(generator: SplitMix64) -> int:
    value = generator.next()
    if ((value >> 52) & 0x7FF) == 0x7FF:
        value ^= 1 << 52
    return value


def _candidate_records(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    seed = int(seed_text, 16)
    random = SplitMix64(seed)
    modes = _rounding_modes(case)
    random_generation: dict[str, JSONValue] = {
        "algorithm": "splitmix64",
        "class": "random",
        "seed": seed_text,
    }
    if case.id == "sse2.add.f64x2.default":
        structured = (
            ((0x3FF0000000000000, 0x4024000000000000), (0x4000000000000000, 0x4034000000000000), "structured"),
            ((0, 0x8000000000000000), (0, 0), "boundary"),
            ((0x0000000000000001, 0x000FFFFFFFFFFFFF), (0, 0), "boundary"),
            ((0x0010000000000000, 0x7FEFFFFFFFFFFFFF), (0, 0), "boundary"),
            ((0x7FF0000000000000, 0xFFF0000000000000), (0x3FF0000000000000, 0xBFF0000000000000), "boundary"),
            ((0x7FF8000000000001, 0x7FF0000000000001), (0x3FF0000000000000, 0x3FF0000000000000), "boundary"),
            ((0x7FEFFFFFFFFFFFFF, 0x7FEFFFFFFFFFFFFF), (0x7FEFFFFFFFFFFFFF, 0x7FEFFFFFFFFFFFFF), "boundary"),
            ((0x3FF0000000000000, 0x3FF0000000000000), (0x3CA8000000000000, 0x3CA8000000000000), "boundary"),
            ((0x8000000000000001, 0x800FFFFFFFFFFFFF), (0x8000000000000000, 0x8000000000000000), "boundary"),
            ((0x8010000000000000, 0xFFEFFFFFFFFFFFFF), (0x8000000000000000, 0x8000000000000000), "boundary"),
        )
        for index, (a, b, generation_class) in enumerate(structured):
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
                "generation": {"class": generation_class},
                "operands": {"a": _vector("f64", a), "b": _vector("f64", b)},
            }
        while True:
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
                "generation": dict(random_generation),
                "operands": {
                    "a": _vector("f64", (_random_finite_bits(random), _random_finite_bits(random))),
                    "b": _vector("f64", (_random_finite_bits(random), _random_finite_bits(random))),
                },
            }
    elif case.id == "sse2.set1.f64x2.default":
        for index, value in enumerate(F64_BOUNDARY):
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
                "generation": {"class": "boundary"},
                "operands": {"value": _scalar("f64", value)},
            }
        while True:
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
                "generation": dict(random_generation),
                "operands": {"value": _scalar("f64", random.next())},
            }
    elif case.id == "sse2.shuffle.i32x4.imm8":
        definitions = case.data["immediates"]
        assert isinstance(definitions, dict)
        definition = definitions["imm8"]
        assert isinstance(definition, dict)
        allowed = definition["values"]
        assert isinstance(allowed, list)
        patterns = (
            (0, 1, 2, 3),
            (0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210),
            (0xFFFFFFFF, 0, 0x80000000, 0x7FFFFFFF),
            (0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
        )
        for immediate in allowed:
            for pattern in patterns:
                yield {
                    "environment": {"fp_mode": "ieee", "rounding": modes[0]},
                    "generation": {"class": "structured"},
                    "immediates": {"imm8": int(immediate)},
                    "operands": {"a": _vector("i32", pattern)},
                }
        while True:
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
                "generation": dict(random_generation),
                "immediates": {"imm8": int(allowed[random.next() % len(allowed)])},
                "operands": {
                    "a": _vector("i32", tuple(random.next() & 0xFFFFFFFF for _ in range(4)))
                },
            }
    else:
        raise ValidationError(f"generator has no implementation for case {case.id!r}")


def _all_records(
    registry: CaseRegistry, *, count_per_case: int, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    sequence = 0
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
            mode for mode in _rounding_modes(case) if mode != "nearest_even"
        }
        missing_modes = required_regression_modes - found_regression_modes
        if missing_modes:
            raise ValidationError(
                f"generator did not materialize rounding witnesses for {case.id}: "
                + ", ".join(sorted(missing_modes))
            )


def generate_artifact(
    *,
    cases: str | Path | CaseRegistry,
    isa_registry: ISARegistry,
    output: str | Path,
    profile: str = "smoke",
    count_per_case: int | None = None,
    seed: str = DEFAULT_SEED,
) -> GenerateResult:
    registry = resolve_case_registry(cases, isa_registry=isa_registry)
    if profile not in PROFILE_COUNTS:
        raise ValidationError(f"unsupported profile: {profile}")
    if not re.fullmatch(r"0x[0-9a-f]{16}", seed):
        raise ValidationError("seed must be 0x followed by 16 lowercase hex digits")
    count = PROFILE_COUNTS[profile] if count_per_case is None else count_per_case
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1_000_000:
        raise ValidationError("count_per_case must be from 1 through 1000000")
    if profile == "standard" and count < len(F64_BOUNDARY):
        raise ValidationError(
            f"standard profile requires at least {len(F64_BOUNDARY)} records per case "
            "for mandatory boundaries"
        )
    used = project_used_isa(isa_registry, registry)
    output_directory = Path(output)
    output_directory.mkdir(parents=True, exist_ok=True)
    vectors_path = output_directory / "test-vectors.jsonl"
    manifest_path = output_directory / "test-vectors.manifest.json"
    contracts = output_directory / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    remove_completion_marker(manifest_path)
    record_count, byte_length, vectors_sha = write_jsonl(
        vectors_path,
        _all_records(registry, count_per_case=count, seed_text=seed),
    )
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
    )
