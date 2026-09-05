"""Capture fixed SSE2 oracles without importing or executing the case models.

Build native/probe_sse2_nan.c with strict FP, then pass --probe and an explicit
--execution-context. Use --verify to compare a fresh capture with saved rows.
"""

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess


MODES = ("nearest_even", "toward_negative", "toward_positive", "toward_zero")
ROOT = Path(__file__).resolve().parents[1]


def vector(element, values):
    mask = (1 << int(element[1:])) - 1
    return {"element": element, "lanes": [f"0x{v & mask:0{int(element[1:]) // 4}x}" for v in values]}


def scalar(element, value):
    return {"element": element, "bits": vector(element, [value])["lanes"][0]}


def capture(probe):
    @lru_cache(None)
    def expected(element, op, a, b, mode):
        output = subprocess.check_output(
            [str(probe), element, op, hex(a), hex(b), mode], text=True
        )
        return int(output.strip(), 16)

    rows = []

    def add(case_id, mode, operands, result, family, label):
        rows.append(dict(case_id=case_id, rounding=mode, operands=operands,
                         expected={"return": result}, family=family, label=label))

    for element, one, quarter, three_quarters, half, three in (
        ("f32", 0x3F800000, 0x33000000, 0x33C00000, 0x3F000000, 0x40400000),
        ("f64", 0x3FF0000000000000, 0x3C90000000000000, 0x3CA8000000000000,
         0x3FE0000000000000, 0x4008000000000000),
    ):
        width = int(element[1:])
        sign, lanes = 1 << (width - 1), 128 // width
        poison = ((0x7F800001, 0x80000000, 0x7FC00042) if width == 32
                  else (0x7FF0000000000001,))
        examples = {
            "add": [(one, quarter), (one, three_quarters), (one | sign, quarter | sign)],
            "sub": [(one, quarter), (one | sign, quarter)],
            "mul": [(one + 1, one + 1), (1, half), (sign | 1, half)],
            "div": [(one, three), (one | sign, three), (1, one + (1 << (23 if width == 32 else 52)))],
            "sqrt": [(one + (1 << (23 if width == 32 else 52)), 0), (1, 0)],
        }
        for op, pairs in examples.items():
            for a, b in pairs:
                for mode in MODES:
                    answer = expected(element, op, a, b, mode)
                    for variant in ("default", "scalar"):
                        operands = {"a": vector(element, (a,) + poison if variant == "scalar" else (a,) * lanes)}
                        if op != "sqrt":
                            operands["b"] = vector(element, (b,) * lanes)
                        result = vector(element, (answer,) + poison if variant == "scalar" else (answer,) * lanes)
                        add(f"sse2.{op}.{element}x{lanes}.{variant}", mode, operands,
                            result, "rounding_sqrt" if op == "sqrt" else "rounding_arithmetic", f"{a:x}/{b:x}")

        # Rounding vs truncation, positive/negative ties and integer boundaries.
        points = ([0x3FC00000, 0xBFC00000, 0x40200000, 0x4EFFFFFF, 0x4F000000]
                  if width == 32 else [0x3FF8000000000000, 0xBFF8000000000000,
                                      0x4004000000000000, 0x41DFFFFFFFE00000, 0x41DFFFFFFFE00001])
        for a in points:
            for op in ("cvt", "cvtt"):
                for mode in MODES:
                    operands = {"a": vector(element, (a,) * lanes)}
                    answer = expected(element, op + "_i32", a, 0, mode)
                    add(f"sse2.{op}.{element}x{lanes}.i32.scalar", mode, operands,
                        scalar("i32", answer), "rounding_float_to_integer", f"{a:x}")
                    add(f"sse2.{op}.{element}x{lanes}.i32x4", mode, operands,
                        vector("i32", (answer,) * lanes + (0,) * (4 - lanes)),
                        "rounding_float_to_integer", f"{a:x}")
                    if width == 64:
                        answer64 = expected(element, op + "_i64", a, 0, mode)
                        add(f"sse2.{op}.f64x2.i64.scalar", mode, operands,
                            scalar("i64", answer64), "rounding_float_to_integer", f"{a:x}")

    for a in (0x3FF0000010000000, 0xBFF0000010000000, 0x3690000000000000,
              0xB690000000000000, 0x47EFFFFFF0000000, 0xC7EFFFFFF0000000):
        for mode in MODES:
            answer = expected("f64", "narrow", a, 0, mode)
            add("sse2.cvt.f64x2.f32x4", mode, {"a": vector("f64", (a, a))},
                vector("f32", (answer, answer, 0, 0)), "rounding_narrowing", f"{a:x}")
            add("sse2.cvt.f64x2.f32x4.scalar", mode,
                {"a": vector("f32", (0, 0x7F800001, 0x80000000, 0x7FC00042)),
                 "b": vector("f64", (a, 0))},
                vector("f32", (answer, 0x7F800001, 0x80000000, 0x7FC00042)),
                "rounding_narrowing", f"{a:x}")

    for a in (0x01000001, 0xFEFFFFFF, 0x7FFFFFFF, 0x80000001):
        for mode in MODES:
            answer = expected("f32", "from_i32", a, 0, mode)
            add("sse2.cvt.i32x4.f32x4", mode, {"a": vector("i32", (a,) * 4)},
                vector("f32", (answer,) * 4), "rounding_integer_to_float", f"{a:x}")
            add("sse2.cvt.i32.f32x4.scalar", mode,
                {"a": vector("f32", (0, 0x7F800001, 0x80000000, 0x7FC00042)), "value": scalar("i32", a)},
                vector("f32", (answer, 0x7F800001, 0x80000000, 0x7FC00042)),
                "rounding_integer_to_float", f"{a:x}")
    for a in (0x0020000000000001, 0xFFDFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF, 0x8000000000000001):
        for mode in MODES:
            answer = expected("f64", "from_i64", a, 0, mode)
            add("sse2.cvt.i64.f64x2.scalar", mode,
                {"a": vector("f64", (0, 0x7FF0000000000001)), "value": scalar("i64", a)},
                vector("f64", (answer, 0x7FF0000000000001)), "rounding_integer_to_float", f"{a:x}")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--execution-context", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "tests/data/rounding-oracles.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    rows = capture(args.probe.resolve())
    if args.verify:
        assert json.loads(args.output.read_text())["rows"] == rows, "oracle capture changed"
    else:
        sources = [ROOT / "tests/native/probe_sse2_nan.c", Path(__file__)]
        artifact = {
            "schema_version": 1, "oracle": "SSE2 intrinsics with MXCSR rounding; exceptions masked; FTZ/DAZ off",
            "execution_context": args.execution_context,
            "native_cross_host_evidence": False,
            "probe_sha256": hashlib.sha256(args.probe.read_bytes()).hexdigest(),
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            "rows": rows,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(f"{'Verified' if args.verify else 'Captured'} {len(rows)} independent SSE2 rows.")
