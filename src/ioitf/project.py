"""Small project-file layer that keeps suites outside the framework tree."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .errors import ValidationError


@dataclass(frozen=True)
class ProjectConfig:
    path: Path
    suite: Path
    isa_registry: Path


def _project_path(project: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{project}: ioitf.{field} must be a non-empty string")
    configured = Path(value)
    return configured if configured.is_absolute() else project.parent / configured


def load_project(path: str | Path) -> ProjectConfig:
    """Load the closed ``ioitf.toml`` schema and resolve its relative paths."""

    project = Path(path)
    try:
        raw = project.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read project file {project}: {exc}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValidationError(f"{project}: UTF-8 BOM is not allowed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{project}: file is not valid UTF-8") from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ValidationError(f"{project}: invalid TOML: {exc}") from exc

    if set(data) != {"ioitf"} or not isinstance(data["ioitf"], dict):
        raise ValidationError(f"{project}: expected only an [ioitf] table")
    settings = data["ioitf"]
    expected = {"isa_registry", "schema_version", "suite"}
    if set(settings) != expected:
        missing = expected - set(settings)
        extra = set(settings) - expected
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if extra:
            details.append("unknown " + ", ".join(sorted(extra)))
        raise ValidationError(f"{project}: invalid [ioitf] keys ({'; '.join(details)})")
    version = settings["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ValidationError(f"{project}: ioitf.schema_version must be integer 1")
    return ProjectConfig(
        project,
        _project_path(project, settings["suite"], "suite"),
        _project_path(project, settings["isa_registry"], "isa_registry"),
    )
