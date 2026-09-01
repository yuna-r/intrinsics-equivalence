"""Development case-pack API shared by vector generation and fixtures.

Normative contracts stay in ``case.yaml``.  The neighboring
``development.py`` keeps the non-native input generator and executable model
for that one case together, so adding a case does not require editing central
dispatch tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from types import ModuleType
from typing import Callable, Iterator, Mapping

from .canonical import JSONValue, sha256_bytes
from .cases import CaseDefinition
from .errors import UnsupportedError, ValidationError


MASK64 = (1 << 64) - 1


class SplitMix64:
    def __init__(self, seed: int):
        self.state = seed & MASK64

    def next(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return (value ^ (value >> 31)) & MASK64


def vector(element: str, values: tuple[int, ...]) -> dict[str, JSONValue]:
    digits = {
        "f32": 8,
        "f64": 16,
        "i8": 2,
        "i16": 4,
        "i32": 8,
        "i64": 16,
        "u8": 2,
        "u16": 4,
        "u32": 8,
        "u64": 16,
    }[element]
    mask = (1 << (digits * 4)) - 1
    return {
        "element": element,
        "lanes": [f"0x{value & mask:0{digits}x}" for value in values],
    }


def scalar(element: str, value: int) -> dict[str, JSONValue]:
    digits = {"f64": 16}[element]
    return {"bits": f"0x{value:0{digits}x}", "element": element}


def rounding_modes(case: CaseDefinition) -> list[str]:
    modes = case.environment["fp_rounding_modes"]
    assert isinstance(modes, list)
    return [str(mode) for mode in modes]


def random_finite_f64_bits(generator: SplitMix64) -> int:
    value = generator.next()
    if ((value >> 52) & 0x7FF) == 0x7FF:
        value ^= 1 << 52
    return value


CandidateFactory = Callable[..., Iterator[dict[str, JSONValue]]]
Executor = Callable[[dict[str, JSONValue]], dict[str, JSONValue]]


@dataclass(frozen=True)
class DevelopmentCase:
    id: str
    candidates: CandidateFactory
    execute: Executor
    minimum_counts: Mapping[str, int]
    source_path: Path


_CACHE: dict[Path, DevelopmentCase] = {}
_LOADED_BY_ID: dict[str, DevelopmentCase] = {}


def _module_from_path(path: Path) -> ModuleType:
    module_name = f"_ioitf_casepack_{sha256_bytes(str(path).encode('utf-8'))}"
    module = ModuleType(module_name)
    module.__file__ = str(path)
    sys.modules[module_name] = module
    try:
        source = path.read_bytes()
        exec(compile(source, str(path), "exec"), module.__dict__)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise ValidationError(f"cannot load development case pack {path}: {exc}") from exc
    return module


def load_development_case(case: CaseDefinition) -> DevelopmentCase:
    """Load the development behavior next to a case's normative contract."""

    if case.source_path is None:
        loaded = _LOADED_BY_ID.get(case.id)
        if loaded is not None:
            return loaded
        raise UnsupportedError(f"case {case.id!r} has no development case pack")
    path = case.source_path.parent / "development.py"
    if not path.is_file():
        loaded = _LOADED_BY_ID.get(case.id)
        if loaded is not None:
            return loaded
        raise UnsupportedError(
            f"case {case.id!r} has no neighboring development.py"
        )
    resolved = path.resolve()
    cached = _CACHE.get(resolved)
    if cached is not None:
        if cached.id != case.id:
            raise ValidationError(
                f"development case pack {path} declares {cached.id!r}, expected {case.id!r}"
            )
        _LOADED_BY_ID[case.id] = cached
        return cached

    module = _module_from_path(resolved)
    case_id = getattr(module, "CASE_ID", None)
    candidates = getattr(module, "candidates", None)
    execute = getattr(module, "execute", None)
    minimum_counts = getattr(module, "MINIMUM_COUNTS", {})
    if (
        not isinstance(case_id, str)
        or not callable(candidates)
        or not callable(execute)
    ):
        raise ValidationError(
            f"{path}: expected CASE_ID plus callable candidates and execute exports"
        )
    if not isinstance(minimum_counts, dict) or any(
        not isinstance(profile, str)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 1
        for profile, count in minimum_counts.items()
    ):
        raise ValidationError(
            f"{path}: MINIMUM_COUNTS must map profiles to positive integers"
        )
    pack = DevelopmentCase(case_id, candidates, execute, minimum_counts, resolved)
    if pack.id != case.id:
        raise ValidationError(
            f"development case pack {path} declares {pack.id!r}, expected {case.id!r}"
        )
    _CACHE[resolved] = pack
    _LOADED_BY_ID[case.id] = pack
    return pack
