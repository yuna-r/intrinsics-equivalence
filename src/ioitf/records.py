"""Input/result record validation and input identity derivation."""

from __future__ import annotations

import re
from typing import Any

from .canonical import (
    JSONValue,
    dump_bytes,
    require_exact_keys,
    require_int,
    require_object,
    require_string,
    sha256_bytes,
    utf16_sort_key,
)
from .cases import CaseDefinition, ELEMENT_WIDTHS, ROUNDING_MODES
from .errors import ValidationError


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
SEED_PATTERN = re.compile(r"^0x[0-9a-f]{16}$")
GENERATION_CLASSES = {"boundary", "exhaustive", "random", "regression", "structured"}
RESULT_STATUSES = {
    "infrastructure_error",
    "invalid_input",
    "ok",
    "runtime_error",
    "signal",
    "unsupported",
}
STATUS_STAGE = {
    "infrastructure_error": "runner",
    "invalid_input": "input_validation",
    "runtime_error": "execution",
    "signal": "signal",
    "unsupported": "capability",
}
FP_EXCEPTION_ORDER = ["invalid", "divide-by-zero", "overflow", "underflow", "inexact"]


def require_sha256(value: Any, location: str) -> str:
    text = require_string(value, location)
    if not SHA256_PATTERN.fullmatch(text):
        raise ValidationError(f"{location}: expected a lowercase SHA-256")
    return text


def require_bits(value: Any, element: str, location: str) -> str:
    text = require_string(value, location)
    width = ELEMENT_WIDTHS.get(element)
    if width is None:
        raise ValidationError(f"{location}: unknown element {element!r}")
    digits = width // 4
    if not re.fullmatch(rf"0x[0-9a-f]{{{digits}}}", text):
        raise ValidationError(f"{location}: expected {element} fixed-width lowercase bits")
    return text


def _arguments(case: CaseDefinition) -> list[dict[str, JSONValue]]:
    raw = case.signature["arguments"]
    assert isinstance(raw, list)
    return [require_object(item, f"case {case.id}.signature.arguments") for item in raw]


def _validate_typed_value(
    value: JSONValue,
    contract: dict[str, JSONValue],
    location: str,
) -> None:
    value_type = str(contract["type"])
    if value_type == "pointer":
        pointer = require_object(value, location)
        require_exact_keys(pointer, {"buffer", "offset"}, location=location)
        buffer_id = require_string(pointer["buffer"], f"{location}.buffer")
        if not IDENTIFIER_PATTERN.fullmatch(buffer_id):
            raise ValidationError(f"{location}.buffer: invalid buffer ID")
        require_int(pointer["offset"], f"{location}.offset", minimum=0)
        return
    element = str(contract["element"])
    obj = require_object(value, location)
    if value_type == "scalar":
        require_exact_keys(obj, {"bits", "element"}, location=location)
        if obj["element"] != element:
            raise ValidationError(f"{location}.element: expected {element!r}")
        require_bits(obj["bits"], element, f"{location}.bits")
        return
    if value_type in {"mask", "vector"}:
        require_exact_keys(obj, {"element", "lanes"}, location=location)
        if obj["element"] != element:
            raise ValidationError(f"{location}.element: expected {element!r}")
        lanes = obj["lanes"]
        expected = int(contract["lanes"])
        if not isinstance(lanes, list) or len(lanes) != expected:
            raise ValidationError(f"{location}.lanes: expected {expected} lanes")
        for index, bits in enumerate(lanes):
            require_bits(bits, element, f"{location}.lanes[{index}]")
        return
    raise ValidationError(f"{location}: unsupported value type {value_type!r}")


def input_identity_payload(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    fields = {"case_id", "environment", "operands"}
    if "buffers" in record:
        fields.add("buffers")
    if "immediates" in record:
        fields.add("immediates")
    return {key: record[key] for key in fields}


def derive_input_id(record: dict[str, JSONValue]) -> str:
    return sha256_bytes(dump_bytes(input_identity_payload(record)))


def _buffer_lengths(value: JSONValue, location: str) -> dict[str, int]:
    buffers = require_object(value, location)
    lengths: dict[str, int] = {}
    for buffer_id in sorted(buffers, key=utf16_sort_key):
        if not IDENTIFIER_PATTERN.fullmatch(buffer_id):
            raise ValidationError(f"{location}: invalid buffer ID {buffer_id!r}")
        buffer = require_object(buffers[buffer_id], f"{location}.{buffer_id}")
        require_exact_keys(buffer, {"alignment", "bytes"}, location=f"{location}.{buffer_id}")
        alignment = require_int(buffer["alignment"], f"{location}.{buffer_id}.alignment", minimum=1)
        if alignment & (alignment - 1):
            raise ValidationError(f"{location}.{buffer_id}.alignment: expected power of two")
        encoded = require_string(buffer["bytes"], f"{location}.{buffer_id}.bytes")
        if not re.fullmatch(r"0x(?:[0-9a-f]{2})*", encoded):
            raise ValidationError(f"{location}.{buffer_id}.bytes: invalid byte string")
        lengths[buffer_id] = (len(encoded) - 2) // 2
    return lengths


def _validate_pointer_contracts(
    case: CaseDefinition,
    operands: dict[str, JSONValue],
    buffer_lengths: dict[str, int],
    buffers: dict[str, JSONValue],
) -> None:
    memory = require_object(case.data["memory_contract"], f"case {case.id}.memory_contract")
    for argument in _arguments(case):
        if argument["type"] != "pointer":
            continue
        name = str(argument["name"])
        pointer = require_object(operands[name], f"input.operands.{name}")
        buffer_id = str(pointer["buffer"])
        offset = int(pointer["offset"])
        if buffer_id not in buffer_lengths:
            raise ValidationError(f"input.operands.{name}.buffer: unknown buffer {buffer_id!r}")
        if offset > buffer_lengths[buffer_id]:
            raise ValidationError(f"input.operands.{name}.offset: outside buffer")
        contract = require_object(memory[name], f"case {case.id}.memory_contract.{name}")
        required_alignment = int(contract["required_alignment"])
        allocation = require_object(buffers[buffer_id], f"input.buffers.{buffer_id}")
        allocation_alignment = int(allocation["alignment"])
        if allocation_alignment % required_alignment or offset % required_alignment:
            raise ValidationError(f"input.operands.{name}: effective offset is misaligned")
        for range_kind in ("read_ranges", "write_ranges"):
            ranges = contract[range_kind]
            assert isinstance(ranges, list)
            for item in ranges:
                range_value = require_object(item, "memory range")
                end = offset + int(range_value["offset"]) + int(range_value["byte_length"])
                if end > buffer_lengths[buffer_id]:
                    raise ValidationError(f"input.operands.{name}: {range_kind} exceeds buffer")


def validate_input_record(
    record: dict[str, JSONValue],
    case: CaseDefinition,
    *,
    expected_sequence: int | None = None,
) -> None:
    arguments = _arguments(case)
    immediate_arguments = [argument for argument in arguments if argument["type"] == "immediate"]
    pointer_arguments = [argument for argument in arguments if argument["type"] == "pointer"]
    required = {
        "case_id",
        "environment",
        "generation",
        "input_id",
        "operands",
        "schema_version",
        "sequence",
    }
    if immediate_arguments:
        required.add("immediates")
    if pointer_arguments:
        required.add("buffers")
    require_exact_keys(record, required, location=f"input {record.get('input_id', '?')}")
    if require_int(record["schema_version"], "input.schema_version") != 1:
        raise ValidationError("input.schema_version: only version 1 is supported")
    if record["case_id"] != case.id:
        raise ValidationError(f"input.case_id: expected {case.id!r}")
    sequence = require_int(record["sequence"], "input.sequence", minimum=1)
    if expected_sequence is not None and sequence != expected_sequence:
        raise ValidationError(f"input.sequence: expected {expected_sequence}, got {sequence}")
    environment = require_object(record["environment"], "input.environment")
    require_exact_keys(environment, {"fp_mode", "rounding"}, location="input.environment")
    if environment["fp_mode"] != "ieee":
        raise ValidationError("input.environment.fp_mode: expected ieee")
    rounding = require_string(environment["rounding"], "input.environment.rounding")
    allowed_modes = case.environment["fp_rounding_modes"]
    assert isinstance(allowed_modes, list)
    if rounding not in ROUNDING_MODES or rounding not in allowed_modes:
        raise ValidationError("input.environment.rounding: not allowed by case")

    generation = require_object(record["generation"], "input.generation")
    generation_class = require_string(generation.get("class"), "input.generation.class")
    if generation_class not in GENERATION_CLASSES:
        raise ValidationError("input.generation.class: unknown class")
    if generation_class == "random":
        require_exact_keys(generation, {"algorithm", "class", "seed"}, location="input.generation")
        require_string(generation["algorithm"], "input.generation.algorithm")
        seed = require_string(generation["seed"], "input.generation.seed")
        if not SEED_PATTERN.fullmatch(seed):
            raise ValidationError("input.generation.seed: expected 64-bit lowercase hex")
    elif generation_class == "regression":
        require_exact_keys(generation, {"class", "regression_id"}, location="input.generation")
        regression_id = require_string(generation["regression_id"], "input.generation.regression_id")
        regressions = require_object(case.data.get("regressions"), f"case {case.id}.regressions")
        if regression_id not in regressions:
            raise ValidationError("input.generation.regression_id: unknown regression")
    else:
        require_exact_keys(generation, {"class"}, location="input.generation")

    operands = require_object(record["operands"], "input.operands")
    normal_arguments = [argument for argument in arguments if argument["type"] != "immediate"]
    names = {str(argument["name"]) for argument in normal_arguments}
    require_exact_keys(operands, names, location="input.operands")
    for argument in normal_arguments:
        name = str(argument["name"])
        _validate_typed_value(operands[name], argument, f"input.operands.{name}")

    if immediate_arguments:
        immediates = require_object(record["immediates"], "input.immediates")
        definitions = require_object(case.data["immediates"], f"case {case.id}.immediates")
        immediate_names = {str(argument["name"]) for argument in immediate_arguments}
        require_exact_keys(immediates, immediate_names, location="input.immediates")
        for argument in immediate_arguments:
            name = str(argument["name"])
            value = require_int(immediates[name], f"input.immediates.{name}")
            definition = require_object(definitions[name], f"case {case.id}.immediates.{name}")
            allowed = definition["values"]
            assert isinstance(allowed, list)
            if value not in allowed:
                raise ValidationError(f"input.immediates.{name}: undeclared value")

    if pointer_arguments:
        lengths = _buffer_lengths(record["buffers"], "input.buffers")
        buffers = require_object(record["buffers"], "input.buffers")
        for name, length in lengths.items():
            allocation = require_object(buffers[name], f"input.buffers.{name}")
            alignment = int(allocation["alignment"])
            if alignment < 1 or length < 0:
                raise ValidationError("invalid buffer allocation")
        _validate_pointer_contracts(case, operands, lengths, buffers)

    supplied_id = require_sha256(record["input_id"], "input.input_id")
    calculated = derive_input_id(record)
    if supplied_id != calculated:
        raise ValidationError(f"input.input_id: hash mismatch; expected {calculated}")
    if generation_class == "regression":
        regressions = require_object(case.data["regressions"], f"case {case.id}.regressions")
        regression = require_object(regressions[str(generation["regression_id"])], "regression")
        if regression["input_id"] != supplied_id:
            raise ValidationError("input regression entry refers to a different input_id")


def _validate_observed(
    value: JSONValue,
    case: CaseDefinition,
    *,
    input_record: dict[str, JSONValue] | None,
) -> None:
    observed = require_object(value, "result.observed")
    result_contract = require_object(case.signature["return"], f"case {case.id}.signature.return")
    pointer_case = any(argument["type"] == "pointer" for argument in _arguments(case))
    observe_exceptions = bool(case.environment["observe_fp_exceptions"])
    required: set[str] = set()
    if result_contract["type"] != "void":
        required.add("return")
    if pointer_case:
        required.add("buffers")
    if observe_exceptions:
        required.add("fp_exceptions")
    require_exact_keys(observed, required, location="result.observed")
    if "return" in required:
        _validate_typed_value(observed["return"], result_contract, "result.observed.return")
    if "buffers" in required:
        buffers = require_object(observed["buffers"], "result.observed.buffers")
        expected_ids: set[str] | None = None
        lengths: dict[str, int] | None = None
        if input_record is not None:
            lengths = _buffer_lengths(input_record["buffers"], "input.buffers")
            expected_ids = set(lengths)
            require_exact_keys(buffers, expected_ids, location="result.observed.buffers")
        for buffer_id, raw in buffers.items():
            item = require_object(raw, f"result.observed.buffers.{buffer_id}")
            require_exact_keys(item, {"byte_offset", "bytes"}, location=f"result.observed.buffers.{buffer_id}")
            if require_int(item["byte_offset"], f"result.observed.buffers.{buffer_id}.byte_offset") != 0:
                raise ValidationError("result buffer byte_offset must be zero in schema v1")
            encoded = require_string(item["bytes"], f"result.observed.buffers.{buffer_id}.bytes")
            if not re.fullmatch(r"0x(?:[0-9a-f]{2})*", encoded):
                raise ValidationError(f"result.observed.buffers.{buffer_id}.bytes: invalid")
            if lengths is not None and (len(encoded) - 2) // 2 != lengths[buffer_id]:
                raise ValidationError(f"result.observed.buffers.{buffer_id}: length changed")
    if "fp_exceptions" in required:
        flags = observed["fp_exceptions"]
        if not isinstance(flags, list):
            raise ValidationError("result.observed.fp_exceptions: expected an array")
        parsed = [
            require_string(flag, f"result.observed.fp_exceptions[{index}]")
            for index, flag in enumerate(flags)
        ]
        normalized = [flag for flag in FP_EXCEPTION_ORDER if flag in parsed]
        if parsed != normalized or len(parsed) != len(set(parsed)):
            raise ValidationError("result.observed.fp_exceptions: invalid order or flag")


def validate_result_record(
    record: dict[str, JSONValue],
    case: CaseDefinition,
    *,
    role: str,
    input_record: dict[str, JSONValue] | None = None,
) -> None:
    status = require_string(record.get("status"), "result.status")
    required = {
        "case_id",
        "duration_ns",
        "input_id",
        "runner",
        "schema_version",
        "status",
    }
    required.add("observed" if status == "ok" else "error")
    require_exact_keys(record, required, location=f"result {record.get('input_id', '?')}")
    if require_int(record["schema_version"], "result.schema_version") != 1:
        raise ValidationError("result.schema_version: only version 1 is supported")
    if record["case_id"] != case.id:
        raise ValidationError(f"result.case_id: expected {case.id!r}")
    require_sha256(record["input_id"], "result.input_id")
    if record["runner"] != role or role not in {"intel", "openpower"}:
        raise ValidationError(f"result.runner: expected {role!r}")
    if status not in RESULT_STATUSES:
        raise ValidationError("result.status: unknown status")
    require_int(record["duration_ns"], "result.duration_ns", minimum=0)
    if status == "ok":
        _validate_observed(record["observed"], case, input_record=input_record)
        return
    error = require_object(record["error"], "result.error")
    require_exact_keys(error, {"code", "stage"}, location="result.error")
    stage = require_string(error["stage"], "result.error.stage")
    code = require_string(error["code"], "result.error.code")
    if stage != STATUS_STAGE[status]:
        raise ValidationError(f"result.error.stage: expected {STATUS_STAGE[status]!r}")
    if not CODE_PATTERN.fullmatch(code):
        raise ValidationError("result.error.code: invalid stable code")
