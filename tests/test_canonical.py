from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ioitf.canonical import (  # noqa: E402
    MAX_SAFE_INTEGER,
    dump_bytes,
    dumps,
    iter_canonical_jsonl,
    loads,
    read_canonical_json,
)
from ioitf.errors import ValidationError  # noqa: E402


class CanonicalJSONTests(unittest.TestCase):
    def test_utf16_code_unit_order_differs_from_code_point_order(self) -> None:
        # U+10000 begins with UTF-16 high surrogate D800, before BMP U+E000.
        self.assertEqual(dumps({"\ue000": 1, "\U00010000": 2}), '{"𐀀":2,"":1}')

    def test_rejects_duplicate_float_unsafe_integer_and_surrogate(self) -> None:
        invalid = (
            '{"a":1,"a":2}',
            '{"value":1.5}',
            f'{{"value":{MAX_SAFE_INTEGER + 1}}}',
            '"\\ud800"',
        )
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValidationError):
                loads(text)

    def test_parser_limits_are_reported_as_validation_errors(self) -> None:
        with self.assertRaises(ValidationError):
            loads("1" * 5000)
        with self.assertRaises(ValidationError):
            loads("[" * 1100 + "0" + "]" * 1100)

    def test_canonical_file_requires_exactly_one_lf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "value.json"
            for raw in (b'{"a":1}', b'{"a":1}\r\n', b'{"a":1}\n\n', b'{ "a": 1 }\n'):
                with self.subTest(raw=raw):
                    path.write_bytes(raw)
                    with self.assertRaises(ValidationError):
                        read_canonical_json(path)
            path.write_bytes(dump_bytes({"a": 1}, newline=True))
            self.assertEqual(read_canonical_json(path), {"a": 1})

    def test_jsonl_rejects_empty_line_and_noncanonical_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "records.jsonl"
            for raw in (b'{"a":1}\n\n', b'{ "a":1}\n', b'{"a":1}\r\n'):
                with self.subTest(raw=raw):
                    path.write_bytes(raw)
                    with self.assertRaises(ValidationError):
                        list(iter_canonical_jsonl(path))


if __name__ == "__main__":
    unittest.main()
