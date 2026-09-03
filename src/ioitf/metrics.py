"""Derived verification metrics shared by terminal and showcase reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .canonical import JSONValue
from .cases import ELEMENT_WIDTHS, CaseDefinition


@dataclass(frozen=True)
class VerificationMetrics:
    case_count: int
    trials: int
    implementation_path_evaluations: int
    lane_verdicts: int
    bit_positions: int
    matched_inputs: int
    mismatched_inputs: int
    not_comparable_inputs: int
    mismatch_atoms: int
    match_rate: float
    vectors_per_case: int


def collect_verification_metrics(
    cases: Iterable[CaseDefinition], summary: Mapping[str, JSONValue]
) -> VerificationMetrics:
    """Derive workload and outcome counts from canonical comparison results."""

    ordered_cases = tuple(cases)
    case_count = len(ordered_cases)
    trials = int(summary["record_count"])
    if trials < 0:
        raise ValueError("verification record_count must not be negative")
    if case_count == 0 and trials:
        raise ValueError("verification records require at least one case")
    if case_count and trials % case_count:
        raise ValueError("verification record_count must divide evenly across cases")

    matched = int(summary["matched_inputs"])
    mismatched = int(summary["mismatched_inputs"])
    not_comparable = int(summary["not_comparable_inputs"])
    mismatch_atoms = int(summary["mismatch_atoms"])
    vectors_per_case = trials // case_count if case_count else 0

    lanes_per_sweep = 0
    bits_per_sweep = 0
    for case in ordered_cases:
        return_shape = case.signature["return"]
        assert isinstance(return_shape, dict)
        if return_shape["type"] == "void":
            memory = case.data.get("memory_contract")
            if not isinstance(memory, dict):
                raise ValueError(
                    "void-return verification metrics require memory writes"
                )
            write_ranges = []
            for contract in memory.values():
                if isinstance(contract, dict):
                    ranges = contract.get("write_ranges", [])
                    if isinstance(ranges, list):
                        write_ranges.extend(ranges)
            if not write_ranges:
                raise ValueError(
                    "void-return verification metrics require memory writes"
                )
            lanes_per_sweep += len(write_ranges)
            bits_per_sweep += sum(
                int(item["byte_length"]) * 8
                for item in write_ranges
                if isinstance(item, dict)
            )
            continue
        lanes = int(return_shape.get("lanes", 1))
        if lanes < 1:
            raise ValueError("verification return-vector lanes must be positive")
        element = str(return_shape.get("element", ""))
        try:
            element_bits = ELEMENT_WIDTHS[element]
        except KeyError as error:
            raise ValueError(
                f"unsupported return element for verification metrics: {element!r}"
            ) from error
        lanes_per_sweep += lanes
        bits_per_sweep += lanes * element_bits

    match_rate = 100.0 if trials == 0 else matched * 100.0 / trials
    return VerificationMetrics(
        case_count=case_count,
        trials=trials,
        implementation_path_evaluations=trials * 2,
        lane_verdicts=lanes_per_sweep * vectors_per_case,
        bit_positions=bits_per_sweep * vectors_per_case,
        matched_inputs=matched,
        mismatched_inputs=mismatched,
        not_comparable_inputs=not_comparable,
        mismatch_atoms=mismatch_atoms,
        match_rate=match_rate,
        vectors_per_case=vectors_per_case,
    )
