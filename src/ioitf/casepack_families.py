"""Small reusable generators and executable models for related case packs.

Each case owns one combined Python pack, while legacy neighboring models remain
readable.  This module removes the mechanical repetition shared by closely
related SSE2 operations, keeping every individual model short enough to scan.
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


def _shape(shape: str) -> tuple[str, int, int, int]:
    element, separator, lane_text = shape.rpartition("x")
    if not separator or element[:1] not in {"f", "i", "u"}:
        raise ValueError(f"invalid vector shape: {shape!r}")
    width = int(element[1:])
    lanes = int(lane_text)
    return element, width, lanes, (1 << width) - 1


def _boundary_values(element: str) -> tuple[int, ...]:
    width = int(element[1:])
    mask = (1 << width) - 1
    sign = 1 << (width - 1)
    if element == "f32":
        return (
            0, 0x80000000, 1, 0x80000001, 0x007FFFFF,
            0x807FFFFF, 0x00800000, 0x80800000, 0x7F7FFFFF,
            0xFF7FFFFF, 0x7F800000, 0xFF800000, 0x7FC00042,
            0x7F800001, 0x3F800000, 0xBF800000, 0x40000000,
            0x41200000, 0x41A00000, 0x3F7FFFFF,
        )
    if element == "f64":
        return (
            0, 0x8000000000000000, 1, 0x8000000000000001,
            0x000FFFFFFFFFFFFF, 0x800FFFFFFFFFFFFF,
            0x0010000000000000, 0x8010000000000000,
            0x7FEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF,
            0x7FF0000000000000, 0xFFF0000000000000,
            0x7FF8000000000042, 0x7FF0000000000001,
            0x3FF0000000000000, 0xBFF0000000000000,
            0x4000000000000000, 0x4024000000000000,
            0x4034000000000000, 0x3FEFFFFFFFFFFFFF,
        )
    return (
        0, 1, mask, sign, sign - 1,
        0xAAAAAAAAAAAAAAAA & mask, 0x5555555555555555 & mask,
        0x0123456789ABCDEF & mask, 2, (mask - 1) & mask,
    )


def _pair_candidates(
    case: CaseDefinition,
    *,
    seed_text: str,
    element: str,
    lanes: int,
    standard: int,
    finite: bool = False,
    examples: Sequence[tuple[Sequence[int], Sequence[int]]] | None = None,
) -> Iterator[Candidate]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    width = int(element[1:])
    mask = (1 << width) - 1
    boundaries = _boundary_values(element)
    for index in range(standard):
        if examples is None:
            a = tuple(boundaries[(index + lane) % len(boundaries)] for lane in range(lanes))
            offset = 0 if index == 0 else index * lanes + 3
            b = tuple(boundaries[(offset + lane) % len(boundaries)] for lane in range(lanes))
        else:
            a, b = examples[index]
        item = _base(case, index, random=False, seed=seed_text)
        item["operands"] = {"a": vector(element, a), "b": vector(element, b)}
        yield item
    index = standard
    while True:
        def next_lane() -> int:
            bits = random.next() & mask
            if finite and element.startswith("f"):
                exponent_mask = ((1 << (8 if width == 32 else 11)) - 1) << (23 if width == 32 else 52)
                if bits & exponent_mask == exponent_mask:
                    bits ^= 1 << (23 if width == 32 else 52)
            return bits

        item = _base(case, index, random=True, seed=seed_text)
        environment = item["environment"]
        assert isinstance(environment, dict)
        environment["rounding"] = modes[random.next() % len(modes)]
        item["operands"] = {
            "a": vector(element, tuple(next_lane() for _ in range(lanes))),
            "b": vector(element, tuple(next_lane() for _ in range(lanes))),
        }
        yield item
        index += 1


def _unary_candidates(
    case: CaseDefinition,
    *,
    seed_text: str,
    element: str,
    lanes: int,
    standard: int,
    examples: Sequence[Sequence[int]] | None = None,
) -> Iterator[Candidate]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    width = int(element[1:])
    mask = (1 << width) - 1
    boundaries = _boundary_values(element)
    for index in range(standard):
        values = (
            tuple(boundaries[(index + lane) % len(boundaries)] for lane in range(lanes))
            if examples is None
            else tuple(examples[index])
        )
        item = _base(case, index, random=False, seed=seed_text)
        item["operands"] = {"a": vector(element, values)}
        yield item
    index = standard
    while True:
        item = _base(case, index, random=True, seed=seed_text)
        environment = item["environment"]
        assert isinstance(environment, dict)
        environment["rounding"] = modes[random.next() % len(modes)]
        item["operands"] = {
            "a": vector(element, tuple(random.next() & mask for _ in range(lanes)))
        }
        yield item
        index += 1


def _float_from_bits(element: str, bits: int) -> float:
    code = ">f" if element == "f32" else ">d"
    return struct.unpack(code, bits.to_bytes(int(element[1:]) // 8, "big"))[0]


def _float_to_bits(element: str, value: float) -> int:
    code = ">f" if element == "f32" else ">d"
    try:
        return int.from_bytes(struct.pack(code, value), "big")
    except OverflowError:
        width = int(element[1:])
        infinity = 0x7F800000 if width == 32 else 0x7FF0000000000000
        return infinity | ((1 << (width - 1)) if math.copysign(1.0, value) < 0.0 else 0)


def _round_ratio_even(numerator: int, denominator: int, shift: int) -> int:
    if shift >= 0:
        numerator <<= shift
    else:
        denominator <<= -shift
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder << 1
    if doubled > denominator or (doubled == denominator and quotient & 1):
        quotient += 1
    return quotient


def _divide_float_bits(element: str, left: int, right: int) -> int:
    """Return the SSE nearest-even quotient, including its NaN bit rules."""

    width = int(element[1:])
    fraction_width = 23 if width == 32 else 52
    exponent_width = 8 if width == 32 else 11
    bias = (1 << (exponent_width - 1)) - 1
    sign = (left ^ right) & (1 << (width - 1))
    fraction_mask = (1 << fraction_width) - 1
    exponent_max = (1 << exponent_width) - 1
    exponent_mask = exponent_max << fraction_width
    quiet_bit = 1 << (fraction_width - 1)
    indefinite = (1 << (width - 1)) | exponent_mask | quiet_bit

    left_exponent = (left & exponent_mask) >> fraction_width
    right_exponent = (right & exponent_mask) >> fraction_width
    left_fraction = left & fraction_mask
    right_fraction = right & fraction_mask
    left_nan = left_exponent == exponent_max and left_fraction != 0
    right_nan = right_exponent == exponent_max and right_fraction != 0
    if left_nan:
        return left | quiet_bit
    if right_nan:
        return right | quiet_bit

    left_zero = left_exponent == 0 and left_fraction == 0
    right_zero = right_exponent == 0 and right_fraction == 0
    left_infinite = left_exponent == exponent_max
    right_infinite = right_exponent == exponent_max
    if (left_zero and right_zero) or (left_infinite and right_infinite):
        return indefinite
    if left_infinite or right_zero:
        return sign | exponent_mask
    if left_zero or right_infinite:
        return sign

    precision = fraction_width + 1
    left_significand = left_fraction
    right_significand = right_fraction
    left_power = 1 - bias - fraction_width
    right_power = 1 - bias - fraction_width
    if left_exponent:
        left_significand |= 1 << fraction_width
        left_power = left_exponent - bias - fraction_width
    if right_exponent:
        right_significand |= 1 << fraction_width
        right_power = right_exponent - bias - fraction_width

    numerator = left_significand
    denominator = right_significand
    power = left_power - right_power
    if power >= 0:
        numerator <<= power
    else:
        denominator <<= -power

    binary_exponent = numerator.bit_length() - denominator.bit_length()
    if binary_exponent >= 0:
        if numerator < denominator << binary_exponent:
            binary_exponent -= 1
    elif numerator << -binary_exponent < denominator:
        binary_exponent -= 1

    minimum_normal = 1 - bias
    if binary_exponent >= minimum_normal:
        significand = _round_ratio_even(
            numerator, denominator, precision - 1 - binary_exponent
        )
        if significand == 1 << precision:
            significand >>= 1
            binary_exponent += 1
        if binary_exponent > bias:
            return sign | exponent_mask
        exponent = binary_exponent + bias
        return sign | (exponent << fraction_width) | (significand & fraction_mask)

    subnormal = _round_ratio_even(
        numerator, denominator, precision - 1 - minimum_normal
    )
    if subnormal == 0:
        return sign
    if subnormal >= 1 << fraction_width:
        return sign | (1 << fraction_width)
    return sign | subnormal


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
    examples: Sequence[BinaryExample] | None = None,
    *,
    standard: int = 8,
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
        if examples is None:
            yield from _pair_candidates(
                case,
                seed_text=seed_text,
                element=element,
                lanes=lanes,
                standard=standard,
            )
            return
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


def bitwise_case(case_id: str, shape: str, operation: str) -> FactoryResult:
    """Build a raw-bit vector operation, including vectors typed as floats."""

    element, _width, lanes, mask = _shape(shape)
    operations = {
        "&": lambda a, b: a & b,
        "|": lambda a, b: a | b,
        "^": lambda a, b: a ^ b,
        "~&": lambda a, b: (~a) & b,
    }
    try:
        apply = operations[operation]
    except KeyError as error:
        raise ValueError(f"unknown bitwise operation: {operation!r}") from error

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _pair_candidates(
            case, seed_text=seed_text, element=element, lanes=lanes, standard=8
        )

    def execute(record: Candidate) -> Candidate:
        output = tuple(
            apply(int(str(a), 16), int(str(b), 16)) & mask
            for a, b in zip(_lanes(record, "a"), _lanes(record, "b"), strict=True)
        )
        return {"return": vector(element, output)}

    return case_id, {"standard": 8}, candidates, execute


def float_binary_case(
    case_id: str, shape: str, operation: str, *, scalar_only: bool = False
) -> FactoryResult:
    """Build ``+``, ``-``, ``*`` or ``/`` for a packed or low-lane float vector."""

    element, _width, lanes, _mask = _shape(shape)
    if not element.startswith("f") or operation not in {"+", "-", "*", "/"}:
        raise ValueError(f"invalid float binary case: {shape!r} {operation!r}")

    examples = None
    if element == "f64" and lanes == 2 and operation == "+" and not scalar_only:
        examples = (
            ((0x3FF0000000000000, 0x4024000000000000), (0x4000000000000000, 0x4034000000000000)),
            ((0, 0x8000000000000000), (0, 0)),
            ((1, 0x000FFFFFFFFFFFFF), (0, 0)),
            ((0x0010000000000000, 0x7FEFFFFFFFFFFFFF), (0, 0)),
            ((0x7FF0000000000000, 0xFFF0000000000000), (0x3FF0000000000000, 0xBFF0000000000000)),
            ((0x7FF8000000000001, 0x7FF0000000000001), (0x3FF0000000000000, 0x3FF0000000000000)),
            ((0x7FEFFFFFFFFFFFFF, 0x7FEFFFFFFFFFFFFF), (0x7FEFFFFFFFFFFFFF, 0x7FEFFFFFFFFFFFFF)),
            ((0x3FF0000000000000, 0x3FF0000000000000), (0x3CA8000000000000, 0x3CA8000000000000)),
            ((0x8000000000000001, 0x800FFFFFFFFFFFFF), (0x8000000000000000, 0x8000000000000000)),
            ((0x8010000000000000, 0xFFEFFFFFFFFFFFFF), (0x8000000000000000, 0x8000000000000000)),
        )

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _pair_candidates(
            case,
            seed_text=seed_text,
            element=element,
            lanes=lanes,
            standard=14 if operation == "/" else 10,
            finite=True,
            examples=examples,
        )

    def apply(a: float, b: float) -> float:
        if operation == "+":
            return a + b
        if operation == "-":
            return a - b
        return a * b

    def execute(record: Candidate) -> Candidate:
        left = _lanes(record, "a")
        right = _lanes(record, "b")
        count = 1 if scalar_only else lanes
        if operation == "/":
            output = [
                _divide_float_bits(
                    element,
                    int(str(left[index]), 16),
                    int(str(right[index]), 16),
                )
                for index in range(count)
            ]
            if scalar_only:
                output.extend(int(str(value), 16) for value in left[1:])
            return {"return": vector(element, tuple(output))}
        output = [
            _float_to_bits(
                element,
                apply(
                    _float_from_bits(element, int(str(left[index]), 16)),
                    _float_from_bits(element, int(str(right[index]), 16)),
                ),
            )
            for index in range(count)
        ]
        if scalar_only:
            output.extend(int(str(value), 16) for value in left[1:])
        return {"return": vector(element, tuple(output))}

    return case_id, {"standard": 14 if operation == "/" else 10}, candidates, execute


def float_compare_case(
    case_id: str, shape: str, predicate: str, *, scalar_only: bool = False
) -> FactoryResult:
    """Build an SSE ordered/unordered packed or low-lane float comparison."""

    element, _width, lanes, mask = _shape(shape)
    predicates = {"==", "!=", "<", "<=", ">", ">=", "!<", "!<=", "!>", "!>=", "ord", "unord"}
    if not element.startswith("f") or predicate not in predicates:
        raise ValueError(f"invalid float comparison: {shape!r} {predicate!r}")

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _pair_candidates(
            case, seed_text=seed_text, element=element, lanes=lanes, standard=8
        )

    def matches(a_bits: int, b_bits: int) -> bool:
        a = _float_from_bits(element, a_bits)
        b = _float_from_bits(element, b_bits)
        unordered = math.isnan(a) or math.isnan(b)
        if predicate == "ord":
            return not unordered
        if predicate == "unord":
            return unordered
        if predicate == "==":
            return not unordered and a == b
        if predicate == "!=":
            return unordered or a != b
        ordered = {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}
        if predicate.startswith("!"):
            return unordered or not ordered[predicate[1:]]
        return not unordered and ordered[predicate]

    def execute(record: Candidate) -> Candidate:
        left = _lanes(record, "a")
        right = _lanes(record, "b")
        count = 1 if scalar_only else lanes
        output = [
            mask if matches(
                int(str(left[index]), 16), int(str(right[index]), 16)
            ) else 0
            for index in range(count)
        ]
        if scalar_only:
            output.extend(int(str(value), 16) for value in left[1:])
        return {"return": vector(element, tuple(output))}

    return case_id, {"standard": 8}, candidates, execute


def lanes_case(case_id: str, shape: str, pattern: str) -> FactoryResult:
    """Build a lane-only operation from a tiny map such as ``ziplo`` or ``b0 a1``."""

    element, _width, lanes, _mask = _shape(shape)
    if pattern == "ziplo":
        tokens = tuple(f"{source}{index}" for index in range(lanes // 2) for source in "ab")
    elif pattern == "ziphi":
        tokens = tuple(f"{source}{index}" for index in range(lanes // 2, lanes) for source in "ab")
    else:
        tokens = tuple(pattern.split())
    if len(tokens) != lanes:
        raise ValueError(f"lane map for {shape!r} must produce {lanes} lanes")
    binary = any(token.startswith("b") for token in tokens)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        pairs = _pair_candidates(
            case, seed_text=seed_text, element=element, lanes=lanes, standard=8
        )
        for item in pairs:
            if not binary:
                operands = item["operands"]
                assert isinstance(operands, dict)
                operands.pop("b")
            yield item

    def execute(record: Candidate) -> Candidate:
        sources = {"a": _lanes(record, "a")}
        if binary:
            sources["b"] = _lanes(record, "b")
        output = tuple(
            0 if token == "0" else int(str(sources[token[0]][int(token[1:])]), 16)
            for token in tokens
        )
        return {"return": vector(element, output)}

    return case_id, {"standard": 8}, candidates, execute


def immediate_shift_case(case_id: str, shape: str, kind: str) -> FactoryResult:
    """Build immediate lane or whole-register shifts from the YAML imm8 set."""

    element, width, lanes, mask = _shape(shape)
    kinds = {"<<", ">>", "s>>", "bytes<<", "bytes>>"}
    if kind not in kinds:
        raise ValueError(f"unknown immediate shift: {kind!r}")

    def allowed(case: CaseDefinition) -> list[int]:
        definitions = case.data["immediates"]
        assert isinstance(definitions, dict)
        definition = definitions["imm8"]
        assert isinstance(definition, dict)
        values = definition["values"]
        assert isinstance(values, list)
        return [int(value) for value in values]

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        counts = allowed(case)
        boundaries = _boundary_values(element)
        for index, count in enumerate(counts):
            values = tuple(boundaries[(index + lane) % len(boundaries)] for lane in range(lanes))
            item = _base(case, index, random=False, seed=seed_text)
            item["immediates"] = {"imm8": count}
            item["operands"] = {"a": vector(element, values)}
            yield item
        index = len(counts)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["immediates"] = {"imm8": counts[random.next() % len(counts)]}
            item["operands"] = {"a": vector(element, tuple(random.next() & mask for _ in range(lanes)))}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        immediates = record["immediates"]
        assert isinstance(immediates, dict)
        count = int(immediates["imm8"])
        source = [int(str(value), 16) for value in _lanes(record, "a")]
        if kind == "bytes<<":
            output = ([0] * count + source[:lanes - count]) if count < lanes else [0] * lanes
        elif kind == "bytes>>":
            output = (source[count:] + [0] * count) if count < lanes else [0] * lanes
        elif kind == "<<":
            output = [((value << count) & mask) if count < width else 0 for value in source]
        elif kind == ">>":
            output = [(value >> count) if count < width else 0 for value in source]
        else:
            output = [_signed(value, width) >> min(count, width - 1) for value in source]
        return {"return": vector(element, tuple(output))}

    standard = 8 if width == 32 and not kind.startswith("bytes") else 6
    return case_id, {"standard": standard}, candidates, execute


def pack_case(case_id: str, source_shape: str, target_shape: str) -> FactoryResult:
    """Build the three signed-source saturating pack instructions."""

    source, source_width, source_lanes, _source_mask = _shape(source_shape)
    target, target_width, target_lanes, target_mask = _shape(target_shape)
    if not source.startswith("i") or target_lanes != source_lanes * 2:
        raise ValueError(f"invalid pack shape: {source_shape!r} -> {target_shape!r}")
    lower = -(1 << (target_width - 1)) if target.startswith("i") else 0
    upper = (1 << (target_width - 1)) - 1 if target.startswith("i") else target_mask

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _pair_candidates(
            case, seed_text=seed_text, element=source, lanes=source_lanes, standard=8
        )

    def execute(record: Candidate) -> Candidate:
        values = [
            _signed(int(str(bits), 16), source_width)
            for bits in [*_lanes(record, "a"), *_lanes(record, "b")]
        ]
        return {"return": vector(target, tuple(min(upper, max(lower, value)) for value in values))}

    return case_id, {"standard": 8}, candidates, execute


def reduce_case(case_id: str, shape: str, operation: str) -> FactoryResult:
    """Build the three binary operations that reduce groups of input lanes."""

    element, width, lanes, _mask = _shape(shape)
    operations = {"madd", "sad8", "even*"}
    if operation not in operations:
        raise ValueError(f"unknown reduction operation: {operation!r}")

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _pair_candidates(
            case, seed_text=seed_text, element=element, lanes=lanes, standard=4
        )

    def execute(record: Candidate) -> Candidate:
        a = [int(str(value), 16) for value in _lanes(record, "a")]
        b = [int(str(value), 16) for value in _lanes(record, "b")]
        if operation == "madd":
            products = [_signed(x, width) * _signed(y, width) for x, y in zip(a, b, strict=True)]
            return {"return": vector("i32", tuple(products[index] + products[index + 1] for index in range(0, lanes, 2)))}
        if operation == "sad8":
            differences = [abs(x - y) for x, y in zip(a, b, strict=True)]
            return {"return": vector("u64", tuple(sum(differences[index:index + 8]) for index in range(0, lanes, 8)))}
        return {"return": vector("u64", tuple(a[index] * b[index] for index in range(0, lanes, 2)))}

    return case_id, {"standard": 4}, candidates, execute


def scalar_vector_case(case_id: str, shape: str, mode: str) -> FactoryResult:
    """Build scalar-to-vector constructors: broadcast or low-lane insertion."""

    element, _width, lanes, mask = _shape(shape)
    if mode not in {"splat", "low"}:
        raise ValueError(f"unknown scalar vector mode: {mode!r}")
    boundaries = _boundary_values(element)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        modes = rounding_modes(case)
        for index, value in enumerate(boundaries):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {"value": scalar(element, value)}
            yield item
        index = len(boundaries)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            environment = item["environment"]
            assert isinstance(environment, dict)
            environment["rounding"] = modes[random.next() % len(modes)]
            item["operands"] = {"value": scalar(element, random.next() & mask)}
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        value = _bits(record, "value")
        output = (value,) * lanes if mode == "splat" else (value,) + (0,) * (lanes - 1)
        return {"return": vector(element, output)}

    return case_id, {"standard": len(boundaries)}, candidates, execute


def _round_shift_even(value: int, shift: int) -> int:
    if shift <= 0:
        return value << -shift
    quotient = value >> shift
    remainder = value - (quotient << shift)
    halfway = 1 << (shift - 1)
    return quotient + int(remainder > halfway or (remainder == halfway and bool(quotient & 1)))


def _f64_to_f32(bits: int) -> int:
    sign = (bits >> 63) << 31
    exponent = (bits >> 52) & 0x7FF
    fraction = bits & 0x000FFFFFFFFFFFFF
    if exponent == 0x7FF:
        return sign | 0x7F800000 if fraction == 0 else sign | 0x7F800000 | (fraction >> 29) | 0x00400000
    if exponent == 0:
        return sign
    unbiased = exponent - 1023
    significand = (1 << 52) | fraction
    if unbiased > 127:
        return sign | 0x7F800000
    if unbiased >= -126:
        rounded = _round_shift_even(significand, 29)
        if rounded == 1 << 24:
            rounded >>= 1
            unbiased += 1
            if unbiased > 127:
                return sign | 0x7F800000
        return sign | ((unbiased + 127) << 23) | (rounded & 0x007FFFFF)
    rounded = _round_shift_even(significand, -unbiased - 97)
    return sign | (0x00800000 if rounded >= 1 << 23 else rounded)


def _f32_to_f64(bits: int) -> int:
    sign = (bits >> 31) << 63
    exponent = (bits >> 23) & 0xFF
    fraction = bits & 0x7FFFFF
    if exponent == 0xFF:
        return sign | 0x7FF0000000000000 if fraction == 0 else sign | 0x7FF0000000000000 | (fraction << 29) | (1 << 51)
    if exponent != 0:
        return sign | ((exponent + 896) << 52) | (fraction << 29)
    if fraction == 0:
        return sign
    leading = fraction.bit_length() - 1
    return sign | ((leading + 874) << 52) | ((fraction - (1 << leading)) << (52 - leading))


def _i32_to_f32(bits: int) -> int:
    value = _signed(bits, 32)
    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    leading = magnitude.bit_length() - 1
    if leading <= 23:
        rounded = magnitude << (23 - leading)
    else:
        rounded = _round_shift_even(magnitude, leading - 23)
        if rounded == 1 << 24:
            rounded >>= 1
            leading += 1
    return sign | ((leading + 127) << 23) | (rounded & 0x007FFFFF)


def _float_to_integer(
    element: str, bits: int, *, width: int, truncate: bool
) -> int:
    value = _float_from_bits(element, bits)
    indefinite = 1 << (width - 1)
    if not math.isfinite(value):
        return indefinite
    rounded = math.trunc(value) if truncate else round(value)
    if rounded < -(1 << (width - 1)) or rounded > (1 << (width - 1)) - 1:
        return indefinite
    return rounded & ((1 << width) - 1)


def _float_to_i32(element: str, bits: int, *, truncate: bool) -> int:
    return _float_to_integer(element, bits, width=32, truncate=truncate)


def _conversion_examples(source_shape: str, target_shape: str, truncate: bool) -> tuple[tuple[int, ...], ...]:
    if (source_shape, target_shape) == ("f64x2", "f32x4"):
        return (
            (0, 0x8000000000000000), (0x3FF0000000000000, 0xC004000000000000),
            (0x47EFFFFFE0000000, 0xC7EFFFFFE0000000), (0x3810000000000000, 0xB810000000000000),
            (0x380FFFFFC0000000, 0xB80FFFFFC0000000), (0x36A0000000000000, 0xB6A0000000000000),
            (0x3690000000000000, 0xB690000000000000), (0x3690000000000001, 0xB690000000000001),
            (0x3FF0000010000000, 0xBFF0000010000000), (0x7FF0000000000000, 0xFFF0000000000000),
            (0x7FF8000000000042, 0xFFF8000000000043), (0x7FF0000000000001, 0xFFF0000000000002),
        )
    if (source_shape, target_shape) == ("f32x4", "f64x2"):
        return (
            (0, 0x80000000, 0x7FC00001, 0xFFC00001), (0x3F800000, 0xC0200000, 0xAAAAAAAA, 0x55555555),
            (1, 0x80000001, 0, 0), (0x007FFFFF, 0x807FFFFF, 0, 0),
            (0x00800000, 0x80800000, 0, 0), (0x7F7FFFFF, 0xFF7FFFFF, 0, 0),
            (0x7F800000, 0xFF800000, 0, 0), (0x7FC00042, 0xFFC00043, 0, 0),
            (0x7F800001, 0xFF800002, 0, 0), (0x3EAAAAAB, 0xBEAAAAAB, 0x7F800001, 0xFF800002),
        )
    if (source_shape, target_shape) == ("i32x4", "f32x4"):
        return (
            (0, 1, 0xFFFFFFFF, 0x80000000), (0x7FFFFFFF, 0x80000000, 0x40000000, 0xC0000000),
            (0x00FFFFFF, 0x01000000, 0x01000001, 0x01000003), (0xFF000001, 0xFF000000, 0xFEFFFFFF, 0xFEFFFFFD),
            (0x7FFFFF80, 0x7FFFFF81, 0x80000080, 0x8000007F), (0x55555555, 0xAAAAAAAA, 0x33333333, 0xCCCCCCCC),
            (0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210), (2, 3, 4, 5),
        )
    if (source_shape, target_shape) == ("i32x4", "f64x2"):
        return (
            (0, 0, 0, 0), (1, 0xFFFFFFFF, 0, 0), (0x7FFFFFFF, 0x80000000, 0, 0),
            (0x01000001, 0xFEFFFFFF, 0, 0), (0x40000000, 0xC0000000, 0, 0),
            (0x55555555, 0xAAAAAAAA, 0, 0), (0, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000),
            (0x12345678, 0x89ABCDEF, 0xDEADBEEF, 0xCAFEBABE),
        )
    source, _width, lanes, _mask = _shape(source_shape)
    values = _boundary_values(source)
    return tuple(tuple(values[(index + lane) % len(values)] for lane in range(lanes)) for index in range(10 if source == "f64" else 8))


def conversion_case(
    case_id: str, source_shape: str, target_shape: str, *, truncate: bool = False
) -> FactoryResult:
    """Build the numeric SSE2 conversions while keeping the exact oracle centralized."""

    source, _source_width, source_lanes, _source_mask = _shape(source_shape)
    target, _target_width, target_lanes, _target_mask = _shape(target_shape)
    examples = _conversion_examples(source_shape, target_shape, truncate)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _unary_candidates(
            case, seed_text=seed_text, element=source, lanes=source_lanes,
            standard=len(examples), examples=examples,
        )

    def execute(record: Candidate) -> Candidate:
        lanes = [int(str(value), 16) for value in _lanes(record, "a")]
        if (source, target) == ("f64", "f32"):
            output = [_f64_to_f32(value) for value in lanes] + [0, 0]
        elif (source, target) == ("f32", "f64"):
            output = [_f32_to_f64(value) for value in lanes[:target_lanes]]
        elif (source, target) == ("i32", "f32"):
            output = [_i32_to_f32(value) for value in lanes]
        elif (source, target) == ("i32", "f64"):
            output = [_float_to_bits("f64", float(_signed(value, 32))) for value in lanes[:target_lanes]]
        elif source.startswith("f") and target == "i32":
            output = [_float_to_i32(source, value, truncate=truncate) for value in lanes]
            output.extend([0] * (target_lanes - len(output)))
        else:
            raise ValueError(f"unsupported conversion: {source_shape!r} -> {target_shape!r}")
        return {"return": vector(target, tuple(output))}

    return case_id, {"standard": len(examples)}, candidates, execute


def scalar_conversion_case(
    case_id: str, source_shape: str, target_shape: str
) -> FactoryResult:
    """Convert one scalar into lane zero and preserve the target's other lanes."""

    target, _target_width, target_lanes, target_mask = _shape(target_shape)
    if "x" in source_shape:
        source, _source_width, source_lanes, source_mask = _shape(source_shape)
        source_examples = _conversion_examples(source_shape, target_shape, False)
    else:
        source = source_shape
        source_lanes = 1
        source_mask = (1 << int(source[1:])) - 1
        source_examples = tuple((value,) for value in _boundary_values(source))
    supported = {
        ("f64", "f32"),
        ("f32", "f64"),
        ("i32", "f32"),
        ("i32", "f64"),
        ("i64", "f64"),
    }
    if (source, target) not in supported:
        raise ValueError(f"unsupported scalar conversion: {source_shape!r} -> {target_shape!r}")
    target_boundaries = _boundary_values(target)
    standard = len(source_examples)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        modes = rounding_modes(case)
        for index, source_values in enumerate(source_examples):
            item = _base(case, index, random=False, seed=seed_text)
            preserved = tuple(
                target_boundaries[(index + lane) % len(target_boundaries)]
                for lane in range(target_lanes)
            )
            operands: dict[str, JSONValue] = {"a": vector(target, preserved)}
            if source_lanes == 1:
                operands["value"] = scalar(source, source_values[0])
            else:
                operands["b"] = vector(source, source_values)
            item["operands"] = operands
            yield item
        index = standard
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            environment = item["environment"]
            assert isinstance(environment, dict)
            environment["rounding"] = modes[random.next() % len(modes)]
            operands = {
                "a": vector(
                    target,
                    tuple(random.next() & target_mask for _ in range(target_lanes)),
                )
            }
            if source_lanes == 1:
                operands["value"] = scalar(source, random.next() & source_mask)
            else:
                operands["b"] = vector(
                    source,
                    tuple(random.next() & source_mask for _ in range(source_lanes)),
                )
            item["operands"] = operands
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        output = [int(str(value), 16) for value in _lanes(record, "a")]
        source_bits = (
            _bits(record, "value")
            if source_lanes == 1
            else int(str(_lanes(record, "b")[0]), 16)
        )
        if (source, target) == ("f64", "f32"):
            converted = _f64_to_f32(source_bits)
        elif (source, target) == ("f32", "f64"):
            converted = _f32_to_f64(source_bits)
        elif (source, target) == ("i32", "f32"):
            converted = _i32_to_f32(source_bits)
        else:
            converted = _float_to_bits(target, float(_signed(source_bits, int(source[1:]))))
        output[0] = converted
        return {"return": vector(target, tuple(output))}

    return case_id, {"standard": standard}, candidates, execute


def float_to_scalar_case(
    case_id: str,
    source_shape: str,
    target: str,
    *,
    truncate: bool = False,
) -> FactoryResult:
    """Convert the low float lane to a signed scalar integer."""

    source, _source_width, source_lanes, source_mask = _shape(source_shape)
    if source not in {"f32", "f64"} or target not in {"i32", "i64"}:
        raise ValueError(f"unsupported float scalar conversion: {source_shape!r} -> {target!r}")
    if source == "f32" and target == "i64":
        raise ValueError("the official scalar conversion family does not expose f32 to i64")
    target_width = int(target[1:])
    numeric = (
        0.0, -0.0, 0.5, -0.5, 1.5, 2.5, -1.5, -2.5,
        float((1 << (target_width - 1)) - (1024 if target_width == 64 else 128)),
        float(-(1 << (target_width - 1))),
        float(1 << (target_width - 1)),
    )
    special = (
        0x7F800000, 0xFF800000, 0x7FC00042, 0x7F800001
    ) if source == "f32" else (
        0x7FF0000000000000,
        0xFFF0000000000000,
        0x7FF8000000000042,
        0x7FF0000000000001,
    )
    low_values = tuple(_float_to_bits(source, value) for value in numeric) + special
    boundaries = _boundary_values(source)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        modes = rounding_modes(case)
        for index, low in enumerate(low_values):
            lanes = (low,) + tuple(
                boundaries[(index + lane) % len(boundaries)]
                for lane in range(1, source_lanes)
            )
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {"a": vector(source, lanes)}
            yield item
        index = len(low_values)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            environment = item["environment"]
            assert isinstance(environment, dict)
            environment["rounding"] = modes[random.next() % len(modes)]
            item["operands"] = {
                "a": vector(
                    source,
                    tuple(random.next() & source_mask for _ in range(source_lanes)),
                )
            }
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        low = int(str(_lanes(record, "a")[0]), 16)
        converted = _float_to_integer(
            source, low, width=target_width, truncate=truncate
        )
        return {"return": scalar(target, converted)}

    return case_id, {"standard": len(low_values)}, candidates, execute


def shuffle_case(case_id: str, shape: str, kind: str) -> FactoryResult:
    """Build immediate shuffles: whole-vector, two-source, pair, low or high half."""

    element, _width, lanes, mask = _shape(shape)
    repeats = {"all": 4, "two": 2, "pair": 4, "low": 4, "high": 4}
    if kind not in repeats:
        raise ValueError(f"unknown shuffle kind: {kind!r}")

    def allowed(case: CaseDefinition) -> list[int]:
        definitions = case.data["immediates"]
        assert isinstance(definitions, dict)
        definition = definitions["imm8"]
        assert isinstance(definition, dict)
        values = definition["values"]
        assert isinstance(values, list)
        return [int(value) for value in values]

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        modes = rounding_modes(case)
        controls = allowed(case)
        boundaries = _boundary_values(element)
        index = 0
        for control in controls:
            for repeat in range(repeats[kind]):
                a = tuple(boundaries[(index + lane) % len(boundaries)] for lane in range(lanes))
                item = _base(case, index, random=False, seed=seed_text)
                item["immediates"] = {"imm8": control}
                operands: dict[str, JSONValue] = {"a": vector(element, a)}
                if kind in {"two", "pair"}:
                    b = tuple(boundaries[(index + lanes + lane) % len(boundaries)] for lane in range(lanes))
                    operands["b"] = vector(element, b)
                item["operands"] = operands
                yield item
                index += 1
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            environment = item["environment"]
            assert isinstance(environment, dict)
            environment["rounding"] = modes[random.next() % len(modes)]
            item["immediates"] = {"imm8": controls[random.next() % len(controls)]}
            operands = {"a": vector(element, tuple(random.next() & mask for _ in range(lanes)))}
            if kind in {"two", "pair"}:
                operands["b"] = vector(element, tuple(random.next() & mask for _ in range(lanes)))
            item["operands"] = operands
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        immediates = record["immediates"]
        assert isinstance(immediates, dict)
        control = int(immediates["imm8"])
        a = [int(str(value), 16) for value in _lanes(record, "a")]
        if kind == "all":
            output = [a[(control >> (2 * lane)) & 3] for lane in range(4)]
        elif kind == "two":
            b = [int(str(value), 16) for value in _lanes(record, "b")]
            output = [a[control & 3], a[(control >> 2) & 3], b[(control >> 4) & 3], b[(control >> 6) & 3]]
        elif kind == "pair":
            b = [int(str(value), 16) for value in _lanes(record, "b")]
            output = [a[control & 1], b[(control >> 1) & 1]]
        elif kind == "low":
            output = [a[(control >> (2 * lane)) & 3] for lane in range(4)] + a[4:]
        else:
            output = a[:4] + [a[4 + ((control >> (2 * lane)) & 3)] for lane in range(4)]
        return {"return": vector(element, tuple(output))}

    standard = {"all": 16, "two": 12, "pair": 16, "low": 20, "high": 20}[kind]
    return case_id, {"standard": standard}, candidates, execute


def movemask_case(case_id: str, shape: str) -> FactoryResult:
    element, width, lanes, _mask = _shape(shape)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _unary_candidates(
            case, seed_text=seed_text, element=element, lanes=lanes, standard=8
        )

    def execute(record: Candidate) -> Candidate:
        result = sum(
            ((int(str(bits), 16) >> (width - 1)) & 1) << lane
            for lane, bits in enumerate(_lanes(record, "a"))
        )
        return {"return": scalar("i32", result)}

    return case_id, {"standard": 8}, candidates, execute


def sqrt_case(
    case_id: str, shape: str, *, scalar_only: bool = False
) -> FactoryResult:
    element, width, lanes, _mask = _shape(shape)
    if element not in {"f32", "f64"}:
        raise ValueError("sqrt_case requires an f32 or f64 vector")

    sign = 1 << (width - 1)
    if width == 32:
        exponent_mask = 0x7F800000
        fraction_mask = 0x007FFFFF
        quiet_bit = 0x00400000
        indefinite = 0xFFC00000
    else:
        exponent_mask = 0x7FF0000000000000
        fraction_mask = 0x000FFFFFFFFFFFFF
        quiet_bit = 0x0008000000000000
        indefinite = 0xFFF8000000000000

    standard = 10 if width == 32 else 14

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _unary_candidates(
            case, seed_text=seed_text, element=element, lanes=lanes, standard=standard
        )

    def sqrt_bits(bits: int) -> int:
        magnitude = bits & (sign - 1)
        if bits & exponent_mask == exponent_mask and bits & fraction_mask:
            return bits | quiet_bit
        if bits & sign and magnitude:
            return indefinite
        if magnitude == 0 or bits == exponent_mask:
            return bits
        return _float_to_bits(element, math.sqrt(_float_from_bits(element, bits)))

    def execute(record: Candidate) -> Candidate:
        source = _lanes(record, "a")
        count = 1 if scalar_only else lanes
        output = [sqrt_bits(int(str(source[index]), 16)) for index in range(count)]
        if scalar_only:
            output.extend(int(str(value), 16) for value in source[1:])
        return {"return": vector(element, tuple(output))}

    return case_id, {"standard": standard}, candidates, execute


def loadu_f64_case(case_id: str) -> FactoryResult:
    """Build the unaligned two-lane load, including guard bytes and buffer echo."""

    structured = (
        ((0x3FF0000000000000, 0xC004000000000000), 0),
        ((0x0123456789ABCDEF, 0xFEDCBA9876543210), 1),
        ((0, 0x8000000000000000), 3),
        ((1, 0x800FFFFFFFFFFFFF), 7),
        ((0x7FF0000000000000, 0xFFF0000000000000), 8),
        ((0x7FF8000000000042, 0xFFF0000000000001), 9),
        ((0xFFFFFFFFFFFFFFFF, 0), 15),
        ((0x0011223344556677, 0x8899AABBCCDDEEFF), 5),
    )

    def record(raw: bytes, offset: int, generation: dict[str, JSONValue], rounding: str) -> Candidate:
        return {
            "buffers": {"buf0": {"alignment": 1, "bytes": f"0x{raw.hex()}"}},
            "environment": {"fp_mode": "ieee", "rounding": rounding},
            "generation": generation,
            "operands": {"source": {"buffer": "buf0", "offset": offset}},
        }

    def guarded(values: tuple[int, int], offset: int) -> bytes:
        prefix = bytes((0xA0 + index) & 0xFF for index in range(offset))
        payload = b"".join(value.to_bytes(8, "little") for value in values)
        return prefix + payload + bytes((0xD0 + index) & 0xFF for index in range(3))

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        modes = rounding_modes(case)
        for index, (values, offset) in enumerate(structured):
            yield record(guarded(values, offset), offset, {"class": "boundary"}, modes[index % len(modes)])
        while True:
            raw = b"".join(random.next().to_bytes(8, "little") for _ in range(6))
            offset = random.next() % 33
            yield record(raw, offset, {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, modes[random.next() % len(modes)])

    def execute(candidate: Candidate) -> Candidate:
        buffers = candidate["buffers"]
        operands = candidate["operands"]
        assert isinstance(buffers, dict) and isinstance(operands, dict)
        pointer = operands["source"]
        assert isinstance(pointer, dict)
        allocation = buffers[str(pointer["buffer"])]
        assert isinstance(allocation, dict)
        raw = bytes.fromhex(str(allocation["bytes"])[2:])
        offset = int(pointer["offset"])
        loaded = raw[offset:offset + 16]
        observed = {
            name: {"byte_offset": 0, "bytes": str(value["bytes"])}
            for name, value in buffers.items() if isinstance(value, dict)
        }
        return {
            "buffers": observed,
            "return": vector("f64", tuple(int.from_bytes(loaded[start:start + 8], "little") for start in (0, 8))),
        }

    return case_id, {"standard": len(structured)}, candidates, execute


def memory_load_case(case_id: str, shape: str, mode: str) -> FactoryResult:
    """Build scalar, broadcast, preserving, zeroing, and reverse memory loads."""

    element, width, lanes, mask = _shape(shape)
    supported = {
        ("f32x4", "scalar"),
        ("f32x4", "broadcast"),
        ("f32x4", "all"),
        ("f32x4", "reverse"),
        ("f64x2", "scalar"),
        ("f64x2", "broadcast"),
        ("f64x2", "low"),
        ("f64x2", "high"),
        ("f64x2", "reverse"),
        ("i32x4", "all"),
        ("i64x2", "scalar"),
    }
    if (shape, mode) not in supported:
        raise ValueError(f"unsupported memory load: {shape!r} {mode!r}")
    byte_width = width // 8
    loaded_lanes = lanes if mode in {"all", "reverse"} else 1
    alignment = 16 if mode == "reverse" else 1
    boundaries = _boundary_values(element)
    standard = 8

    def make_record(
        case: CaseDefinition,
        index: int,
        *,
        raw: bytes,
        offset: int,
        preserved: tuple[int, ...],
        random_record: bool,
        seed_text: str,
    ) -> Candidate:
        item = _base(
            case, index, random=random_record, seed=seed_text
        )
        item["buffers"] = {
            "buf0": {"alignment": alignment, "bytes": f"0x{raw.hex()}"}
        }
        operands: dict[str, JSONValue] = {
            "source": {"buffer": "buf0", "offset": offset}
        }
        if mode in {"low", "high"}:
            operands["a"] = vector(element, preserved)
        item["operands"] = operands
        return item

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        for index in range(standard):
            offset = 0 if alignment > 1 else (0, 1, 3, 7)[index % 4]
            values = tuple(
                boundaries[(index + lane) % len(boundaries)]
                for lane in range(loaded_lanes)
            )
            payload = b"".join(
                value.to_bytes(byte_width, "little") for value in values
            )
            raw = bytes((0xA0 + n) & 0xFF for n in range(offset)) + payload
            raw += bytes((0xD0 + n) & 0xFF for n in range(5))
            preserved = tuple(
                boundaries[(index + lane + 3) % len(boundaries)]
                for lane in range(lanes)
            )
            yield make_record(
                case,
                index,
                raw=raw,
                offset=offset,
                preserved=preserved,
                random_record=False,
                seed_text=seed_text,
            )
        index = standard
        while True:
            offset = 0 if alignment > 1 else random.next() % 17
            raw = b"".join(random.next().to_bytes(8, "little") for _ in range(4))
            preserved = tuple(random.next() & mask for _ in range(lanes))
            yield make_record(
                case,
                index,
                raw=raw,
                offset=offset,
                preserved=preserved,
                random_record=True,
                seed_text=seed_text,
            )
            index += 1

    def execute(candidate: Candidate) -> Candidate:
        buffers = candidate["buffers"]
        operands = candidate["operands"]
        assert isinstance(buffers, dict) and isinstance(operands, dict)
        pointer = operands["source"]
        assert isinstance(pointer, dict)
        allocation = buffers[str(pointer["buffer"])]
        assert isinstance(allocation, dict)
        raw = bytes.fromhex(str(allocation["bytes"])[2:])
        offset = int(pointer["offset"])
        loaded = tuple(
            int.from_bytes(
                raw[offset + lane * byte_width:offset + (lane + 1) * byte_width],
                "little",
            )
            for lane in range(loaded_lanes)
        )
        if mode == "reverse":
            output = tuple(reversed(loaded))
        elif mode == "all":
            output = loaded
        elif mode == "broadcast":
            output = (loaded[0],) * lanes
        elif mode in {"low", "high"}:
            preserved = tuple(int(str(value), 16) for value in _lanes(candidate, "a"))
            output = (loaded[0], preserved[1]) if mode == "low" else (preserved[0], loaded[0])
        else:
            output = (loaded[0],) + (0,) * (lanes - 1)
        observed = {
            name: {"byte_offset": 0, "bytes": str(value["bytes"])}
            for name, value in buffers.items()
            if isinstance(value, dict)
        }
        return {"buffers": observed, "return": vector(element, output)}

    return case_id, {"standard": standard}, candidates, execute


def memory_store_case(case_id: str, shape: str, mode: str) -> FactoryResult:
    """Build low-lane, high-lane, and reverse-order memory stores."""

    element, width, lanes, mask = _shape(shape)
    supported = {
        ("f32x4", "low"),
        ("f32x4", "all"),
        ("f32x4", "reverse"),
        ("f64x2", "low"),
        ("f64x2", "high"),
        ("f64x2", "all"),
        ("f64x2", "reverse"),
        ("i32x4", "all"),
        ("i64x2", "low"),
    }
    if (shape, mode) not in supported:
        raise ValueError(f"unsupported memory store: {shape!r} {mode!r}")
    byte_width = width // 8
    stored_lanes = lanes if mode in {"all", "reverse"} else 1
    alignment = 16 if mode == "reverse" else 1
    boundaries = _boundary_values(element)
    standard = 8

    def make_record(
        case: CaseDefinition,
        index: int,
        *,
        raw: bytes,
        offset: int,
        values: tuple[int, ...],
        random_record: bool,
        seed_text: str,
    ) -> Candidate:
        item = _base(case, index, random=random_record, seed=seed_text)
        item["buffers"] = {
            "buf0": {"alignment": alignment, "bytes": f"0x{raw.hex()}"}
        }
        item["operands"] = {
            "destination": {"buffer": "buf0", "offset": offset},
            "a": vector(element, values),
        }
        return item

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        write_size = stored_lanes * byte_width
        for index in range(standard):
            offset = 0 if alignment > 1 else (0, 1, 3, 7)[index % 4]
            raw = bytes(
                (0x40 + index * 17 + byte) & 0xFF
                for byte in range(offset + write_size + 5)
            )
            values = tuple(
                boundaries[(index + lane) % len(boundaries)]
                for lane in range(lanes)
            )
            yield make_record(
                case,
                index,
                raw=raw,
                offset=offset,
                values=values,
                random_record=False,
                seed_text=seed_text,
            )
        index = standard
        while True:
            offset = 0 if alignment > 1 else random.next() % (33 - write_size)
            raw = b"".join(random.next().to_bytes(8, "little") for _ in range(4))
            values = tuple(random.next() & mask for _ in range(lanes))
            yield make_record(
                case,
                index,
                raw=raw,
                offset=offset,
                values=values,
                random_record=True,
                seed_text=seed_text,
            )
            index += 1

    def execute(candidate: Candidate) -> Candidate:
        buffers = candidate["buffers"]
        operands = candidate["operands"]
        assert isinstance(buffers, dict) and isinstance(operands, dict)
        pointer = operands["destination"]
        assert isinstance(pointer, dict)
        buffer_id = str(pointer["buffer"])
        allocation = buffers[buffer_id]
        assert isinstance(allocation, dict)
        raw = bytearray.fromhex(str(allocation["bytes"])[2:])
        offset = int(pointer["offset"])
        values = tuple(int(str(value), 16) for value in _lanes(candidate, "a"))
        selected = (
            tuple(reversed(values))
            if mode == "reverse"
            else values
            if mode == "all"
            else (values[1],)
            if mode == "high"
            else (values[0],)
        )
        payload = b"".join(
            value.to_bytes(byte_width, "little") for value in selected
        )
        raw[offset:offset + len(payload)] = payload
        observed = {
            name: {
                "byte_offset": 0,
                "bytes": f"0x{bytes(raw).hex()}" if name == buffer_id else str(value["bytes"]),
            }
            for name, value in buffers.items()
            if isinstance(value, dict)
        }
        return {"buffers": observed}

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
    boundaries = _boundary_values(element)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        for index in range(len(boundaries)):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {
                name: scalar(element, boundaries[(index + lane) % len(boundaries)])
                for lane, name in enumerate(argument_names)
            }
            yield item
        index = len(boundaries)
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

    return case_id, {"standard": len(boundaries)}, candidates, execute


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
    sign_bit = 1 << (source_width - 1)

    def repeat(*values: int) -> tuple[int, ...]:
        return tuple(values[index % len(values)] & source_mask for index in range(source_lanes))

    structured = (
        repeat(0, sign_bit),
        repeat(1, source_mask),
        repeat(source_mask, 0),
        repeat(sign_bit - 1, sign_bit),
        repeat(0xAAAAAAAAAAAAAAAA, 0x5555555555555555),
        repeat(0x0123456789ABCDEF, 0xFEDCBA9876543210),
        repeat(0x7FF0000000000000, 0xFFF0000000000000),
        repeat(0x7FF8000000000042, 0x7FF0000000000001),
    )

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
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

    return case_id, {"standard": len(structured)}, candidates, execute


def minmax_float_case(
    case_id: str, shape: str, kind: str, *, scalar_only: bool = False
) -> FactoryResult:
    element, _width, lanes, _mask = _shape(shape)
    if not element.startswith("f") or kind not in {"min", "max"}:
        raise ValueError(f"invalid float min/max case: {shape!r} {kind!r}")

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        yield from _pair_candidates(
            case, seed_text=seed_text, element=element, lanes=lanes, standard=10
        )

    def execute(record: Candidate) -> Candidate:
        output: list[int] = []
        left = _lanes(record, "a")
        right = _lanes(record, "b")
        count = 1 if scalar_only else lanes
        for index in range(count):
            a_raw, b_raw = left[index], right[index]
            a_bits, b_bits = int(str(a_raw), 16), int(str(b_raw), 16)
            a = _float_from_bits(element, a_bits)
            b = _float_from_bits(element, b_bits)
            if math.isnan(a) or math.isnan(b) or a == b:
                output.append(b_bits)
            elif (kind == "min" and a < b) or (kind == "max" and a > b):
                output.append(a_bits)
            else:
                output.append(b_bits)
        if scalar_only:
            output.extend(int(str(value), 16) for value in left[1:])
        return {"return": vector(element, tuple(output))}

    return case_id, {"standard": 10}, candidates, execute


def minmax_f64_case(case_id: str, kind: str) -> FactoryResult:
    return minmax_float_case(case_id, "f64x2", kind)


def _comi_float_case(
    case_id: str,
    shape: str,
    predicate: str,
    structured: tuple[tuple[int, int], ...],
) -> FactoryResult:
    element, _width, lanes, mask = _shape(shape)

    def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[Candidate]:
        random = SplitMix64(int(seed_text, 16))
        for index, (a, b) in enumerate(structured):
            item = _base(case, index, random=False, seed=seed_text)
            item["operands"] = {
                "a": vector(
                    element,
                    (a,) + tuple(random.next() & mask for _ in range(1, lanes)),
                ),
                "b": vector(
                    element,
                    (b,) + tuple(random.next() & mask for _ in range(1, lanes)),
                ),
            }
            yield item
        index = len(structured)
        while True:
            item = _base(case, index, random=True, seed=seed_text)
            item["operands"] = {
                "a": vector(
                    element, tuple(random.next() & mask for _ in range(lanes))
                ),
                "b": vector(
                    element, tuple(random.next() & mask for _ in range(lanes))
                ),
            }
            yield item
            index += 1

    def execute(record: Candidate) -> Candidate:
        a_bits = int(str(_lanes(record, "a")[0]), 16)
        b_bits = int(str(_lanes(record, "b")[0]), 16)
        a = _float_from_bits(element, a_bits)
        b = _float_from_bits(element, b_bits)
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


def comi_f32_case(case_id: str, predicate: str) -> FactoryResult:
    structured = (
        (0x00000000, 0x80000000),
        (0x3F800000, 0x40000000),
        (0x40000000, 0x3F800000),
        (0x7FC00042, 0x3F800000),
        (0x3F800000, 0x7F800001),
        (0x7F800000, 0x7F800000),
        (0xFF800000, 0x7F800000),
        (0xBF800000, 0xBF800000),
    )
    return _comi_float_case(case_id, "f32x4", predicate, structured)


def comi_f64_case(case_id: str, predicate: str) -> FactoryResult:
    structured = (
        (0x0000000000000000, 0x8000000000000000),
        (0x3FF0000000000000, 0x4000000000000000),
        (0x4000000000000000, 0x3FF0000000000000),
        (0x7FF8000000000042, 0x3FF0000000000000),
    )
    return _comi_float_case(case_id, "f64x2", predicate, structured)
