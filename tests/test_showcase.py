from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.cases import CaseDefinition  # noqa: E402
from ioitf.showcase import render_showcase_html, write_showcase_report  # noqa: E402


class ShowcaseReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = CaseDefinition(
            "sse2.demo.f64x2.default",
            {
                "comparison": {"mode": "bit_exact"},
                "description": "<script>alert('signal')</script>",
                "intel": {"required_isa": ["sse2"], "symbol": "intel_demo"},
                "openpower": {
                    "required_isa": ["power8", "vsx"],
                    "symbol": "power_demo",
                },
                "signature": {
                    "arguments": [
                        {"element": "f64", "lanes": 2, "name": "a", "type": "vector"}
                    ],
                    "return": {"element": "f64", "lanes": 2, "type": "vector"},
                },
            },
        )
        self.summary = {
            "matched_inputs": 8,
            "mismatch_atoms": 0,
            "mismatched_inputs": 0,
            "not_comparable_inputs": 0,
            "outcome": "pass",
            "record_count": 8,
        }
        self.generated_at = datetime(2026, 9, 2, 12, 34, 56, tzinfo=timezone.utc)

    def _render(self) -> str:
        return render_showcase_html(
            cases=[self.case],
            summary=self.summary,
            profile="smoke",
            seed="0x6a09e667f3bcc909",
            vector_sha256="a" * 64,
            case_definitions_sha256="b" * 64,
            isa_contract_sha256="c" * 64,
            generated_at=self.generated_at,
            native_evidence=False,
        )

    def test_report_is_self_contained_responsive_and_escapes_case_text(self) -> None:
        html = self._render()
        parser = HTMLParser()
        parser.feed(html)
        parser.close()

        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn('name="viewport"', html)
        self.assertIn("@media (max-width: 580px)", html)
        self.assertIn("@media (prefers-reduced-motion: reduce)", html)
        self.assertIn("COHERENCE CONFIRMED", html)
        self.assertIn("DEVELOPMENT SIMULATION", html)
        self.assertIn("NON-NORMATIVE SHOWCASE VIEW", html)
        self.assertIn("&lt;script&gt;alert(&#x27;signal&#x27;)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    def test_writer_publishes_one_utf8_html_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "showcase.html"
            result = write_showcase_report(
                path,
                cases=[self.case],
                summary=self.summary,
                profile="smoke",
                seed="0x6a09e667f3bcc909",
                vector_sha256="a" * 64,
                case_definitions_sha256="b" * 64,
                isa_contract_sha256="c" * 64,
                generated_at=self.generated_at,
                native_evidence=False,
            )
            self.assertEqual(result, path)
            self.assertEqual(path.read_text(encoding="utf-8"), self._render())


if __name__ == "__main__":
    unittest.main()
