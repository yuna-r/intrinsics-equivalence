"""Strict validation of completed IOITF input and runner artifacts.

The manifest is a completion marker, not merely descriptive metadata.  This
module therefore validates the canonical manifest, the exact data-file byte
snapshot authenticated by it, every record in that snapshot, and the case/ISA
projections that give the records their meaning before returning an artifact.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .canonical import (
    JSONValue,
    MAX_SAFE_INTEGER,
    dump_bytes,
    iter_canonical_jsonl_bytes,
    read_canonical_json,
    require_bool,
    require_exact_keys,
    require_int,
    require_object,
    require_sorted_unique_strings,
    require_string,
    sha256_bytes,
    utf16_sort_key,
)
from .cases import CaseDefinition, CaseRegistry, resolve_case_registry
from .errors import ValidationError
from .isa import (
    ISARegistry,
    UsedISAContract,
    load_isa_registry,
    project_used_isa,
    validate_isa_registry,
)
from .records import (
    FP_EXCEPTION_ORDER,
    ROUNDING_MODES,
    require_sha256,
    validate_input_record,
    validate_result_record,
)


PROFILES = {"smoke", "standard", "exhaustive-small", "stress"}
ROLE_FILES = {
    "intel": ("intel-results.jsonl", "intel-results.manifest.json", "x86_64"),
    "openpower": ("power-results.jsonl", "power-results.manifest.json", "ppc64le"),
}
ABI_VERSION = 1

_STABLE_ID = re.compile(r"^[a-z][a-z0-9_.-]*$")
_VERSIONED_ID = re.compile(r"^[a-z][a-z0-9_.-]*\.v([1-9][0-9]*)$")
_GIT_COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_MACRO_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class InputArtifact:
    """A completely validated input artifact and its immutable byte snapshot."""

    manifest_path: Path
    vectors_path: Path
    manifest: dict[str, JSONValue]
    records: tuple[dict[str, JSONValue], ...]
    record_count: int
    sha256: str
    case_ids: tuple[str, ...]
    case_definitions_sha256: str
    used_isa_contract: UsedISAContract
    isa_registry_matches_local: bool


@dataclass(frozen=True)
class ResultArtifact:
    """A completely validated normal runner-result artifact."""

    manifest_path: Path
    results_path: Path
    manifest: dict[str, JSONValue]
    records: dict[str, dict[str, JSONValue]]
    ordered_records: tuple[dict[str, JSONValue], ...]
    role: str
    development_fixture: bool
    record_count: int
    sha256: str
    isa_registry_matches_local: bool


@dataclass(frozen=True)
class _PreflightCoverage:
    boolean_controls: dict[str, bool]
    fp_exception_flags: frozenset[str]
    rounding_modes: frozenset[str]


def _snapshot_isa_registry(value: str | Path | ISARegistry) -> ISARegistry:
    if not isinstance(value, ISARegistry):
        return load_isa_registry(value)
    snapshot = validate_isa_registry(
        copy.deepcopy(value.data), source="ISA registry snapshot"
    )
    if snapshot.sha256 != value.sha256:
        raise ValidationError("ISA registry was mutated after validation")
    return snapshot


def _resolve_registries(
    cases: str | Path | CaseRegistry,
    isa_registry: str | Path | ISARegistry,
) -> tuple[CaseRegistry, ISARegistry]:
    isa = _snapshot_isa_registry(isa_registry)
    return resolve_case_registry(cases, isa_registry=isa), isa


def _read_bytes(path: Path, description: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {description} {path}: {exc}") from exc


def _resolve_input_manifest(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "test-vectors.manifest.json"
    elif candidate.name == "test-vectors.jsonl":
        candidate = candidate.with_name("test-vectors.manifest.json")
    if candidate.name != "test-vectors.manifest.json":
        raise ValidationError(
            "input manifest must be named test-vectors.manifest.json"
        )
    return candidate


def _resolve_result_manifest(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        matches = [
            candidate / manifest_name
            for _, manifest_name, _ in ROLE_FILES.values()
            if (candidate / manifest_name).is_file()
        ]
        if len(matches) != 1:
            raise ValidationError(
                f"{candidate}: expected exactly one role result manifest"
            )
        return matches[0]
    for result_name, manifest_name, _ in ROLE_FILES.values():
        if candidate.name == result_name:
            return candidate.with_name(manifest_name)
    return candidate


def _validate_file_metadata(
    value: JSONValue,
    *,
    location: str,
    expected_file: str,
    data_path: Path,
    data: bytes,
) -> tuple[int, str]:
    metadata = require_object(value, location)
    require_exact_keys(
        metadata,
        {"byte_length", "file", "record_count", "sha256"},
        location=location,
    )
    if metadata["file"] != expected_file:
        raise ValidationError(f"{location}.file: expected {expected_file!r}")
    byte_length = require_int(
        metadata["byte_length"], f"{location}.byte_length", minimum=0
    )
    record_count = require_int(
        metadata["record_count"],
        f"{location}.record_count",
        minimum=1,
        maximum=MAX_SAFE_INTEGER,
    )
    expected_sha = require_sha256(metadata["sha256"], f"{location}.sha256")
    if byte_length != len(data):
        raise ValidationError(
            f"{data_path}: byte length mismatch ({len(data)} != {byte_length})"
        )
    actual_sha = sha256_bytes(data)
    if actual_sha != expected_sha:
        raise ValidationError(f"{data_path}: SHA-256 mismatch")
    return record_count, expected_sha


def _validate_input_manifest_shape(
    manifest: dict[str, JSONValue], location: str
) -> None:
    require_exact_keys(
        manifest,
        {
            "artifact_type",
            "case_definitions_sha256",
            "complete",
            "isa_registry_sha256",
            "profile",
            "schema_version",
            "test_vectors",
            "used_isa_contract_sha256",
        },
        location=location,
    )
    if manifest["artifact_type"] != "ioitf.test-vectors":
        raise ValidationError(f"{location}.artifact_type: expected ioitf.test-vectors")
    if require_int(manifest["schema_version"], f"{location}.schema_version") != 1:
        raise ValidationError(f"{location}.schema_version: only version 1 is supported")
    if require_bool(manifest["complete"], f"{location}.complete") is not True:
        raise ValidationError(f"{location}.complete: must be true")
    profile = require_string(manifest["profile"], f"{location}.profile")
    if profile not in PROFILES:
        raise ValidationError(f"{location}.profile: unknown profile {profile!r}")
    for key in (
        "case_definitions_sha256",
        "isa_registry_sha256",
        "used_isa_contract_sha256",
    ):
        require_sha256(manifest[key], f"{location}.{key}")


def validate_input_artifact(
    manifest_path: str | Path,
    cases: str | Path | CaseRegistry,
    isa_registry: str | Path | ISARegistry,
) -> InputArtifact:
    """Validate a completed input artifact against local case and ISA data.

    The full ISA-registry hash is provenance and may differ because of unused
    tokens.  The used projection and referenced case projection are hard gates.
    """

    registry, isa = _resolve_registries(cases, isa_registry)
    resolved_manifest = _resolve_input_manifest(manifest_path)
    manifest = read_canonical_json(resolved_manifest)
    location = str(resolved_manifest)
    _validate_input_manifest_shape(manifest, location)

    vectors_path = resolved_manifest.parent / "test-vectors.jsonl"
    data = _read_bytes(vectors_path, "input data")
    expected_count, vectors_sha = _validate_file_metadata(
        manifest["test_vectors"],
        location=f"{location}.test_vectors",
        expected_file="test-vectors.jsonl",
        data_path=vectors_path,
        data=data,
    )

    records: list[dict[str, JSONValue]] = []
    seen_ids: set[str] = set()
    referenced_cases: set[str] = set()
    for sequence, record in enumerate(
        iter_canonical_jsonl_bytes(data, source=str(vectors_path)), 1
    ):
        case_id = require_string(
            record.get("case_id"), f"{vectors_path}:{sequence}.case_id"
        )
        case = registry.get(case_id)
        validate_input_record(record, case, expected_sequence=sequence)
        input_id = str(record["input_id"])
        if input_id in seen_ids:
            raise ValidationError(
                f"{vectors_path}:{sequence}: duplicate input_id {input_id}"
            )
        seen_ids.add(input_id)
        referenced_cases.add(case_id)
        records.append(record)
    if len(records) != expected_count:
        raise ValidationError(
            f"{vectors_path}: record count mismatch ({len(records)} != {expected_count})"
        )
    case_sha = registry.projected_sha256(referenced_cases)
    supplied_case_sha = str(manifest["case_definitions_sha256"])
    if supplied_case_sha != case_sha:
        raise ValidationError(
            f"{location}: case definition projection SHA-256 mismatch"
        )
    selected_cases = [
        registry.get(case_id)
        for case_id in sorted(referenced_cases, key=utf16_sort_key)
    ]
    used = project_used_isa(isa, selected_cases)
    if manifest["used_isa_contract_sha256"] != used.sha256:
        raise ValidationError(f"{location}: used ISA projection SHA-256 mismatch")

    return InputArtifact(
        manifest_path=resolved_manifest,
        vectors_path=vectors_path,
        manifest=manifest,
        records=tuple(records),
        record_count=expected_count,
        sha256=vectors_sha,
        case_ids=tuple(sorted(referenced_cases, key=utf16_sort_key)),
        case_definitions_sha256=case_sha,
        used_isa_contract=used,
        isa_registry_matches_local=manifest["isa_registry_sha256"] == isa.sha256,
    )


def _require_string_array(
    value: Any, location: str, *, nonempty_items: bool = False
) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError(f"{location}: expected a string array")
    return [
        require_string(item, f"{location}[{index}]", nonempty=nonempty_items)
        for index, item in enumerate(value)
    ]


def _validate_preflight(
    value: JSONValue, *, architecture: str, location: str
) -> _PreflightCoverage:
    preflight = require_object(value, location)
    require_exact_keys(
        preflight,
        {"probe_suite", "probe_suite_sha256", "probes", "status"},
        location=location,
    )
    suite = preflight["probe_suite"]
    if not isinstance(suite, list):
        raise ValidationError(f"{location}.probe_suite: expected an array")
    suite_ids: list[str] = []
    all_boolean: dict[str, bool] = {}
    all_flags: set[str] = set()
    all_modes: set[str] = set()
    allowed_boolean = (
        {"exception_traps_enabled", "mxcsr_daz", "mxcsr_ftz"}
        if architecture == "x86_64"
        else {"exception_traps_enabled", "fpscr_ni", "vscr_nj"}
    )
    for index, raw_probe in enumerate(suite):
        probe_location = f"{location}.probe_suite[{index}]"
        probe = require_object(raw_probe, probe_location)
        require_exact_keys(
            probe,
            {"architecture", "expected", "id", "implementation_id", "version"},
            location=probe_location,
        )
        if probe["architecture"] != architecture:
            raise ValidationError(
                f"{probe_location}.architecture: expected {architecture!r}"
            )
        probe_id = require_string(probe["id"], f"{probe_location}.id")
        match = _VERSIONED_ID.fullmatch(probe_id)
        if match is None:
            raise ValidationError(f"{probe_location}.id: invalid versioned probe ID")
        version = require_int(probe["version"], f"{probe_location}.version", minimum=1)
        if match.group(1) != str(version):
            raise ValidationError(f"{probe_location}: ID and version disagree")
        implementation_id = require_string(
            probe["implementation_id"], f"{probe_location}.implementation_id"
        )
        if not _STABLE_ID.fullmatch(implementation_id):
            raise ValidationError(
                f"{probe_location}.implementation_id: invalid stable identifier"
            )
        expected = require_object(probe["expected"], f"{probe_location}.expected")
        require_exact_keys(
            expected,
            {"boolean_controls", "fp_exception_flags", "rounding_modes"},
            location=f"{probe_location}.expected",
        )
        controls = require_object(
            expected["boolean_controls"],
            f"{probe_location}.expected.boolean_controls",
        )
        unknown_controls = set(controls) - allowed_boolean
        if unknown_controls:
            raise ValidationError(
                f"{probe_location}.expected.boolean_controls: unknown keys: "
                + ", ".join(sorted(unknown_controls))
            )
        for name, raw_value in controls.items():
            control_value = require_bool(
                raw_value, f"{probe_location}.expected.boolean_controls.{name}"
            )
            if name in all_boolean and all_boolean[name] != control_value:
                raise ValidationError(
                    f"{location}: probes disagree about boolean control {name!r}"
                )
            all_boolean[name] = control_value

        raw_flags = expected["fp_exception_flags"]
        if not isinstance(raw_flags, list):
            raise ValidationError(
                f"{probe_location}.expected.fp_exception_flags: expected an array"
            )
        parsed_flags = [
            require_string(
                flag,
                f"{probe_location}.expected.fp_exception_flags[{flag_index}]",
            )
            for flag_index, flag in enumerate(raw_flags)
        ]
        normalized_flags = [flag for flag in FP_EXCEPTION_ORDER if flag in parsed_flags]
        if parsed_flags != normalized_flags or len(parsed_flags) != len(set(parsed_flags)):
            raise ValidationError(
                f"{probe_location}.expected.fp_exception_flags: invalid order or flag"
            )
        modes = require_sorted_unique_strings(
            expected["rounding_modes"],
            f"{probe_location}.expected.rounding_modes",
        )
        if any(mode not in ROUNDING_MODES for mode in modes):
            raise ValidationError(
                f"{probe_location}.expected.rounding_modes: unknown mode"
            )
        if not controls and not parsed_flags and not modes:
            raise ValidationError(f"{probe_location}.expected: probe has no expectation")
        suite_ids.append(probe_id)
        all_flags.update(parsed_flags)
        all_modes.update(modes)

    if suite_ids != sorted(set(suite_ids), key=utf16_sort_key):
        raise ValidationError(f"{location}.probe_suite: expected ID-sorted unique probes")
    supplied_suite_sha = require_sha256(
        preflight["probe_suite_sha256"], f"{location}.probe_suite_sha256"
    )
    if supplied_suite_sha != sha256_bytes(dump_bytes(suite, newline=True)):
        raise ValidationError(f"{location}.probe_suite_sha256: hash mismatch")

    probes = preflight["probes"]
    if not isinstance(probes, list):
        raise ValidationError(f"{location}.probes: expected an array")
    observed_ids: list[str] = []
    for index, raw_result in enumerate(probes):
        probe_location = f"{location}.probes[{index}]"
        result = require_object(raw_result, probe_location)
        require_exact_keys(result, {"id", "status"}, location=probe_location)
        observed_ids.append(require_string(result["id"], f"{probe_location}.id"))
        if result["status"] != "passed":
            raise ValidationError(
                f"{probe_location}.status: normal result manifest requires passed"
            )
    if observed_ids != suite_ids:
        raise ValidationError(f"{location}.probes: must cover the complete suite in order")
    if preflight["status"] != "passed":
        raise ValidationError(f"{location}.status: normal result manifest requires passed")
    return _PreflightCoverage(
        boolean_controls=all_boolean,
        fp_exception_flags=frozenset(all_flags),
        rounding_modes=frozenset(all_modes),
    )


def _validate_compile_unit(
    value: JSONValue, *, index: int, location: str
) -> tuple[str, str, bool]:
    unit_location = f"{location}[{index}]"
    unit = require_object(value, unit_location)
    require_exact_keys(
        unit,
        {
            "assertions_enabled",
            "compile_options",
            "compiler",
            "feature_macros",
            "id",
            "kind",
            "object_sha256",
            "source_blob_sha256",
        },
        location=unit_location,
    )
    unit_id = require_string(unit["id"], f"{unit_location}.id")
    if not _STABLE_ID.fullmatch(unit_id):
        raise ValidationError(f"{unit_location}.id: invalid build-unit ID")
    kind = require_string(unit["kind"], f"{unit_location}.kind")
    if kind not in {"adapter", "runner", "sut", "support"}:
        raise ValidationError(f"{unit_location}.kind: unknown kind")
    assertions = require_bool(
        unit["assertions_enabled"], f"{unit_location}.assertions_enabled"
    )
    _require_string_array(unit["compile_options"], f"{unit_location}.compile_options")
    compiler = require_object(unit["compiler"], f"{unit_location}.compiler")
    require_exact_keys(
        compiler, {"name", "target_triple", "version"}, location=f"{unit_location}.compiler"
    )
    for key in ("name", "target_triple", "version"):
        require_string(compiler[key], f"{unit_location}.compiler.{key}")
    macros = require_object(unit["feature_macros"], f"{unit_location}.feature_macros")
    for name, replacement in macros.items():
        if not _MACRO_NAME.fullmatch(name):
            raise ValidationError(f"{unit_location}.feature_macros: invalid name {name!r}")
        require_string(
            replacement,
            f"{unit_location}.feature_macros.{name}",
            nonempty=False,
        )
    if kind in {"adapter", "sut"} and assertions == ("NDEBUG" in macros):
        raise ValidationError(
            f"{unit_location}: assertions_enabled disagrees with effective NDEBUG"
        )
    for key in ("object_sha256", "source_blob_sha256"):
        require_sha256(unit[key], f"{unit_location}.{key}")
    return unit_id, kind, assertions


def _is_canonical_absolute_posix_path(value: str) -> bool:
    if not value.startswith("/") or value == "/" or "//" in value:
        return False
    parts = value.split("/")[1:]
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return PurePosixPath(value).as_posix() == value


def _validate_environment(
    value: JSONValue,
    *,
    role: str,
    registry: CaseRegistry,
    isa: ISARegistry,
    case_ids: tuple[str, ...],
    local_isa_hash_matches: bool,
    development_fixture: bool,
    location: str,
) -> tuple[set[str], set[str]]:
    environment = require_object(value, location)
    architecture = ROLE_FILES[role][2]
    keys = {
        "architecture",
        "assertions_enabled",
        "available_isa",
        "build_units",
        "case_build_units",
        "cpu_model",
        "endianness",
        "fp_controls",
        "fp_rounding_modes",
        "git_commit",
        "kernel",
        "link",
        "os",
    }
    if architecture == "ppc64le":
        keys.add("vector_semantics")
    require_exact_keys(environment, keys, location=location)
    if environment["architecture"] != architecture:
        raise ValidationError(f"{location}.architecture: expected {architecture!r}")
    if environment["os"] != "linux":
        raise ValidationError(f"{location}.os: schema v1 requires linux")
    if environment["endianness"] != "little":
        raise ValidationError(f"{location}.endianness: schema v1 requires little")
    for key in ("cpu_model", "kernel"):
        require_string(environment[key], f"{location}.{key}")
    commit = require_string(environment["git_commit"], f"{location}.git_commit")
    if not _GIT_COMMIT.fullmatch(commit):
        raise ValidationError(f"{location}.git_commit: invalid full commit ID")

    assertions = require_bool(
        environment["assertions_enabled"], f"{location}.assertions_enabled"
    )
    units = environment["build_units"]
    if not isinstance(units, list) or not units:
        raise ValidationError(f"{location}.build_units: expected a non-empty array")
    unit_ids: list[str] = []
    unit_kinds: dict[str, str] = {}
    relevant_assertions: list[bool] = []
    for index, raw_unit in enumerate(units):
        unit_id, kind, unit_assertions = _validate_compile_unit(
            raw_unit, index=index, location=f"{location}.build_units"
        )
        unit_ids.append(unit_id)
        unit_kinds[unit_id] = kind
        if kind in {"adapter", "sut"}:
            relevant_assertions.append(unit_assertions)
    if unit_ids != sorted(set(unit_ids), key=utf16_sort_key):
        raise ValidationError(f"{location}.build_units: expected ID-sorted unique units")
    if any(value != assertions for value in relevant_assertions):
        raise ValidationError(
            f"{location}.assertions_enabled: disagrees with adapter/SUT unit"
        )
    if not development_fixture and not relevant_assertions:
        raise ValidationError(
            f"{location}.build_units: native results require an adapter or SUT unit"
        )

    case_units = require_object(
        environment["case_build_units"], f"{location}.case_build_units"
    )
    require_exact_keys(case_units, set(case_ids), location=f"{location}.case_build_units")
    known_units = set(unit_ids)
    for case_id in case_ids:
        references = require_sorted_unique_strings(
            case_units[case_id], f"{location}.case_build_units.{case_id}", nonempty=True
        )
        unknown = set(references) - known_units
        if unknown:
            raise ValidationError(
                f"{location}.case_build_units.{case_id}: unknown units: "
                + ", ".join(sorted(unknown))
            )
        if not development_fixture and not any(
            unit_kinds[unit_id] in {"adapter", "sut"} for unit_id in references
        ):
            raise ValidationError(
                f"{location}.case_build_units.{case_id}: no adapter/SUT unit"
            )

    isa_registry_hash_matches = local_isa_hash_matches
    available = require_sorted_unique_strings(
        environment["available_isa"], f"{location}.available_isa"
    )
    available_set = set(available)
    for token in available:
        try:
            entry = isa.get(token)
        except ValidationError:
            if isa_registry_hash_matches:
                raise ValidationError(
                    f"{location}.available_isa: token {token!r} is absent from matching registry"
                )
            if not _STABLE_ID.fullmatch(token):
                raise ValidationError(f"{location}.available_isa: invalid token {token!r}")
            continue
        if entry["architecture"] != architecture:
            raise ValidationError(
                f"{location}.available_isa: token {token!r} has wrong architecture"
            )
        closure = set(isa.closure([token], architecture=architecture))
        if not closure.issubset(available_set):
            missing = sorted(closure - available_set, key=utf16_sort_key)
            raise ValidationError(
                f"{location}.available_isa: missing implied tokens: {', '.join(missing)}"
            )

    modes = require_sorted_unique_strings(
        environment["fp_rounding_modes"], f"{location}.fp_rounding_modes"
    )
    if any(mode not in ROUNDING_MODES for mode in modes):
        raise ValidationError(f"{location}.fp_rounding_modes: unknown mode")
    controls = require_object(environment["fp_controls"], f"{location}.fp_controls")
    control_keys = (
        {"exception_traps_enabled", "mxcsr_daz", "mxcsr_ftz"}
        if architecture == "x86_64"
        else {"exception_traps_enabled", "fpscr_ni", "vscr_nj"}
    )
    require_exact_keys(controls, control_keys, location=f"{location}.fp_controls")
    for key in control_keys:
        if require_bool(controls[key], f"{location}.fp_controls.{key}") is not False:
            raise ValidationError(f"{location}.fp_controls.{key}: expected false")

    if architecture == "ppc64le":
        semantics = require_object(
            environment["vector_semantics"], f"{location}.vector_semantics"
        )
        require_exact_keys(
            semantics,
            {"altivec_src_compat", "element_reg_order"},
            location=f"{location}.vector_semantics",
        )
        if semantics["altivec_src_compat"] not in {"gcc", "xl", "mixed", "unknown"}:
            raise ValidationError(
                f"{location}.vector_semantics.altivec_src_compat: invalid value"
            )
        if semantics["element_reg_order"] not in {"little", "big", "unknown"}:
            raise ValidationError(
                f"{location}.vector_semantics.element_reg_order: invalid value"
            )

    link = require_object(environment["link"], f"{location}.link")
    require_exact_keys(
        link,
        {"binary_sha256", "link_options", "loaded_libraries"},
        location=f"{location}.link",
    )
    require_sha256(link["binary_sha256"], f"{location}.link.binary_sha256")
    _require_string_array(link["link_options"], f"{location}.link.link_options")
    libraries = link["loaded_libraries"]
    if not isinstance(libraries, list):
        raise ValidationError(f"{location}.link.loaded_libraries: expected an array")
    paths: list[str] = []
    for index, raw_library in enumerate(libraries):
        library_location = f"{location}.link.loaded_libraries[{index}]"
        library = require_object(raw_library, library_location)
        require_exact_keys(library, {"path", "sha256"}, location=library_location)
        path = require_string(library["path"], f"{library_location}.path")
        if not _is_canonical_absolute_posix_path(path):
            raise ValidationError(f"{library_location}.path: expected canonical absolute POSIX path")
        require_sha256(library["sha256"], f"{library_location}.sha256")
        paths.append(path)
    if paths != sorted(set(paths), key=utf16_sort_key):
        raise ValidationError(
            f"{location}.link.loaded_libraries: expected path-sorted unique entries"
        )
    return available_set, set(modes)


def _case_uses_floating(case: CaseDefinition) -> bool:
    signature = case.signature
    arguments = signature["arguments"]
    assert isinstance(arguments, list)
    values = [require_object(item, "case signature argument") for item in arguments]
    values.append(require_object(signature["return"], "case signature return"))
    return any(value.get("element") in {"f32", "f64"} for value in values)


def _validate_preflight_coverage(
    coverage: _PreflightCoverage,
    *,
    role: str,
    registry: CaseRegistry,
    inputs_by_id: dict[str, dict[str, JSONValue]],
    results: dict[str, dict[str, JSONValue]],
) -> set[str]:
    active_ids = {
        input_id
        for input_id, result in results.items()
        if result["status"] != "unsupported"
    }
    active_modes = {
        str(require_object(inputs_by_id[input_id]["environment"], "input.environment")["rounding"])
        for input_id in active_ids
    }
    if not active_modes.issubset(coverage.rounding_modes):
        missing = sorted(active_modes - set(coverage.rounding_modes), key=utf16_sort_key)
        raise ValidationError(
            "result manifest.preflight: missing rounding probes for " + ", ".join(missing)
        )
    floating = any(
        _case_uses_floating(registry.get(str(inputs_by_id[input_id]["case_id"])))
        for input_id in active_ids
    )
    if floating:
        required_controls = (
            {"exception_traps_enabled", "mxcsr_daz", "mxcsr_ftz"}
            if role == "intel"
            else {"exception_traps_enabled", "fpscr_ni", "vscr_nj"}
        )
        missing_controls = required_controls - set(coverage.boolean_controls)
        if missing_controls:
            raise ValidationError(
                "result manifest.preflight: missing floating-point control probes: "
                + ", ".join(sorted(missing_controls))
            )
        if any(coverage.boolean_controls[name] for name in required_controls):
            raise ValidationError(
                "result manifest.preflight: floating-point non-IEEE/trap controls must be false"
            )
    observe_exceptions = any(
        bool(registry.get(str(inputs_by_id[input_id]["case_id"])).environment["observe_fp_exceptions"])
        for input_id in active_ids
    )
    if observe_exceptions and set(FP_EXCEPTION_ORDER) - set(coverage.fp_exception_flags):
        raise ValidationError(
            "result manifest.preflight: exception-observing cases require all five flag probes"
        )
    return active_modes


def _validate_result_manifest_shape(
    manifest: dict[str, JSONValue], *, location: str
) -> tuple[str, bool]:
    require_exact_keys(
        manifest,
        {
            "artifact_type",
            "case_definitions_sha256",
            "complete",
            "environment",
            "input_sha256",
            "isa_registry_sha256",
            "preflight",
            "results",
            "runner",
            "schema_version",
            "used_isa_contract_sha256",
        },
        location=location,
    )
    if manifest["artifact_type"] != "ioitf.runner-results":
        raise ValidationError(f"{location}.artifact_type: expected ioitf.runner-results")
    if require_int(manifest["schema_version"], f"{location}.schema_version") != 1:
        raise ValidationError(f"{location}.schema_version: only version 1 is supported")
    if require_bool(manifest["complete"], f"{location}.complete") is not True:
        raise ValidationError(f"{location}.complete: must be true")
    for key in (
        "case_definitions_sha256",
        "input_sha256",
        "isa_registry_sha256",
        "used_isa_contract_sha256",
    ):
        require_sha256(manifest[key], f"{location}.{key}")
    runner = require_object(manifest["runner"], f"{location}.runner")
    require_exact_keys(
        runner, {"abi_version", "build_id", "role"}, location=f"{location}.runner"
    )
    if require_int(runner["abi_version"], f"{location}.runner.abi_version") != ABI_VERSION:
        raise ValidationError(f"{location}.runner.abi_version: expected {ABI_VERSION}")
    role = require_string(runner["role"], f"{location}.runner.role")
    if role not in ROLE_FILES:
        raise ValidationError(f"{location}.runner.role: expected intel or openpower")
    build_id = require_string(runner["build_id"], f"{location}.runner.build_id")
    return role, build_id.startswith("development-fixture:")


def _revalidate_input_snapshot(
    artifact: InputArtifact,
    registry: CaseRegistry,
    isa: ISARegistry,
) -> InputArtifact:
    """Revalidate an InputArtifact without consulting its filesystem paths.

    A coordinator validates its input exactly once before it starts validating
    host results.  Reopening the manifest path here would let a concurrent
    replacement mix two different input sets in one comparison.  Canonical
    reserialization of the captured records reconstructs the authenticated
    byte snapshot and also detects accidental mutation by library callers.
    """

    manifest = copy.deepcopy(artifact.manifest)
    records = [copy.deepcopy(record) for record in artifact.records]
    location = "input artifact snapshot"
    _validate_input_manifest_shape(manifest, location)
    data = b"".join(dump_bytes(record, newline=True) for record in records)
    expected_count, vectors_sha = _validate_file_metadata(
        manifest["test_vectors"],
        location=f"{location}.test_vectors",
        expected_file="test-vectors.jsonl",
        data_path=artifact.vectors_path,
        data=data,
    )
    if expected_count != artifact.record_count or vectors_sha != artifact.sha256:
        raise ValidationError("input artifact snapshot metadata was mutated")

    seen_ids: set[str] = set()
    referenced_cases: set[str] = set()
    for sequence, record in enumerate(records, 1):
        case_id = require_string(record.get("case_id"), f"snapshot:{sequence}.case_id")
        case = registry.get(case_id)
        validate_input_record(record, case, expected_sequence=sequence)
        input_id = str(record["input_id"])
        if input_id in seen_ids:
            raise ValidationError(f"snapshot:{sequence}: duplicate input_id {input_id}")
        seen_ids.add(input_id)
        referenced_cases.add(case_id)
    if len(records) != expected_count:
        raise ValidationError("input artifact snapshot record count mismatch")

    case_sha = registry.projected_sha256(referenced_cases)
    if manifest["case_definitions_sha256"] != case_sha:
        raise ValidationError("input artifact snapshot case projection mismatch")
    selected_cases = [
        registry.get(case_id)
        for case_id in sorted(referenced_cases, key=utf16_sort_key)
    ]
    used = project_used_isa(isa, selected_cases)
    if manifest["used_isa_contract_sha256"] != used.sha256:
        raise ValidationError("input artifact snapshot used ISA projection mismatch")
    expected_case_ids = tuple(sorted(referenced_cases, key=utf16_sort_key))
    if (
        artifact.case_ids != expected_case_ids
        or artifact.case_definitions_sha256 != case_sha
        or artifact.used_isa_contract.sha256 != used.sha256
    ):
        raise ValidationError("input artifact snapshot derived metadata was mutated")

    return InputArtifact(
        manifest_path=artifact.manifest_path,
        vectors_path=artifact.vectors_path,
        manifest=manifest,
        records=tuple(records),
        record_count=expected_count,
        sha256=vectors_sha,
        case_ids=expected_case_ids,
        case_definitions_sha256=case_sha,
        used_isa_contract=used,
        isa_registry_matches_local=manifest["isa_registry_sha256"] == isa.sha256,
    )


def validate_result_artifact(
    manifest_path: str | Path,
    cases: str | Path | CaseRegistry,
    isa_registry: str | Path | ISARegistry,
    *,
    input_artifact: str | Path | InputArtifact,
) -> ResultArtifact:
    """Validate a completed normal result artifact and its input relationship."""

    registry, isa = _resolve_registries(cases, isa_registry)
    if isinstance(input_artifact, InputArtifact):
        inputs = _revalidate_input_snapshot(input_artifact, registry, isa)
    else:
        inputs = validate_input_artifact(input_artifact, registry, isa)

    resolved_manifest = _resolve_result_manifest(manifest_path)
    manifest = read_canonical_json(resolved_manifest)
    location = str(resolved_manifest)
    role, development_fixture = _validate_result_manifest_shape(
        manifest, location=location
    )
    result_name, expected_manifest_name, architecture = ROLE_FILES[role]
    if resolved_manifest.name != expected_manifest_name:
        raise ValidationError(
            f"{location}: role {role!r} requires manifest name {expected_manifest_name!r}"
        )

    if manifest["input_sha256"] != inputs.sha256:
        raise ValidationError(f"{location}: input SHA-256 does not match input artifact")
    if manifest["case_definitions_sha256"] != inputs.case_definitions_sha256:
        raise ValidationError(f"{location}: case definition projection SHA-256 mismatch")
    if manifest["used_isa_contract_sha256"] != inputs.used_isa_contract.sha256:
        raise ValidationError(f"{location}: used ISA projection SHA-256 mismatch")
    local_isa_hash_matches = manifest["isa_registry_sha256"] == isa.sha256

    available_isa, manifest_modes = _validate_environment(
        manifest["environment"],
        role=role,
        registry=registry,
        isa=isa,
        case_ids=inputs.case_ids,
        local_isa_hash_matches=local_isa_hash_matches,
        development_fixture=development_fixture,
        location=f"{location}.environment",
    )
    preflight = _validate_preflight(
        manifest["preflight"],
        architecture=architecture,
        location=f"{location}.preflight",
    )

    results_path = resolved_manifest.parent / result_name
    data = _read_bytes(results_path, "result data")
    expected_count, results_sha = _validate_file_metadata(
        manifest["results"],
        location=f"{location}.results",
        expected_file=result_name,
        data_path=results_path,
        data=data,
    )
    if expected_count != inputs.record_count:
        raise ValidationError(
            f"{location}.results.record_count: does not match input artifact"
        )

    inputs_by_id = {str(record["input_id"]): record for record in inputs.records}
    records: dict[str, dict[str, JSONValue]] = {}
    ordered_records: list[dict[str, JSONValue]] = []
    for line_number, record in enumerate(
        iter_canonical_jsonl_bytes(data, source=str(results_path)), 1
    ):
        input_id = require_sha256(
            record.get("input_id"), f"{results_path}:{line_number}.input_id"
        )
        if input_id in records:
            raise ValidationError(
                f"{results_path}:{line_number}: duplicate input_id {input_id}"
            )
        try:
            input_record = inputs_by_id[input_id]
        except KeyError as exc:
            raise ValidationError(
                f"{results_path}:{line_number}: unknown input_id {input_id}"
            ) from exc
        case_id = require_string(
            record.get("case_id"), f"{results_path}:{line_number}.case_id"
        )
        if case_id != input_record["case_id"]:
            raise ValidationError(
                f"{results_path}:{line_number}: case_id does not match input"
            )
        case = registry.get(case_id)
        validate_result_record(
            record, case, role=role, input_record=input_record
        )
        if record["status"] == "ok":
            missing_isa = set(case.required_isa(role)) - available_isa
            if missing_isa:
                raise ValidationError(
                    f"{results_path}:{line_number}: ok result lacks required ISA metadata: "
                    + ", ".join(sorted(missing_isa, key=utf16_sort_key))
                )
        records[input_id] = record
        ordered_records.append(record)
    if len(records) != expected_count:
        raise ValidationError(
            f"{results_path}: record count mismatch ({len(records)} != {expected_count})"
        )
    missing_ids = set(inputs_by_id) - set(records)
    if missing_ids:
        raise ValidationError(
            f"{results_path}: missing input IDs: "
            + ", ".join(sorted(missing_ids, key=utf16_sort_key)[:5])
        )

    _validate_preflight_coverage(
        preflight,
        role=role,
        registry=registry,
        inputs_by_id=inputs_by_id,
        results=records,
    )
    input_modes = {
        str(require_object(record["environment"], "input.environment")["rounding"])
        for record in inputs.records
    }
    if manifest_modes != input_modes:
        raise ValidationError(
            f"{location}.environment.fp_rounding_modes: does not match result inputs"
        )
    return ResultArtifact(
        manifest_path=resolved_manifest,
        results_path=results_path,
        manifest=manifest,
        records=records,
        ordered_records=tuple(ordered_records),
        role=role,
        development_fixture=development_fixture,
        record_count=expected_count,
        sha256=results_sha,
        isa_registry_matches_local=local_isa_hash_matches,
    )


__all__ = [
    "ABI_VERSION",
    "InputArtifact",
    "PROFILES",
    "ROLE_FILES",
    "ResultArtifact",
    "validate_input_artifact",
    "validate_result_artifact",
]
