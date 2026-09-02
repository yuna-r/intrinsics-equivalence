"""Closed schema-version-1 case definitions."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import copy
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterator, Mapping

from .canonical import (
    JSONValue,
    dump_bytes,
    load_file,
    require_bool,
    require_exact_keys,
    require_int,
    require_object,
    require_sorted_unique_strings,
    require_string,
    sha256_bytes,
    utf16_sort_key,
)
from .errors import ValidationError
from .isa import ISARegistry


ELEMENT_WIDTHS = {
    "i8": 8,
    "i16": 16,
    "i32": 32,
    "i64": 64,
    "u8": 8,
    "u16": 16,
    "u32": 32,
    "u64": 64,
    "f32": 32,
    "f64": 64,
}
INTEGER_ELEMENTS = {name for name in ELEMENT_WIDTHS if name[0] in {"i", "u"}}
ROUNDING_MODES = {
    "nearest_even",
    "toward_negative",
    "toward_positive",
    "toward_zero",
}
CASE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9.-]*$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TAG_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
REGRESSION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*\.v[1-9][0-9]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
U64_PATTERN = re.compile(r"^(0|[1-9][0-9]*)$")
DECIMAL_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
U64_MAX = (1 << 64) - 1
U64_MAX_TEXT = str(U64_MAX)
ENDIAN_SENSITIVE_OPERATIONS = {
    "extract",
    "insert",
    "load",
    "merge",
    "pack",
    "permute",
    "shuffle",
    "store",
    "unpack",
}


@dataclass(frozen=True)
class CaseDefinition:
    id: str
    data: dict[str, JSONValue]
    source_path: Path | None = None

    @property
    def signature(self) -> dict[str, JSONValue]:
        return require_object(self.data["signature"], f"case {self.id}.signature")

    @property
    def comparison(self) -> dict[str, JSONValue]:
        return require_object(self.data["comparison"], f"case {self.id}.comparison")

    @property
    def environment(self) -> dict[str, JSONValue]:
        return require_object(self.data["environment"], f"case {self.id}.environment")

    def required_isa(self, role: str) -> tuple[str, ...]:
        role_value = require_object(self.data[role], f"case {self.id}.{role}")
        values = role_value["required_isa"]
        assert isinstance(values, list)
        return tuple(str(value) for value in values)


@dataclass(frozen=True)
class CaseRegistry:
    _cases: Mapping[str, CaseDefinition]
    sha256: str

    def __iter__(self) -> Iterator[CaseDefinition]:
        for case_id in self.ids:
            yield self._cases[case_id]

    def __len__(self) -> int:
        return len(self._cases)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._cases, key=utf16_sort_key))

    def get(self, case_id: str) -> CaseDefinition:
        try:
            return self._cases[case_id]
        except KeyError as exc:
            raise ValidationError(f"unknown case_id: {case_id}") from exc

    def projected_data(self, case_ids: set[str] | None = None) -> list[JSONValue]:
        selected = set(self.ids) if case_ids is None else case_ids
        unknown = selected - set(self.ids)
        if unknown:
            raise ValidationError(f"unknown case IDs in projection: {', '.join(sorted(unknown))}")
        return [self.get(case_id).data for case_id in self.ids if case_id in selected]

    def projected_sha256(self, case_ids: set[str] | None = None) -> str:
        return sha256_bytes(dump_bytes(self.projected_data(case_ids), newline=True))


def _require_identifier(value: Any, location: str) -> str:
    text = require_string(value, location)
    if not IDENTIFIER_PATTERN.fullmatch(text):
        raise ValidationError(f"{location}: expected a C identifier")
    return text


def _validate_role(
    value: JSONValue,
    location: str,
    *,
    isa_registry: ISARegistry | None,
    architecture: str,
) -> None:
    role = require_object(value, location)
    require_exact_keys(role, {"required_isa", "symbol"}, location=location)
    _require_identifier(role["symbol"], f"{location}.symbol")
    required = require_sorted_unique_strings(
        role["required_isa"], f"{location}.required_isa", nonempty=True
    )
    if isa_registry is not None:
        isa_registry.closure(required, architecture=architecture)


def _validate_argument(value: JSONValue, location: str) -> dict[str, JSONValue]:
    argument = require_object(value, location)
    argument_type = require_string(argument.get("type"), f"{location}.type")
    if argument_type == "pointer":
        require_exact_keys(argument, {"name", "type"}, location=location)
    elif argument_type in {"scalar", "immediate"}:
        require_exact_keys(argument, {"element", "name", "type"}, location=location)
    elif argument_type in {"vector", "mask"}:
        require_exact_keys(
            argument, {"element", "lanes", "name", "type"}, location=location
        )
        require_int(argument["lanes"], f"{location}.lanes", minimum=1)
    else:
        raise ValidationError(f"{location}.type: unsupported argument type {argument_type!r}")
    _require_identifier(argument["name"], f"{location}.name")
    if argument_type != "pointer":
        element = require_string(argument["element"], f"{location}.element")
        if element not in ELEMENT_WIDTHS:
            raise ValidationError(f"{location}.element: unknown element {element!r}")
        if argument_type == "immediate" and element not in {"u8", "i8"}:
            raise ValidationError(f"{location}.element: immediate must be u8 or i8")
        if argument_type == "mask" and element not in INTEGER_ELEMENTS:
            raise ValidationError(f"{location}.element: mask elements must be integers")
    return argument


def _validate_return(value: JSONValue, location: str) -> dict[str, JSONValue]:
    result = require_object(value, location)
    result_type = require_string(result.get("type"), f"{location}.type")
    if result_type == "void":
        require_exact_keys(result, {"type"}, location=location)
        return result
    if result_type == "scalar":
        require_exact_keys(result, {"element", "type"}, location=location)
    elif result_type in {"vector", "mask"}:
        require_exact_keys(result, {"element", "lanes", "type"}, location=location)
        require_int(result["lanes"], f"{location}.lanes", minimum=1)
    else:
        raise ValidationError(f"{location}.type: return cannot be {result_type!r}")
    element = require_string(result["element"], f"{location}.element")
    if element not in ELEMENT_WIDTHS:
        raise ValidationError(f"{location}.element: unknown element {element!r}")
    if result_type == "mask" and element not in INTEGER_ELEMENTS:
        raise ValidationError(f"{location}.element: mask elements must be integers")
    return result


def _validate_immediates(
    value: JSONValue,
    immediate_arguments: list[dict[str, JSONValue]],
    location: str,
) -> None:
    definitions = require_object(value, location)
    names = {str(argument["name"]) for argument in immediate_arguments}
    require_exact_keys(definitions, names, location=location)
    by_name = {str(argument["name"]): argument for argument in immediate_arguments}
    for name in sorted(names, key=utf16_sort_key):
        definition = require_object(definitions[name], f"{location}.{name}")
        require_exact_keys(definition, {"compile_time", "values"}, location=f"{location}.{name}")
        if require_bool(definition["compile_time"], f"{location}.{name}.compile_time") is not True:
            raise ValidationError(f"{location}.{name}.compile_time: must be true")
        values = definition["values"]
        if not isinstance(values, list) or not values:
            raise ValidationError(f"{location}.{name}.values: expected a non-empty array")
        parsed = [
            require_int(item, f"{location}.{name}.values[{index}]")
            for index, item in enumerate(values)
        ]
        if parsed != sorted(set(parsed)):
            raise ValidationError(f"{location}.{name}.values: expected ascending unique values")
        element = str(by_name[name]["element"])
        minimum, maximum = (0, 255) if element == "u8" else (-128, 127)
        if any(item < minimum or item > maximum for item in parsed):
            raise ValidationError(f"{location}.{name}.values: value outside {element}")


def _validate_ranges(value: Any, location: str) -> list[dict[str, JSONValue]]:
    if not isinstance(value, list):
        raise ValidationError(f"{location}: expected an array")
    ranges: list[dict[str, JSONValue]] = []
    previous_end = 0
    for index, item in enumerate(value):
        entry = require_object(item, f"{location}[{index}]")
        require_exact_keys(entry, {"byte_length", "offset"}, location=f"{location}[{index}]")
        offset = require_int(entry["offset"], f"{location}[{index}].offset", minimum=0)
        length = require_int(entry["byte_length"], f"{location}[{index}].byte_length", minimum=1)
        if index and offset < previous_end:
            raise ValidationError(f"{location}: ranges overlap or are not offset-sorted")
        previous_end = offset + length
        if previous_end > (1 << 53) - 1:
            raise ValidationError(f"{location}[{index}]: range end exceeds safe integer")
        ranges.append(entry)
    return ranges


def _validate_memory_contract(
    value: JSONValue,
    pointer_arguments: list[dict[str, JSONValue]],
    location: str,
) -> None:
    contract = require_object(value, location)
    names = {str(argument["name"]) for argument in pointer_arguments}
    require_exact_keys(contract, names, location=location)
    for name in sorted(names, key=utf16_sort_key):
        entry = require_object(contract[name], f"{location}.{name}")
        require_exact_keys(
            entry,
            {"access", "read_ranges", "required_alignment", "write_ranges"},
            location=f"{location}.{name}",
        )
        access = require_string(entry["access"], f"{location}.{name}.access")
        if access not in {"read", "read_write", "write"}:
            raise ValidationError(f"{location}.{name}.access: invalid access")
        alignment = require_int(
            entry["required_alignment"], f"{location}.{name}.required_alignment", minimum=1
        )
        if alignment & (alignment - 1):
            raise ValidationError(f"{location}.{name}.required_alignment: expected power of two")
        reads = _validate_ranges(entry["read_ranges"], f"{location}.{name}.read_ranges")
        writes = _validate_ranges(entry["write_ranges"], f"{location}.{name}.write_ranges")
        if access == "read" and (not reads or writes):
            raise ValidationError(f"{location}.{name}: read access/ranges disagree")
        if access == "write" and (reads or not writes):
            raise ValidationError(f"{location}.{name}: write access/ranges disagree")
        if access == "read_write" and (not reads or not writes):
            raise ValidationError(f"{location}.{name}: read_write needs both range sets")


def _validate_nan_policy(value: JSONValue, location: str) -> None:
    policy = require_object(value, location)
    require_exact_keys(
        policy, {"both_nan", "payload", "quiet_signaling", "sign"}, location=location
    )
    allowed = {
        "both_nan": {"equal", "unequal"},
        "payload": {"ignore", "match"},
        "quiet_signaling": {"ignore", "match"},
        "sign": {"ignore", "match"},
    }
    for key, choices in allowed.items():
        if policy[key] not in choices:
            raise ValidationError(f"{location}.{key}: invalid value")


def _require_u64_string(value: Any, location: str) -> str:
    text = require_string(value, location)
    if (
        not U64_PATTERN.fullmatch(text)
        or len(text) > len(U64_MAX_TEXT)
        or (len(text) == len(U64_MAX_TEXT) and text > U64_MAX_TEXT)
    ):
        raise ValidationError(f"{location}: expected canonical u64 decimal string")
    return text


def _validate_comparison(
    value: JSONValue, result: dict[str, JSONValue], location: str
) -> None:
    comparison = require_object(value, location)
    mode = require_string(comparison.get("mode"), f"{location}.mode")
    result_type = str(result["type"])
    element = str(result.get("element", ""))
    if result_type == "void" or result_type == "mask" or element in INTEGER_ELEMENTS:
        require_exact_keys(comparison, {"mode"}, location=location)
        if mode != "bit_exact":
            raise ValidationError(f"{location}.mode: this return requires bit_exact")
        return
    if mode == "bit_exact":
        require_exact_keys(comparison, {"mode"}, location=location)
        return
    if mode in {"classification", "ieee_value"}:
        require_exact_keys(comparison, {"mode", "nan", "signed_zero"}, location=location)
    elif mode == "ulp":
        require_exact_keys(
            comparison, {"max_ulps", "mode", "nan", "signed_zero"}, location=location
        )
        _require_u64_string(comparison["max_ulps"], f"{location}.max_ulps")
    elif mode == "abs_rel":
        require_exact_keys(
            comparison,
            {"abs_tolerance", "mode", "nan", "rel_tolerance", "signed_zero"},
            location=location,
        )
        for key in ("abs_tolerance", "rel_tolerance"):
            text = require_string(comparison[key], f"{location}.{key}")
            if not DECIMAL_PATTERN.fullmatch(text):
                raise ValidationError(f"{location}.{key}: invalid non-negative decimal")
    else:
        raise ValidationError(f"{location}.mode: unknown comparison mode {mode!r}")
    if comparison["signed_zero"] not in {"distinct", "equal"}:
        raise ValidationError(f"{location}.signed_zero: invalid policy")
    _validate_nan_policy(comparison["nan"], f"{location}.nan")


def _validate_expected_value(
    value: JSONValue,
    contract: dict[str, JSONValue],
    location: str,
) -> None:
    result_type = str(contract["type"])
    element = str(contract["element"])
    observed = require_object(value, location)
    if result_type == "scalar":
        require_exact_keys(observed, {"bits", "element"}, location=location)
        bits = observed["bits"]
        if observed["element"] != element or not isinstance(bits, str):
            raise ValidationError(f"{location}: value does not match {element} scalar")
        if not re.fullmatch(rf"0x[0-9a-f]{{{ELEMENT_WIDTHS[element] // 4}}}", bits):
            raise ValidationError(f"{location}.bits: invalid fixed-width value")
        return
    require_exact_keys(observed, {"element", "lanes"}, location=location)
    if observed["element"] != element:
        raise ValidationError(f"{location}.element: expected {element!r}")
    lanes = observed["lanes"]
    expected_lanes = int(contract["lanes"])
    if not isinstance(lanes, list) or len(lanes) != expected_lanes:
        raise ValidationError(f"{location}.lanes: expected {expected_lanes} lanes")
    pattern = re.compile(rf"0x[0-9a-f]{{{ELEMENT_WIDTHS[element] // 4}}}")
    if any(not isinstance(bits, str) or not pattern.fullmatch(bits) for bits in lanes):
        raise ValidationError(f"{location}.lanes: invalid fixed-width value")


def _validate_expected_observed(
    value: JSONValue,
    *,
    result: dict[str, JSONValue],
    pointer_arguments: list[dict[str, JSONValue]],
    observe_fp_exceptions: bool,
    location: str,
) -> None:
    observed = require_object(value, location)
    required: set[str] = set()
    if result["type"] != "void":
        required.add("return")
    if pointer_arguments:
        required.add("buffers")
    if observe_fp_exceptions:
        required.add("fp_exceptions")
    require_exact_keys(observed, required, location=location)
    if "return" in required:
        _validate_expected_value(
            observed["return"], result, f"{location}.return"
        )
    if "buffers" in required:
        buffers = require_object(observed["buffers"], f"{location}.buffers")
        if not buffers:
            raise ValidationError(f"{location}.buffers: expected at least one buffer")
        for buffer_id, raw_buffer in buffers.items():
            if not IDENTIFIER_PATTERN.fullmatch(buffer_id):
                raise ValidationError(f"{location}.buffers: invalid buffer ID {buffer_id!r}")
            buffer = require_object(raw_buffer, f"{location}.buffers.{buffer_id}")
            require_exact_keys(
                buffer,
                {"byte_offset", "bytes"},
                location=f"{location}.buffers.{buffer_id}",
            )
            if require_int(
                buffer["byte_offset"],
                f"{location}.buffers.{buffer_id}.byte_offset",
            ) != 0:
                raise ValidationError(f"{location}.buffers.{buffer_id}.byte_offset: expected 0")
            encoded = require_string(
                buffer["bytes"], f"{location}.buffers.{buffer_id}.bytes"
            )
            if not re.fullmatch(r"0x(?:[0-9a-f]{2})*", encoded):
                raise ValidationError(f"{location}.buffers.{buffer_id}.bytes: invalid")
    if "fp_exceptions" in required:
        flags = observed["fp_exceptions"]
        order = ["invalid", "divide-by-zero", "overflow", "underflow", "inexact"]
        if not isinstance(flags, list):
            raise ValidationError(f"{location}.fp_exceptions: expected an array")
        parsed = [
            require_string(flag, f"{location}.fp_exceptions[{index}]")
            for index, flag in enumerate(flags)
        ]
        normalized = [flag for flag in order if flag in parsed]
        if parsed != normalized or len(parsed) != len(set(parsed)):
            raise ValidationError(f"{location}.fp_exceptions: invalid order or flag")


def _validate_regressions(
    value: JSONValue,
    location: str,
    *,
    result: dict[str, JSONValue],
    pointer_arguments: list[dict[str, JSONValue]],
    observe_fp_exceptions: bool,
) -> None:
    regressions = require_object(value, location)
    if not regressions:
        raise ValidationError(f"{location}: expected at least one regression")
    input_ids: set[str] = set()
    for regression_id, raw in regressions.items():
        if not REGRESSION_ID_PATTERN.fullmatch(regression_id):
            raise ValidationError(f"{location}: invalid regression ID {regression_id!r}")
        entry = require_object(raw, f"{location}.{regression_id}")
        require_exact_keys(entry, {"expected_intel", "input_id"}, location=f"{location}.{regression_id}")
        input_id = require_string(entry["input_id"], f"{location}.{regression_id}.input_id")
        if not SHA256_PATTERN.fullmatch(input_id):
            raise ValidationError(f"{location}.{regression_id}.input_id: invalid SHA-256")
        if input_id in input_ids:
            raise ValidationError(f"{location}: multiple regression IDs use {input_id}")
        input_ids.add(input_id)
        expected = require_object(entry["expected_intel"], f"{location}.{regression_id}.expected_intel")
        require_exact_keys(expected, {"observed", "status"}, location=f"{location}.{regression_id}.expected_intel")
        if expected["status"] != "ok":
            raise ValidationError(f"{location}.{regression_id}.expected_intel.status: expected ok")
        _validate_expected_observed(
            expected["observed"],
            result=result,
            pointer_arguments=pointer_arguments,
            observe_fp_exceptions=observe_fp_exceptions,
            location=f"{location}.{regression_id}.expected_intel.observed",
        )


def validate_case_definition(
    value: JSONValue,
    *,
    source: str = "case",
    source_path: Path | None = None,
    isa_registry: ISARegistry | None = None,
) -> CaseDefinition:
    case = require_object(value, source)
    require_exact_keys(
        case,
        {
            "comparison",
            "description",
            "environment",
            "id",
            "input_domain",
            "intel",
            "openpower",
            "schema_version",
            "signature",
            "tags",
        },
        optional={"immediates", "memory_contract", "regressions"},
        location=source,
    )
    if require_int(case["schema_version"], f"{source}.schema_version") != 1:
        raise ValidationError(f"{source}.schema_version: only version 1 is supported")
    case_id = require_string(case["id"], f"{source}.id")
    if not CASE_ID_PATTERN.fullmatch(case_id):
        raise ValidationError(f"{source}.id: invalid case ID")
    require_string(case["description"], f"{source}.description")
    _validate_role(case["intel"], f"{source}.intel", isa_registry=isa_registry, architecture="x86_64")
    _validate_role(
        case["openpower"],
        f"{source}.openpower",
        isa_registry=isa_registry,
        architecture="ppc64le",
    )
    signature = require_object(case["signature"], f"{source}.signature")
    require_exact_keys(signature, {"arguments", "return"}, location=f"{source}.signature")
    raw_arguments = signature["arguments"]
    if not isinstance(raw_arguments, list):
        raise ValidationError(f"{source}.signature.arguments: expected an array")
    arguments = [
        _validate_argument(argument, f"{source}.signature.arguments[{index}]")
        for index, argument in enumerate(raw_arguments)
    ]
    names = [str(argument["name"]) for argument in arguments]
    if len(names) != len(set(names)):
        raise ValidationError(f"{source}.signature.arguments: duplicate names")
    result = _validate_return(signature["return"], f"{source}.signature.return")

    immediate_arguments = [argument for argument in arguments if argument["type"] == "immediate"]
    if immediate_arguments:
        if "immediates" not in case:
            raise ValidationError(f"{source}.immediates: required by signature")
        _validate_immediates(case["immediates"], immediate_arguments, f"{source}.immediates")
    elif "immediates" in case:
        raise ValidationError(f"{source}.immediates: no immediate arguments exist")

    pointer_arguments = [argument for argument in arguments if argument["type"] == "pointer"]
    if pointer_arguments:
        if "memory_contract" not in case:
            raise ValidationError(f"{source}.memory_contract: required by pointer arguments")
        _validate_memory_contract(
            case["memory_contract"], pointer_arguments, f"{source}.memory_contract"
        )
    elif "memory_contract" in case:
        raise ValidationError(f"{source}.memory_contract: no pointer arguments exist")

    input_domain = require_object(case["input_domain"], f"{source}.input_domain")
    require_exact_keys(input_domain, {"exclude"}, location=f"{source}.input_domain")
    if input_domain["exclude"] != []:
        raise ValidationError(f"{source}.input_domain.exclude: schema v1 requires []")
    environment = require_object(case["environment"], f"{source}.environment")
    require_exact_keys(
        environment,
        {"fp_rounding_modes", "observe_fp_exceptions"},
        location=f"{source}.environment",
    )
    modes = require_sorted_unique_strings(
        environment["fp_rounding_modes"],
        f"{source}.environment.fp_rounding_modes",
        nonempty=True,
    )
    if any(mode not in ROUNDING_MODES for mode in modes):
        raise ValidationError(f"{source}.environment.fp_rounding_modes: unknown mode")
    if any(mode != "nearest_even" for mode in modes) and "nearest_even" not in modes:
        raise ValidationError(
            f"{source}.environment.fp_rounding_modes: non-default rounding "
            "requires nearest_even as the witness baseline"
        )
    require_bool(environment["observe_fp_exceptions"], f"{source}.environment.observe_fp_exceptions")
    tags = require_sorted_unique_strings(case["tags"], f"{source}.tags")
    if any(not TAG_PATTERN.fullmatch(tag) for tag in tags):
        raise ValidationError(f"{source}.tags: invalid tag")
    operation_segments = set(case_id.split("."))
    if operation_segments & ENDIAN_SENSITIVE_OPERATIONS and "endianness-sensitive" not in tags:
        raise ValidationError(
            f"{source}.tags: this operation requires endianness-sensitive"
        )
    _validate_comparison(case["comparison"], result, f"{source}.comparison")
    requires_witness = any(mode != "nearest_even" for mode in modes) or bool(
        environment["observe_fp_exceptions"]
    )
    if requires_witness and "regressions" not in case:
        raise ValidationError(
            f"{source}.regressions: required by non-default rounding or FP exception observation"
        )
    if "regressions" in case:
        _validate_regressions(
            case["regressions"],
            f"{source}.regressions",
            result=result,
            pointer_arguments=pointer_arguments,
            observe_fp_exceptions=bool(environment["observe_fp_exceptions"]),
        )
    return CaseDefinition(case_id, case, source_path)


def _case_values(path: Path) -> Iterator[tuple[JSONValue, str, Path]]:
    if path.is_dir():
        files = sorted(
            (
                item
                for item in path.rglob("*")
                if item.is_file()
                and (
                    item.suffix.lower() in {".json", ".yaml", ".yml"}
                    or (
                        item.suffix.lower() == ".py"
                        and b"CASE_YAML" in item.read_bytes()
                    )
                )
                and item.name != "isa-registry.json"
            ),
            key=lambda item: utf16_sort_key(item.as_posix()),
        )
        if not files:
            raise ValidationError(f"{path}: no JSON, YAML, or Python case definitions found")
        for file_path in files:
            yield from _case_values(file_path)
        return
    if not path.is_file():
        raise ValidationError(f"case definition path does not exist: {path}")
    if path.suffix.lower() in {".yaml", ".yml"}:
        from .yamlio import load_yaml_file

        value = load_yaml_file(path)
    elif path.suffix.lower() == ".py":
        from .yamlio import load_yaml_text

        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValidationError(f"cannot read {path}: {exc}") from exc
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValidationError(f"{path}: UTF-8 BOM is not allowed")
        try:
            source_text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError(f"{path}: file is not valid UTF-8") from exc
        try:
            module = ast.parse(source_text, filename=str(path))
        except SyntaxError as exc:
            raise ValidationError(f"{path}: invalid Python: {exc}") from exc
        declarations: list[ast.expr] = []
        for statement in module.body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "CASE_YAML"
                for target in statement.targets
            ):
                declarations.append(statement.value)
            elif (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.target.id == "CASE_YAML"
            ):
                declarations.append(statement.value)
        if (
            len(declarations) != 1
            or not isinstance(declarations[0], ast.Constant)
            or not isinstance(declarations[0].value, str)
        ):
            raise ValidationError(
                f"{path}: expected exactly one literal CASE_YAML string"
            )
        value = load_yaml_text(declarations[0].value, source=f"{path}:CASE_YAML")
    elif path.suffix.lower() == ".json":
        value = load_file(path)
    else:
        raise ValidationError(f"unsupported case definition extension: {path}")
    if isinstance(value, list):
        if not value:
            raise ValidationError(f"{path}: case definition array is empty")
        for index, item in enumerate(value):
            yield item, f"{path}[{index}]", path
    else:
        yield value, str(path), path


def load_case_definitions(
    path: str | Path, *, isa_registry: ISARegistry | None = None
) -> CaseRegistry:
    cases: dict[str, CaseDefinition] = {}
    for value, source, source_path in _case_values(Path(path)):
        case = validate_case_definition(
            value,
            source=source,
            source_path=source_path,
            isa_registry=isa_registry,
        )
        if case.id in cases:
            raise ValidationError(f"duplicate case definition ID: {case.id}")
        cases[case.id] = case
    if not cases:
        raise ValidationError("at least one case definition is required")
    ordered = [cases[case_id].data for case_id in sorted(cases, key=utf16_sort_key)]
    digest = sha256_bytes(dump_bytes(ordered, newline=True))
    return CaseRegistry(MappingProxyType(cases), digest)


def resolve_case_registry(
    value: str | Path | CaseRegistry, *, isa_registry: ISARegistry | None = None
) -> CaseRegistry:
    if not isinstance(value, CaseRegistry):
        return load_case_definitions(value, isa_registry=isa_registry)
    snapshots: dict[str, CaseDefinition] = {}
    for original in value:
        snapshot = validate_case_definition(
            copy.deepcopy(original.data),
            source=f"case registry snapshot {original.id}",
            source_path=original.source_path,
            isa_registry=isa_registry,
        )
        snapshots[snapshot.id] = snapshot
    ordered = [snapshots[case_id].data for case_id in sorted(snapshots, key=utf16_sort_key)]
    digest = sha256_bytes(dump_bytes(ordered, newline=True))
    if digest != value.sha256:
        raise ValidationError("case registry was mutated after validation")
    return CaseRegistry(MappingProxyType(snapshots), digest)
