"""Strict failure-bundle loading and replay-result verification.

The verifier deliberately consumes the contracts embedded in a failure
bundle.  A full local ISA registry is not a hard gate here: the bundle's used
ISA projection contains exactly the vocabulary needed to validate its single
case, while the full registry hashes remain provenance diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
import stat
import tempfile
from typing import Iterator

from .artifacts import (
    ABI_VERSION,
    InputArtifact,
    ResultArtifact,
    validate_input_artifact,
    validate_result_artifact,
)
from .canonical import (
    JSONValue,
    dump_bytes,
    loads,
    require_exact_keys,
    require_int,
    require_object,
    require_string,
    sha256_bytes,
    utf16_sort_key,
)
from .cases import CaseRegistry, load_case_definitions
from .compare import compare_result_records
from .errors import ValidationError
from .isa import (
    ISARegistry,
    UsedISAContract,
    validate_isa_registry,
    validate_used_isa_contract,
)
from .records import require_sha256


_FAILURE_KEYS = {
    "abi_version",
    "artifact_type",
    "baseline",
    "case_definitions_sha256",
    "case_id",
    "comparison",
    "contracts",
    "first_difference",
    "input_id",
    "mismatch_count",
    "reproduce",
    "schema_version",
    "source_artifacts",
    "test_vectors_manifest",
    "used_isa_contract_sha256",
}
_SOURCE_KEYS = (
    "case_definitions_sha256",
    "input_isa_registry_sha256",
    "input_sha256",
    "intel_isa_registry_sha256",
    "intel_results_sha256",
    "openpower_isa_registry_sha256",
    "openpower_results_sha256",
    "used_isa_contract_sha256",
)
_FIXED_PATHS = {
    "test_vectors_manifest": "test-vectors.manifest.json",
    "intel_manifest": "baseline/intel/intel-results.manifest.json",
    "openpower_manifest": "baseline/openpower/power-results.manifest.json",
    "case_definitions": "contracts/case-definitions.json",
    "used_isa": "contracts/isa-used.json",
}
_REPRODUCE: dict[str, list[JSONValue]] = {
    "intel": [
        "ioitf", "replay", "--failure", "failure.json", "--role", "intel",
        "--output", "replay/intel",
    ],
    "openpower": [
        "ioitf", "replay", "--failure", "failure.json", "--role", "openpower",
        "--output", "replay/openpower",
    ],
    "verify": [
        "ioitf", "verify-replay", "--failure", "failure.json", "--intel",
        "replay/intel/intel-results.manifest.json", "--openpower",
        "replay/openpower/power-results.manifest.json",
    ],
}
_BUNDLE_MEMBERS = (
    "test-vectors.manifest.json",
    "test-vectors.jsonl",
    "contracts/case-definitions.json",
    "contracts/isa-used.json",
    "baseline/intel/intel-results.manifest.json",
    "baseline/intel/intel-results.jsonl",
    "baseline/openpower/power-results.manifest.json",
    "baseline/openpower/power-results.jsonl",
)


@dataclass(frozen=True)
class FailureBundle:
    """A completely validated, self-contained single-input failure bundle."""

    root: Path
    failure_path: Path
    failure: dict[str, JSONValue]
    cases: CaseRegistry
    isa_registry: ISARegistry
    used_isa_contract: UsedISAContract
    input_artifact: InputArtifact
    baseline_intel: ResultArtifact
    baseline_openpower: ResultArtifact


@dataclass(frozen=True)
class ReplayVerification:
    """Deterministic comparison of two replay artifacts with their baselines."""

    reproduced: bool
    environment_differences: dict[str, list[JSONValue]]
    result_differences: list[JSONValue]
    replay_comparison: dict[str, JSONValue]


def _read_canonical_value(raw: bytes, *, source: str) -> JSONValue:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n") or b"\r" in raw:
        raise ValidationError(f"{source}: canonical JSON must have exactly one final LF")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValidationError(f"{source}: UTF-8 BOM is not allowed")
    try:
        value = loads(raw[:-1].decode("utf-8"), source=source)
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{source}: file is not valid UTF-8") from exc
    if dump_bytes(value, newline=True) != raw:
        raise ValidationError(f"{source}: JSON is not in canonical form")
    return value


def _failure_path(value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_dir():
        candidate = candidate / "failure.json"
    if candidate.name != "failure.json":
        raise ValidationError("failure bundle marker must be named failure.json")
    return candidate


def _snapshot_bundle_files(root: Path, relatives: tuple[str, ...]) -> dict[str, bytes]:
    """Read regular bundle files once, without following member symlinks."""

    if os.open not in os.supports_dir_fd or not hasattr(os, "O_NOFOLLOW"):
        return _portable_snapshot_bundle_files(root, relatives)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    nofollow = os.O_NOFOLLOW
    try:
        root_descriptor = os.open(root, directory_flags)
    except OSError as exc:
        raise ValidationError(f"cannot open failure bundle directory {root}: {exc}") from exc

    snapshots: dict[str, bytes] = {}
    try:
        for relative in relatives:
            components = relative.split("/")
            directory_descriptor = os.dup(root_descriptor)
            try:
                for component in components[:-1]:
                    next_descriptor = os.open(
                        component,
                        directory_flags | nofollow,
                        dir_fd=directory_descriptor,
                    )
                    os.close(directory_descriptor)
                    directory_descriptor = next_descriptor
                file_descriptor = os.open(
                    components[-1],
                    os.O_RDONLY | os.O_NONBLOCK | nofollow,
                    dir_fd=directory_descriptor,
                )
                try:
                    if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
                        raise ValidationError(
                            f"bundle member is not a regular file: {relative}"
                        )
                    with os.fdopen(file_descriptor, "rb", closefd=False) as stream:
                        snapshots[relative] = stream.read()
                finally:
                    os.close(file_descriptor)
            except OSError as exc:
                raise ValidationError(
                    f"cannot read bundle member {relative}: {exc}"
                ) from exc
            finally:
                os.close(directory_descriptor)
    finally:
        os.close(root_descriptor)
    return snapshots


def _portable_snapshot_bundle_files(
    root: Path, relatives: tuple[str, ...]
) -> dict[str, bytes]:
    """Best-effort fallback for platforms without POSIX ``openat`` support."""

    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"cannot open failure bundle directory {root}: {exc}") from exc
    snapshots: dict[str, bytes] = {}
    for relative in relatives:
        candidate = root.joinpath(*relative.split("/"))
        current = root
        for component in relative.split("/"):
            current = current / component
            if current.is_symlink():
                raise ValidationError(
                    f"bundle path must not use symbolic links: {relative}"
                )
        try:
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
                raise ValidationError(f"invalid regular bundle member: {relative}")
            snapshots[relative] = resolved.read_bytes()
        except OSError as exc:
            raise ValidationError(f"cannot read bundle member {relative}: {exc}") from exc
    return snapshots


def _write_snapshot(root: Path, files: dict[str, bytes]) -> None:
    for relative, data in files.items():
        destination = root.joinpath(*relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)


def _validate_contract_reference(
    value: JSONValue,
    *,
    location: str,
    expected_file: str,
) -> tuple[str, str]:
    reference = require_object(value, location)
    require_exact_keys(reference, {"file", "sha256"}, location=location)
    file_name = require_string(reference["file"], f"{location}.file")
    if file_name != expected_file:
        raise ValidationError(f"{location}.file: expected {expected_file!r}")
    return file_name, require_sha256(reference["sha256"], f"{location}.sha256")


def _validate_failure_shape(value: JSONValue, *, location: str) -> dict[str, JSONValue]:
    failure = require_object(value, location)
    require_exact_keys(failure, _FAILURE_KEYS, location=location)
    if failure["artifact_type"] != "ioitf.failure":
        raise ValidationError(f"{location}.artifact_type: expected ioitf.failure")
    if require_int(failure["schema_version"], f"{location}.schema_version") != 1:
        raise ValidationError(f"{location}.schema_version: only version 1 is supported")
    if require_int(failure["abi_version"], f"{location}.abi_version") != ABI_VERSION:
        raise ValidationError(f"{location}.abi_version: expected {ABI_VERSION}")
    require_string(failure["case_id"], f"{location}.case_id")
    require_sha256(failure["input_id"], f"{location}.input_id")
    require_sha256(
        failure["case_definitions_sha256"],
        f"{location}.case_definitions_sha256",
    )
    require_sha256(
        failure["used_isa_contract_sha256"],
        f"{location}.used_isa_contract_sha256",
    )
    require_int(failure["mismatch_count"], f"{location}.mismatch_count", minimum=1)
    require_object(failure["comparison"], f"{location}.comparison")
    require_object(failure["first_difference"], f"{location}.first_difference")

    baseline = require_object(failure["baseline"], f"{location}.baseline")
    require_exact_keys(
        baseline,
        {"intel_manifest", "openpower_manifest"},
        location=f"{location}.baseline",
    )
    for key in ("intel_manifest", "openpower_manifest"):
        if baseline[key] != _FIXED_PATHS[key]:
            raise ValidationError(
                f"{location}.baseline.{key}: expected {_FIXED_PATHS[key]!r}"
            )

    if failure["test_vectors_manifest"] != _FIXED_PATHS["test_vectors_manifest"]:
        raise ValidationError(
            f"{location}.test_vectors_manifest: expected "
            f"{_FIXED_PATHS['test_vectors_manifest']!r}"
        )

    contracts = require_object(failure["contracts"], f"{location}.contracts")
    require_exact_keys(
        contracts,
        {"case_definitions", "used_isa"},
        location=f"{location}.contracts",
    )
    _validate_contract_reference(
        contracts["case_definitions"],
        location=f"{location}.contracts.case_definitions",
        expected_file=_FIXED_PATHS["case_definitions"],
    )
    _validate_contract_reference(
        contracts["used_isa"],
        location=f"{location}.contracts.used_isa",
        expected_file=_FIXED_PATHS["used_isa"],
    )

    reproduce = require_object(failure["reproduce"], f"{location}.reproduce")
    require_exact_keys(
        reproduce, {"intel", "openpower", "verify"}, location=f"{location}.reproduce"
    )
    if reproduce != _REPRODUCE:
        raise ValidationError(f"{location}.reproduce: commands do not match schema v1")

    source = require_object(failure["source_artifacts"], f"{location}.source_artifacts")
    require_exact_keys(
        source, set(_SOURCE_KEYS), location=f"{location}.source_artifacts"
    )
    for key in _SOURCE_KEYS:
        require_sha256(source[key], f"{location}.source_artifacts.{key}")
    return failure


def _validate_bundle_snapshot(
    *,
    snapshot_root: Path,
    original_root: Path,
    marker: Path,
    failure: dict[str, JSONValue],
    case_bytes: bytes,
    case_value: JSONValue,
    used_bytes: bytes,
    used_value: JSONValue,
) -> FailureBundle:
    file_paths = {
        name: snapshot_root.joinpath(*relative.split("/"))
        for name, relative in _FIXED_PATHS.items()
    }
    if not isinstance(case_value, list) or len(case_value) != 1:
        raise ValidationError("failure bundle must contain exactly one case definition")
    case_sha = sha256_bytes(case_bytes)

    used_object = require_object(used_value, str(original_root / _FIXED_PATHS["used_isa"]))
    require_exact_keys(
        used_object,
        {"cases", "schema_version", "tokens"},
        location=str(original_root / _FIXED_PATHS["used_isa"]),
    )
    minimal_registry_data: dict[str, JSONValue] = {
        "schema_version": 1,
        "tokens": used_object["tokens"],
    }
    embedded_isa = validate_isa_registry(
        minimal_registry_data,
        source=f"{original_root / _FIXED_PATHS['used_isa']} tokens",
    )
    cases = load_case_definitions(
        file_paths["case_definitions"], isa_registry=embedded_isa
    )
    used = validate_used_isa_contract(
        used_object,
        registry=embedded_isa,
        cases=cases,
        source=str(original_root / _FIXED_PATHS["used_isa"]),
    )
    used_sha = sha256_bytes(used_bytes)
    if case_sha != cases.sha256:
        raise ValidationError("case definition contract hash is inconsistent")
    if used_sha != used.sha256:
        raise ValidationError("used ISA contract hash is inconsistent")

    contracts = require_object(failure["contracts"], "failure.contracts")
    case_reference = require_object(
        contracts["case_definitions"], "failure.contracts.case_definitions"
    )
    used_reference = require_object(contracts["used_isa"], "failure.contracts.used_isa")
    if case_reference["sha256"] != case_sha:
        raise ValidationError("failure case contract SHA-256 does not match its file")
    if used_reference["sha256"] != used_sha:
        raise ValidationError("failure used ISA SHA-256 does not match its file")
    if failure["case_definitions_sha256"] != case_sha:
        raise ValidationError("failure case_definitions_sha256 does not match its contract")
    if failure["used_isa_contract_sha256"] != used_sha:
        raise ValidationError("failure used_isa_contract_sha256 does not match its contract")

    inputs = validate_input_artifact(
        file_paths["test_vectors_manifest"], cases, embedded_isa
    )
    intel = validate_result_artifact(
        file_paths["intel_manifest"],
        cases,
        embedded_isa,
        input_artifact=inputs,
    )
    power = validate_result_artifact(
        file_paths["openpower_manifest"],
        cases,
        embedded_isa,
        input_artifact=inputs,
    )
    if inputs.record_count != 1 or intel.record_count != 1 or power.record_count != 1:
        raise ValidationError("failure bundle artifacts must contain exactly one record")
    if intel.role != "intel" or power.role != "openpower":
        raise ValidationError("failure baseline roles do not match their fixed paths")

    input_record = inputs.records[0]
    input_id = str(input_record["input_id"])
    case_id = str(input_record["case_id"])
    if failure["input_id"] != input_id or failure["case_id"] != case_id:
        raise ValidationError("failure identity does not match its single input")
    if failure["comparison"] != cases.get(case_id).comparison:
        raise ValidationError("failure comparison does not match its case contract")
    for role, artifact in (("intel", intel), ("openpower", power)):
        record = artifact.records[input_id]
        if record["input_id"] != input_id or record["case_id"] != case_id:
            raise ValidationError(f"failure {role} baseline identity mismatch")

    comparison = compare_result_records(
        cases.get(case_id),
        input_record,
        intel.records[input_id],
        power.records[input_id],
        validate=False,
    )
    if comparison.outcome != "mismatch" or comparison.first_difference is None:
        raise ValidationError("failure baselines do not contain an ordinary mismatch")
    if comparison.mismatch_count != failure["mismatch_count"]:
        raise ValidationError("failure mismatch_count does not match its baselines")
    if comparison.first_difference != failure["first_difference"]:
        raise ValidationError("failure first_difference does not match its baselines")

    # The validators consumed immutable snapshot files.  Restore public paths
    # to the supplied bundle while retaining the validated in-memory data.
    inputs = replace(
        inputs,
        manifest_path=original_root / _FIXED_PATHS["test_vectors_manifest"],
        vectors_path=original_root / "test-vectors.jsonl",
    )
    intel = replace(
        intel,
        manifest_path=original_root / _FIXED_PATHS["intel_manifest"],
        results_path=original_root / "baseline/intel/intel-results.jsonl",
    )
    power = replace(
        power,
        manifest_path=original_root / _FIXED_PATHS["openpower_manifest"],
        results_path=original_root / "baseline/openpower/power-results.jsonl",
    )
    return FailureBundle(
        root=original_root,
        failure_path=marker,
        failure=failure,
        cases=cases,
        isa_registry=embedded_isa,
        used_isa_contract=used,
        input_artifact=inputs,
        baseline_intel=intel,
        baseline_openpower=power,
    )


def load_failure_bundle(path: str | Path) -> FailureBundle:
    """Load and cross-check an immutable snapshot of a failure bundle."""

    marker = _failure_path(path)
    root = marker.parent
    files = _snapshot_bundle_files(root, ("failure.json", *_BUNDLE_MEMBERS))
    failure_value = _read_canonical_value(files["failure.json"], source=str(marker))
    failure = _validate_failure_shape(failure_value, location=str(marker))
    case_relative = _FIXED_PATHS["case_definitions"]
    used_relative = _FIXED_PATHS["used_isa"]
    case_value = _read_canonical_value(
        files[case_relative], source=str(root / case_relative)
    )
    used_value = _read_canonical_value(
        files[used_relative], source=str(root / used_relative)
    )

    with tempfile.TemporaryDirectory(prefix="ioitf-failure-snapshot-") as temporary:
        snapshot_root = Path(temporary)
        _write_snapshot(snapshot_root, files)
        try:
            return _validate_bundle_snapshot(
                snapshot_root=snapshot_root,
                original_root=root,
                marker=marker,
                failure=failure,
                case_bytes=files[case_relative],
                case_value=case_value,
                used_bytes=files[used_relative],
                used_value=used_value,
            )
        except ValidationError as exc:
            message = str(exc).replace(str(snapshot_root), str(root))
            raise ValidationError(message) from exc


def _result_projection(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    projection: dict[str, JSONValue] = {
        key: record[key]
        for key in ("case_id", "input_id", "runner", "status")
    }
    if record["status"] == "ok":
        projection["observed"] = record["observed"]
    else:
        error = require_object(record["error"], "replay result.error")
        projection["error"] = {"code": error["code"], "stage": error["stage"]}
    return projection


def _first_difference(
    baseline: JSONValue,
    replay: JSONValue,
    *,
    path: str,
) -> dict[str, JSONValue] | None:
    if baseline == replay:
        return None
    if isinstance(baseline, dict) and isinstance(replay, dict):
        keys = sorted(set(baseline) | set(replay), key=utf16_sort_key)
        for key in keys:
            child_path = f"{path}.{key}" if path else key
            if key not in baseline or key not in replay:
                return {
                    "baseline": baseline.get(key),
                    "path": child_path,
                    "replay": replay.get(key),
                }
            difference = _first_difference(
                baseline[key], replay[key], path=child_path
            )
            if difference is not None:
                return difference
    elif isinstance(baseline, list) and isinstance(replay, list):
        common = min(len(baseline), len(replay))
        for index in range(common):
            difference = _first_difference(
                baseline[index], replay[index], path=f"{path}[{index}]"
            )
            if difference is not None:
                return difference
        return {
            "baseline": len(baseline),
            "path": f"{path}.length",
            "replay": len(replay),
        }
    return {"baseline": baseline, "path": path, "replay": replay}


def _difference_paths(
    baseline: JSONValue,
    replay: JSONValue,
    *,
    path: str,
) -> Iterator[str]:
    if baseline == replay:
        return
    if isinstance(baseline, dict) and isinstance(replay, dict):
        for key in sorted(set(baseline) | set(replay), key=utf16_sort_key):
            child_path = f"{path}.{key}" if path else key
            if key not in baseline or key not in replay:
                yield child_path
            else:
                yield from _difference_paths(
                    baseline[key], replay[key], path=child_path
                )
        return
    if isinstance(baseline, list) and isinstance(replay, list):
        for index in range(min(len(baseline), len(replay))):
            yield from _difference_paths(
                baseline[index], replay[index], path=f"{path}[{index}]"
            )
        if len(baseline) != len(replay):
            yield f"{path}.length"
        return
    yield path


def _environment_differences(
    baseline: ResultArtifact,
    replay: ResultArtifact,
) -> list[JSONValue]:
    paths: list[str] = []
    pairs: list[tuple[str, JSONValue, JSONValue]] = [
        (
            "runner.build_id",
            require_object(baseline.manifest["runner"], "baseline.runner")["build_id"],
            require_object(replay.manifest["runner"], "replay.runner")["build_id"],
        ),
        (
            "isa_registry_sha256",
            baseline.manifest["isa_registry_sha256"],
            replay.manifest["isa_registry_sha256"],
        ),
    ]
    baseline_environment = require_object(
        baseline.manifest["environment"], "baseline.environment"
    )
    replay_environment = require_object(
        replay.manifest["environment"], "replay.environment"
    )
    for key in ("cpu_model", "git_commit", "kernel", "os", "build_units", "link"):
        pairs.append(
            (
                f"environment.{key}",
                baseline_environment[key],
                replay_environment[key],
            )
        )
    for path, expected, actual in pairs:
        paths.extend(_difference_paths(expected, actual, path=path))
    return paths


def verify_replay_artifacts(
    bundle: FailureBundle,
    *,
    intel_manifest: str | Path,
    openpower_manifest: str | Path,
) -> tuple[ReplayVerification, ResultArtifact, ResultArtifact]:
    """Validate replay artifacts and compare them with both bundle baselines."""

    intel = validate_result_artifact(
        intel_manifest,
        bundle.cases,
        bundle.isa_registry,
        input_artifact=bundle.input_artifact,
    )
    power = validate_result_artifact(
        openpower_manifest,
        bundle.cases,
        bundle.isa_registry,
        input_artifact=bundle.input_artifact,
    )
    if intel.role != "intel" or power.role != "openpower":
        raise ValidationError("replay result roles do not match their command arguments")

    input_record = bundle.input_artifact.records[0]
    input_id = str(input_record["input_id"])
    case_id = str(input_record["case_id"])
    result_differences: list[JSONValue] = []
    for role, baseline, replay in (
        ("intel", bundle.baseline_intel, intel),
        ("openpower", bundle.baseline_openpower, power),
    ):
        difference = _first_difference(
            _result_projection(baseline.records[input_id]),
            _result_projection(replay.records[input_id]),
            path="",
        )
        if difference is not None:
            result_differences.append({"difference": difference, "role": role})

    comparison = compare_result_records(
        bundle.cases.get(case_id),
        input_record,
        intel.records[input_id],
        power.records[input_id],
        validate=False,
    )
    replay_comparison: dict[str, JSONValue] = {
        "first_difference": comparison.first_difference,
        "mismatch_count": comparison.mismatch_count,
        "outcome": comparison.outcome,
    }
    expected_count = bundle.failure["mismatch_count"]
    expected_first = bundle.failure["first_difference"]
    comparison_matches = (
        comparison.outcome == "mismatch"
        and comparison.mismatch_count == expected_count
        and comparison.first_difference == expected_first
    )
    verification = ReplayVerification(
        reproduced=not result_differences and comparison_matches,
        environment_differences={
            "intel": _environment_differences(bundle.baseline_intel, intel),
            "openpower": _environment_differences(bundle.baseline_openpower, power),
        },
        result_differences=result_differences,
        replay_comparison=replay_comparison,
    )
    return verification, intel, power


__all__ = [
    "FailureBundle",
    "ReplayVerification",
    "load_failure_bundle",
    "verify_replay_artifacts",
]
