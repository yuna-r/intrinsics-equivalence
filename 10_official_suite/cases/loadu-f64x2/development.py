"""Development generator and executable model for _mm_loadu_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes


CASE_ID = "sse2.loadu.f64x2.default"
MINIMUM_COUNTS = {"standard": 8}


def _record(
    raw: bytes,
    offset: int,
    generation: dict[str, JSONValue],
    rounding: str,
) -> dict[str, JSONValue]:
    return {
        "buffers": {"buf0": {"alignment": 1, "bytes": f"0x{raw.hex()}"}},
        "environment": {"fp_mode": "ieee", "rounding": rounding},
        "generation": generation,
        "operands": {"source": {"buffer": "buf0", "offset": offset}},
    }


def _with_guards(lanes: tuple[int, int], offset: int, suffix: int = 3) -> bytes:
    prefix = bytes((0xA0 + index) & 0xFF for index in range(offset))
    payload = b"".join(lane.to_bytes(8, "little") for lane in lanes)
    return prefix + payload + bytes((0xD0 + index) & 0xFF for index in range(suffix))


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x3FF0000000000000, 0xC004000000000000), 0, "structured"),
        ((0x0123456789ABCDEF, 0xFEDCBA9876543210), 1, "boundary"),
        ((0x0000000000000000, 0x8000000000000000), 3, "boundary"),
        ((0x0000000000000001, 0x800FFFFFFFFFFFFF), 7, "boundary"),
        ((0x7FF0000000000000, 0xFFF0000000000000), 8, "boundary"),
        ((0x7FF8000000000042, 0xFFF0000000000001), 9, "boundary"),
        ((0xFFFFFFFFFFFFFFFF, 0x0000000000000000), 15, "boundary"),
        ((0x0011223344556677, 0x8899AABBCCDDEEFF), 5, "boundary"),
    )
    for index, (lanes, offset, generation_class) in enumerate(structured):
        yield _record(
            _with_guards(lanes, offset),
            offset,
            {"class": generation_class},
            modes[index % len(modes)],
        )
    while True:
        raw = b"".join(random.next().to_bytes(8, "little") for _ in range(6))
        offset = random.next() % 33
        yield _record(
            raw,
            offset,
            {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            modes[random.next() % len(modes)],
        )


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    buffers = record["buffers"]
    operands = record["operands"]
    assert isinstance(buffers, dict) and isinstance(operands, dict)
    pointer = operands["source"]
    assert isinstance(pointer, dict)
    buffer_id = str(pointer["buffer"])
    allocation = buffers[buffer_id]
    assert isinstance(allocation, dict)
    encoded = str(allocation["bytes"])
    raw = bytes.fromhex(encoded[2:])
    offset = int(pointer["offset"])
    loaded = raw[offset : offset + 16]
    lanes = [
        f"0x{int.from_bytes(loaded[start:start + 8], 'little'):016x}"
        for start in (0, 8)
    ]
    observed_buffers = {
        name: {"byte_offset": 0, "bytes": str(value["bytes"])}
        for name, value in buffers.items()
        if isinstance(value, dict)
    }
    return {
        "buffers": observed_buffers,
        "return": {"element": "f64", "lanes": lanes},
    }
