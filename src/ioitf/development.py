"""Portable case-model API shared by vector generation and fixtures.

New case packs keep their normative ``CASE_YAML`` and executable model in one
Python file.  Neighboring ``model.py`` and legacy ``development.py`` packs
remain readable.
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
    return {"bits": f"0x{value & mask:0{digits}x}", "element": element}


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
        raise ValidationError(f"cannot load portable case model {path}: {exc}") from exc
    return module


def load_development_case(case: CaseDefinition) -> DevelopmentCase:
    """Load a combined case pack or a model next to its contract."""

    if case.source_path is None:
        loaded = _LOADED_BY_ID.get(case.id)
        if loaded is not None:
            return loaded
        raise UnsupportedError(f"case {case.id!r} has no portable model")
    if case.source_path.suffix.lower() == ".py":
        path = case.source_path
    else:
        model_path = case.source_path.parent / "model.py"
        legacy_path = case.source_path.parent / "development.py"
        if model_path.is_file() and legacy_path.is_file():
            raise ValidationError(
                f"case {case.id!r} has both model.py and legacy development.py"
            )
        path = model_path if model_path.is_file() else legacy_path
    if not path.is_file():
        loaded = _LOADED_BY_ID.get(case.id)
        if loaded is not None:
            return loaded
        raise UnsupportedError(f"case {case.id!r} has no portable model")
    resolved = path.resolve()
    cached = _CACHE.get(resolved)
    if cached is not None:
        if cached.id != case.id:
            raise ValidationError(
                f"portable case model {path} declares {cached.id!r}, expected {case.id!r}"
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
            f"portable case model {path} declares {pack.id!r}, expected {case.id!r}"
        )
    _CACHE[resolved] = pack
    _LOADED_BY_ID[case.id] = pack
    return pack
