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

    def _render(self, *, quality=None) -> str:
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
            quality=quality,
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

    def test_oracle_findings_override_pass_headline_and_preserve_comparison_counts(self):
        quality = {
            "status": "fail",
            "gates": {"python_coverage": {
                "status": "fail", "model_oracle_tests_run": 1,
                "failure_classification": {
                    "portable_model_output_mismatches": 1,
                    "other_assertion_failures": 0, "test_execution_errors": 0,
                },
                "model_output_mismatches": [{
                    "input": {"case_id": "<script>bad</script>", "input_id": "a" * 64,
                              "operands": {"a": "0x7ff0000000000000"}},
                    "expected": {"bits": "0xfff8000000000000"},
                    "actual": {"bits": "0x7ff8000000000000"},
                    "test_id": "test_nan",
                }],
            }},
        }
        html = self._render(quality=quality)
        self.assertIn("QUALITY CHECK FAILED // QUALITY_FAILED", html)
        self.assertNotIn("COHERENCE CONFIRMED", html)
        self.assertIn("Matched inputs</span><b>0008", html)
        self.assertIn("Comparison outcome</span><b>PASS", html)
        self.assertIn("比較・集計処理の誤判定として検出されたものではありません", html)
        self.assertIn("0xfff8000000000000", html)
        self.assertIn("0x7ff8000000000000", html)
        self.assertIn("&lt;script&gt;bad&lt;/script&gt;", html)
        self.assertNotIn("<script>bad", html)

    def test_missing_quality_is_not_presented_as_an_oracle_pass(self):
        self.assertIn("独立したモデル検証：未実施", self._render())
        html = self._render(quality={"status": "fail", "gates": {}})
        self.assertIn("QUALITY CHECK FAILED", html)
        self.assertIn("未集計", html)
        self.assertNotIn("今回の不一致の対象は", html)

    def test_load_spectrum_shows_derived_workload(self) -> None:
        html = self._render()

        self.assertIn('<section class="load-spectrum-section"', html)
        self.assertIn("Test load spectrum", html)
        self.assertIn("Verification density", html)
        self.assertIn("DETERMINISTIC PAIRED-FIXTURE TRIALS", html)
        self.assertIn("<strong>8</strong>", html)
        self.assertIn("FIXTURE PATH EVALUATIONS", html)
        self.assertIn("<strong>16</strong>", html)
        self.assertIn("LANE VERDICTS", html)
        self.assertIn("BIT-EXACT POSITIONS", html)
        self.assertIn("<strong>1,024</strong>", html)
        self.assertIn("Bit-exact contracts", html)
        self.assertIn("Divergence atoms", html)
        self.assertIn("0 non-comparable inputs", html)
        self.assertIn("DEVELOPMENT SIMULATION", html)
        self.assertIn("SSE2 SEMANTICS // DEV FIXTURE", html)
        self.assertIn("VSX SEMANTICS // DEV FIXTURE", html)

        metrics_end = html.index(
            '</div>\n\n    <section class="load-spectrum-section"'
        )
        topology = html.index("Transmission topology")
        self.assertLess(metrics_end, topology)

    def test_rectangular_graph_uses_standard_load_as_the_fixed_scale(self) -> None:
        html = self._render()

        self.assertIn('role="meter"', html)
        self.assertIn('aria-valuemax="1000"', html)
        self.assertIn('aria-valuenow="8"', html)
        self.assertIn(
            'aria-valuetext="8 vectors per case; standard load scale 0.8 percent"',
            html,
        )
        self.assertIn('style="--load-level:0.8%"', html)
        self.assertIn("1,000 vectors per case = standard", html)
        self.assertIn("Profile // SMOKE", html)
        self.assertIn("VECTORS / CASE", html)
        self.assertIn('class="load-axis-label" style="--level:100%">1000', html)
        self.assertIn('class="load-axis-label" style="--level:75%">750', html)
        self.assertIn('class="load-axis-label" style="--level:50%">500', html)
        self.assertIn('class="load-axis-label" style="--level:25%">250', html)
        self.assertIn('class="load-axis-label" style="--level:0%">0', html)
        self.assertEqual(html.count('class="load-gridline"'), 5)
        self.assertIn('class="load-bar"', html)
        self.assertIn('class="load-marker"', html)
        self.assertIn("#58e9ff", html)
        self.assertIn("#70ffd1", html)
        self.assertIn("#e7f66b", html)
        self.assertIn("#ff9d42", html)
        self.assertIn("Failure indication remains red", html)

        lowered = html.lower()
        self.assertNotIn("thermostat", lowered)
        self.assertNotIn("thermo-", lowered)
        self.assertNotIn("chamber", lowered)
        self.assertNotIn("qualification", lowered)
        self.assertNotIn("heat", lowered)
        self.assertNotIn("gate", lowered)

    def test_stress_load_saturates_meter_but_keeps_actual_readout(self) -> None:
        html = render_showcase_html(
            cases=[self.case],
            summary={**self.summary, "matched_inputs": 1500, "record_count": 1500},
            profile="stress",
            seed="safe",
            vector_sha256="a" * 64,
            case_definitions_sha256="b" * 64,
            isa_contract_sha256="c" * 64,
            generated_at=self.generated_at,
            native_evidence=False,
        )

        self.assertIn('aria-valuemax="1000" aria-valuenow="1000"', html)
        self.assertIn(
            'aria-valuetext="1,500 vectors per case; standard load scale 100 percent"',
            html,
        )
        self.assertIn('style="--load-level:100%"', html)
        self.assertIn(
            "<strong>1,500</strong><span>ACTUAL VECTORS / CASE</span>", html
        )
        self.assertIn("Profile // STRESS", html)

    def test_all_supported_element_widths_feed_the_workload_totals(self) -> None:
        shapes = (
            ("f32", 4),
            ("f64", 2),
            ("i8", 16),
            ("u8", 16),
            ("i16", 8),
            ("u16", 8),
            ("i32", 4),
            ("u32", 4),
            ("i64", 2),
            ("u64", 2),
        )
        cases = []
        for index, (element, lanes) in enumerate(shapes):
            cases.append(
                CaseDefinition(
                    f"demo.width.{index}",
                    {
                        "comparison": {"mode": "bit_exact"},
                        "description": f"{element} measurement",
                        "intel": {"required_isa": ["sse2"], "symbol": "intel_demo"},
                        "openpower": {
                            "required_isa": ["power8", "vsx"],
                            "symbol": "power_demo",
                        },
                        "signature": {
                            "arguments": [
                                {
                                    "element": element,
                                    "lanes": lanes,
                                    "name": "a",
                                    "type": "vector",
                                }
                            ],
                            "return": {
                                "element": element,
                                "lanes": lanes,
                                "type": "vector",
                            },
                        },
                    },
                )
            )

        html = render_showcase_html(
            cases=cases,
            summary={**self.summary, "matched_inputs": 20, "record_count": 20},
            profile="widths",
            seed="safe",
            vector_sha256="a" * 64,
            case_definitions_sha256="b" * 64,
            isa_contract_sha256="c" * 64,
            generated_at=self.generated_at,
            native_evidence=False,
        )

        self.assertIn("<strong>40</strong>", html)
        self.assertIn("<strong>132</strong>", html)
        self.assertIn("<strong>2,560</strong>", html)
        self.assertIn('style="--load-level:0.2%"', html)

    def test_non_pass_capture_does_not_claim_every_lane_was_a_verdict(self) -> None:
        summaries = (
            {
                **self.summary,
                "matched_inputs": 7,
                "not_comparable_inputs": 1,
                "outcome": "not_comparable",
            },
            {
                **self.summary,
                "matched_inputs": 7,
                "mismatched_inputs": 1,
                "mismatch_atoms": 1,
                "outcome": "mismatch",
            },
        )
        for summary in summaries:
            with self.subTest(outcome=summary["outcome"]):
                html = render_showcase_html(
                    cases=[self.case],
                    summary=summary,
                    profile="smoke",
                    seed="safe",
                    vector_sha256="a" * 64,
                    case_definitions_sha256="b" * 64,
                    isa_contract_sha256="c" * 64,
                    generated_at=self.generated_at,
                    native_evidence=False,
                )

                self.assertIn("MATRIX LANE POSITIONS", html)
                self.assertIn("PAIRED OUTPUT-BIT POSITIONS", html)
                self.assertNotIn("<span>LANE VERDICTS</span>", html)

    def test_native_capture_uses_architecture_specific_labels(self) -> None:
        html = render_showcase_html(
            cases=[self.case],
            summary=self.summary,
            profile="standard",
            seed="safe",
            vector_sha256="a" * 64,
            case_definitions_sha256="b" * 64,
            isa_contract_sha256="c" * 64,
            generated_at=self.generated_at,
            native_evidence=True,
        )

        self.assertIn("NATIVE EVIDENCE", html)
        self.assertIn("DETERMINISTIC CROSS-ARCH TRIALS", html)
        self.assertIn("PATH EXECUTIONS", html)
        self.assertIn("x86_64 // NATIVE RUNNER", html)
        self.assertIn("ppc64le // NATIVE RUNNER", html)
        self.assertIn("crossed two native architectures", html)

    def test_uneven_record_distribution_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "divide evenly"):
            render_showcase_html(
                cases=[self.case, self.case],
                summary={**self.summary, "record_count": 9},
                profile="smoke",
                seed="safe",
                vector_sha256="a" * 64,
                case_definitions_sha256="b" * 64,
                isa_contract_sha256="c" * 64,
                generated_at=self.generated_at,
                native_evidence=False,
            )

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
