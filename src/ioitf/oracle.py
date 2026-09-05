"""Typed evidence from independent portable-model oracle assertions."""

from __future__ import annotations

from .canonical import JSONValue, dumps


class ModelOutputMismatch(AssertionError):
    """A model returned a value different from a literal external oracle.

    This category applies only after contract validation and model execution
    succeeded. Validation errors, runner errors and generic test assertions
    must retain their own failure categories.
    """

    def __init__(
        self,
        *,
        input_record: dict[str, JSONValue],
        expected: dict[str, JSONValue],
        actual: dict[str, JSONValue],
        finding_family: str = "output_mismatch",
        contract_scope: str = "official_nearest_even",
        case_contract: dict[str, JSONValue] | None = None,
        oracle_reference: str = "tests/BUG_HUNT.md",
    ) -> None:
        self.evidence: dict[str, JSONValue] = {
            "category": "portable_model_output_mismatch",
            "subject": "Python portable case model",
            "comparison_path": "direct_python_equality_without_ioitf_compare",
            "oracle": "literal_sse2_expected_bits",
            "oracle_reference": oracle_reference,
            "finding_family": finding_family,
            "contract_scope": contract_scope,
            "input": input_record,
            "expected": expected,
            "actual": actual,
        }
        if case_contract is not None:
            self.evidence["case_contract"] = case_contract
        super().__init__(dumps(self.evidence))
