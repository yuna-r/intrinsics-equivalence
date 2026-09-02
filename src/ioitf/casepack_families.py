"""Small reusable generators and executable models for related case packs.

Each normative contract still owns a neighboring ``development.py``.  This
module only removes the mechanical repetition shared by closely related SSE2
operations, keeping every individual case pack short enough to read at once.
"""

from __future__ import annotations

import math
import struct
from typing import Callable, Iterator, Sequence

from .canonical import JSONValue
from .cases import CaseDefinition
from .development import SplitMix64, rounding_modes, scalar, vector


Candidate = dict[str, JSONValue]
FactoryResult = tuple[str, dict[str, int], Callable[..., Iterator[Candidate]], Callable[[Candidate], Candidate]]


def _base(case: CaseDefinition, index: int, *, random: bool, seed: str) -> Candidate:
    modes = rounding_modes(case)
    generation: dict[str, JSONValue] = {"class": "random" if random else "boundary"}
    if random:
        generation.update({"algorithm": "splitmix64", "seed": seed})
    return {
        "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
        "generation": generation,
    }


def _lanes(record: Candidate, name: str) -> list[JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    value = operands[name]
    assert isinstance(value, dict)
    lanes = value["lanes"]
    assert isinstance(lanes, list)
    return lanes


def _bits(record: Candidate, name: str) -> int:
    operands = record["operands"]
    assert isinstance(operands, dict)
    value = operands[name]
    assert isinstance(value, dict)
    return int(str(value["bits"]), 16)


def _signed(value: int, width: int) -> int:
    return value - (1 << width) if value & (1 << (width - 1)) else value


BinaryExample = (
    tuple[Sequence[int], Sequence[int]]
    | tuple[Sequence[int], Sequence[int], str]
)


def _binary_lane(operation: str, left: int, right: int, *, width: int, signed: bool) -> int:
    """The deliberately tiny instruction set behind :func:`binary_case`."""

    mask = (1 << width) - 1
    a = _signed(left, width) if signed else left
    b = _signed(right, width) if signed else right
    if operation == "+":
        return left + right
    if operation == "-":
        return left - right
    if operation == "&":
        return left & right
    if operation == "|":
        return left | right
    if operation == "^":
        return left ^ right
    if operation == "~&":
        return (~left) & right
    if operation == "==":
        return mask if left == right else 0
    if operation == ">":
        return mask if a > b else 0
    if operation == "<":
        return mask if a < b else 0
    if operation == "sat+":
        result = a + b
    elif operation == "sat-":
        result = a - b
    elif operation == "avg":
        return (left + right + 1) // 2
    elif operation == "min":
        return min(a, b)
    elif operation == "max":
        return max(a, b)
    elif operation == "*lo":
        return left * right
    elif operation == "*hi":
        return (a * b) >> width
    else:
        raise ValueError(f"unknown binary case operation: {operation!r}")

    lower = -(1 << (width - 1)) if signed else 0
    upper = (1 << (width - 1)) - 1 if signed else mask
    return min(upper, max(lower, result))


def binary_case(
    case_id: str,
    shape: str,
    operation: str,
    examples: Sequence[BinaryExample],
    *,
    standard: int,
    example_class: str = "boundary",
) -> FactoryResult:
    """Build the repetitive binary-vector case pack from its interesting bits.

    ``shape`` reads like ``i16x8`` and ``operation`` is intentionally compact:
    ``+ - & | ^ ~& == > < sat+ sat- avg min max *lo *hi``.
    """

    element, separator, lane_text = shape.rpartition("x")
    if not separator or element[:1] not in {"i", "u"}:
        raise ValueError(f"binary_case requires an integer vector shape, got {shape!r}")
    width = int(element[1:])
    lanes = int(lane_text)
    mask = (1 << width) - 1
    signed = element.startswith("i")
    _binary_lane(operation, 0, 0, width=width, signed=signed)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        modes = rounding_modes(case)
        for index, example in enumerate(examples):
            left, right = example[:2]
            generation_class = str(example[2]) if len(example) == 3 else example_class
            yield {
                "environment": {
                    "fp_mode": "ieee",
                    "rounding": modes[index % len(modes)],
                },
                "generation": {"class": generation_class},
                "operands": {
                    "a": vector(element, tuple(left)),
                    "b": vector(element, tuple(right)),
                },
            }
        while True:
            yield {
                "environment": {
                    "fp_mode": "ieee",
                    "rounding": modes[random.next() % len(modes)],
                },
                "generation": {
                    "algorithm": "splitmix64",
                    "class": "random",
                    "seed": seed_text,
                },
                "operands": {
                    "a": vector(
                        element, tuple(random.next() & mask for _ in range(lanes))
                    ),
                    "b": vector(
                        element, tuple(random.next() & mask for _ in range(lanes))
                    ),
                },
            }

    def execute(record: Candidate) -> Candidate:
        result = tuple(
            _binary_lane(
                operation,
                int(str(left), 16),
                int(str(right), 16),
                width=width,
                signed=signed,
            )
            for left, right in zip(
                _lanes(record, "a"), _lanes(record, "b"), strict=True
            )
        )
        return {"return": vector(element, result)}

    return case_id, {"standard": standard}, candidates, execute


def variable_shift_case(
    case_id: str, element: str, lanes: int, kind: str
) -> FactoryResult:
    width = int(element[1:])
    mask = (1 << width) - 1
    counts = (0, 1, width // 2, width - 1, width, width + 1, 255)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        for index, count in enumerate(counts):
            item = _base(case, index, random=False, seed=seed_text)
            values = tuple((index * 0x9E37 + lane * 0x5555 + (1 << (width - 1))) & mask for lane in range(lanes))
            item["operands"] = {
                "a": vector(element, values),
                "count": vector("u64", (count, 0xFEDCBA9876543210)),
            }
            yield item
        index = len(counts)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            count = random.next() & 0xFF
            item["operands"] = {
                "a": vector(element, tuple(random.next() & mask for _ in range(lanes))),
                "count": vector("u64", (count, random.next())),
            }
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        count = int(str(_lanes(record, "count")[0]), 16)
        output: list[int] = []
        for raw in _lanes(record, "a"):
            value = int(str(raw), 16)
            if kind == "left":
                result = 0 if count >= width else (value << count) & mask
            elif kind == "logical-right":
                result = 0 if count >= width else value >> count
            else:
                shift = min(count, width - 1)
                result = _signed(value, width) >> shift
            output.append(result)
        return {"return": vector(element, tuple(output))}

    return case_id, {"standard": len(counts)}, candidates, execute


def signed_compare_case(case_id: str, element: str, lanes: int) -> FactoryResult:
    width = int(element[1:])
    mask = (1 << width) - 1

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        structured = (
            (tuple(range(lanes)), tuple(reversed(range(lanes)))),
            (tuple((0, 1, mask, 1 << (width - 1)) * ((lanes + 3) // 4))[:lanes], tuple((mask, 0, mask - 1, (1 << (width - 1)) - 1) * ((lanes + 3) // 4))[:lanes]),
        )
        for index, (a, b) in enumerate(structured):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {"a": vector(element, a), "b": vector(element, b)}
            yield item
        index = len(structured)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["operands"] = {
                "a": vector(element, tuple(random.next() & mask for _ in range(lanes))),
                "b": vector(element, tuple(random.next() & mask for _ in range(lanes))),
            }
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        a = _lanes(record, "a")
        b = _lanes(record, "b")
        result = tuple(mask if _signed(int(str(x), 16), width) < _signed(int(str(y), 16), width) else 0 for x, y in zip(a, b, strict=True))
        return {"return": vector(element, result)}

    return case_id, {"standard": 2}, candidates, execute


def low_scalar_case(case_id: str, element: str, lanes: int) -> FactoryResult:
    width = int(element[1:])
    mask = (1 << width) - 1

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        patterns = (0, 1, mask, 1 << (width - 1), (1 << (width - 1)) - 1, 0xAAAAAAAAAAAAAAAA & mask)
        for index, low in enumerate(patterns):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {"a": vector(element, (low,) + tuple((low + lane) & mask for lane in range(1, lanes)))}
            yield item
        index = len(patterns)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["operands"] = {"a": vector(element, tuple(random.next() & mask for _ in range(lanes)))}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        return {"return": scalar(element, int(str(_lanes(record, "a")[0]), 16))}

    return case_id, {"standard": 6}, candidates, execute


def set_case(
    case_id: str,
    element: str,
    argument_names: Sequence[str],
    *,
    reverse: bool,
) -> FactoryResult:
    width = int(element[1:])
    mask = (1 << width) - 1

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        for index in range(4):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {
                name: scalar(element, (index * 0x3333333333333333 + lane * 0x1111111111111111) & mask)
                for lane, name in enumerate(argument_names)
            }
            yield item
        index = 4
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["operands"] = {name: scalar(element, random.next() & mask) for name in argument_names}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        values = [_bits(record, name) for name in argument_names]
        if reverse:
            values.reverse()
        return {"return": vector(element, tuple(values))}

    return case_id, {"standard": 4}, candidates, execute


def extract_i16_case(case_id: str) -> FactoryResult:
    indices = tuple(range(8))

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        index = 0
        while True:
            lane = indices[index % len(indices)]
            item = _base(case, index, random=index >= len(indices), seed=seed_text)
            values = tuple((position * 0x1111 + index) & 0xFFFF for position in range(8)) if index < len(indices) else tuple(random.next() & 0xFFFF for _ in range(8))
            item["immediates"] = {"imm8": lane}
            item["operands"] = {"a": vector("i16", values)}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        immediates = record["immediates"]
        assert isinstance(immediates, dict)
        return {"return": scalar("u32", int(str(_lanes(record, "a")[int(immediates["imm8"])]), 16))}

    return case_id, {"standard": 8}, candidates, execute


def insert_i16_case(case_id: str) -> FactoryResult:
    indices = tuple(range(8))

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        index = 0
        while True:
            lane = indices[index % len(indices)]
            item = _base(case, index, random=index >= len(indices), seed=seed_text)
            values = tuple((position * 0x1111 + index) & 0xFFFF for position in range(8)) if index < len(indices) else tuple(random.next() & 0xFFFF for _ in range(8))
            item["immediates"] = {"imm8": lane}
            item["operands"] = {"a": vector("i16", values), "value": scalar("i32", 0xCAFE0000 | index if index < len(indices) else random.next())}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        immediates = record["immediates"]
        assert isinstance(immediates, dict)
        values = [int(str(value), 16) for value in _lanes(record, "a")]
        values[int(immediates["imm8"])] = _bits(record, "value") & 0xFFFF
        return {"return": vector("i16", tuple(values))}

    return case_id, {"standard": 8}, candidates, execute


def bitcast_case(case_id: str, source: str, source_lanes: int, target: str, target_lanes: int) -> FactoryResult:
    source_width = int(source[1:])
    source_mask = (1 << source_width) - 1

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        structured = (
            tuple(0 for _ in range(source_lanes)),
            tuple((lane * 0x1111111111111111 + 0x0123456789ABCDEF) & source_mask for lane in range(source_lanes)),
            tuple(source_mask for _ in range(source_lanes)),
        )
        for index, values in enumerate(structured):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {"a": vector(source, values)}
            yield item
        index = len(structured)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["operands"] = {"a": vector(source, tuple(random.next() & source_mask for _ in range(source_lanes)))}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        values = [int(str(value), 16) for value in _lanes(record, "a")]
        if source_width == 64 and int(target[1:]) == 32:
            output = tuple(part for value in values for part in (value & 0xFFFFFFFF, value >> 32))
        elif source_width == 32 and int(target[1:]) == 64:
            output = tuple(values[index] | (values[index + 1] << 32) for index in range(0, len(values), 2))
        else:
            output = tuple(values)
        assert len(output) == target_lanes
        return {"return": vector(target, output)}

    return case_id, {"standard": 3}, candidates, execute


def minmax_f64_case(case_id: str, kind: str) -> FactoryResult:
    structured = (
        ((0x0000000000000000, 0x8000000000000000), (0x8000000000000000, 0x0000000000000000)),
        ((0x3FF0000000000000, 0xC000000000000000), (0x4000000000000000, 0xBFF0000000000000)),
        ((0x7FF8000000000042, 0x3FF0000000000000), (0x4000000000000000, 0x7FF0000000000001)),
    )

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        for index, (a, b) in enumerate(structured):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {"a": vector("f64", a), "b": vector("f64", b)}
            yield item
        index = len(structured)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["operands"] = {"a": vector("f64", (random.next(), random.next())), "b": vector("f64", (random.next(), random.next()))}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        output: list[int] = []
        for a_raw, b_raw in zip(_lanes(record, "a"), _lanes(record, "b"), strict=True):
            a_bits, b_bits = int(str(a_raw), 16), int(str(b_raw), 16)
            a = struct.unpack(">d", a_bits.to_bytes(8, "big"))[0]
            b = struct.unpack(">d", b_bits.to_bytes(8, "big"))[0]
            if math.isnan(a) or math.isnan(b) or a == b:
                output.append(b_bits)
            elif (kind == "min" and a < b) or (kind == "max" and a > b):
                output.append(a_bits)
            else:
                output.append(b_bits)
        return {"return": vector("f64", tuple(output))}

    return case_id, {"standard": len(structured)}, candidates, execute


def comi_f64_case(case_id: str, predicate: str) -> FactoryResult:
    structured = (
        (0x0000000000000000, 0x8000000000000000),
        (0x3FF0000000000000, 0x4000000000000000),
        (0x4000000000000000, 0x3FF0000000000000),
        (0x7FF8000000000042, 0x3FF0000000000000),
    )

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        for index, (a, b) in enumerate(structured):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {"a": vector("f64", (a, random.next())), "b": vector("f64", (b, random.next()))}
            yield item
        index = len(structured)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["operands"] = {"a": vector("f64", (random.next(), random.next())), "b": vector("f64", (random.next(), random.next()))}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        a_bits = int(str(_lanes(record, "a")[0]), 16)
        b_bits = int(str(_lanes(record, "b")[0]), 16)
        a = struct.unpack(">d", a_bits.to_bytes(8, "big"))[0]
        b = struct.unpack(">d", b_bits.to_bytes(8, "big"))[0]
        unordered = math.isnan(a) or math.isnan(b)
        result = {
            "eq": not unordered and a == b,
            "lt": not unordered and a < b,
            "le": not unordered and a <= b,
            "gt": not unordered and a > b,
            "ge": not unordered and a >= b,
            "neq": unordered or a != b,
        }[predicate]
        return {"return": scalar("i32", int(result))}

    return case_id, {"standard": len(structured)}, candidates, execute
