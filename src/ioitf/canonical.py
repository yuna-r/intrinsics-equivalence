"""Strict RFC 8785-oriented JSON, JSONL, hashing, and atomic publication.

IOITF schema version 1 intentionally excludes JSON floating-point numbers.
That removes ECMAScript number-formatting from the data path; floating-point
values and tolerances use strings.  Object keys are ordered as UTF-16 code
units, which is the important difference from Python's normal ``sort_keys``.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterable, Iterator, Mapping
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, BinaryIO, TypeAlias

from .errors import RunnerError, ValidationError


JSONValue: TypeAlias = None | bool | int | str | list["JSONValue"] | dict[str, "JSONValue"]
MAX_SAFE_INTEGER = (1 << 53) - 1


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def utf16_sort_key(value: str) -> bytes:
    """Return the RFC 8785 §3.2.3 ordering key for a Unicode string."""

    _validate_string(value, "JSON object key")
    return value.encode("utf-16-be")


def _validate_string(value: str, location: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValidationError(f"{location}: Unicode surrogate code points are not allowed")


def validate_json_value(value: Any, *, location: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        _validate_string(value, location)
        return
    if isinstance(value, int):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise ValidationError(
                f"{location}: integer is outside -(2^53-1)..2^53-1"
            )
        return
    if isinstance(value, float):
        raise ValidationError(f"{location}: JSON floating-point numbers are not allowed")
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_json_value(item, location=f"{location}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"{location}: JSON object keys must be strings")
            _validate_string(key, f"{location} key")
            validate_json_value(item, location=f"{location}.{key}")
        return
    raise ValidationError(f"{location}: unsupported JSON value {type(value).__name__}")


def loads(text: str, *, source: str = "JSON") -> JSONValue:
    def reject_float(token: str) -> Any:
        raise ValidationError(f"{source}: JSON floating-point number is not allowed: {token}")

    def reject_constant(token: str) -> Any:
        raise ValidationError(f"{source}: non-finite JSON constant is not allowed: {token}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
        validate_json_value(value)
    except ValidationError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValidationError(f"{source}: invalid JSON: {exc}") from exc
    return value


def load_file(path: str | Path) -> JSONValue:
    file_path = Path(path)
    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {file_path}: {exc}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValidationError(f"{file_path}: UTF-8 BOM is not allowed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{file_path}: file is not valid UTF-8") from exc
    return loads(text, source=str(file_path))


def _ordered(value: JSONValue) -> JSONValue:
    if isinstance(value, dict):
        return OrderedDict(
            (key, _ordered(value[key]))
            for key in sorted(value, key=utf16_sort_key)
        )  # type: ignore[return-value]
    if isinstance(value, list):
        return [_ordered(item) for item in value]
    return value


def dumps(value: JSONValue) -> str:
    """Serialize the IOITF integer-only data model as RFC 8785 JSON."""

    try:
        validate_json_value(value)
        return json.dumps(
            _ordered(value),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except ValidationError:
        raise
    except (ValueError, RecursionError) as exc:
        raise ValidationError(f"cannot canonicalize JSON value: {exc}") from exc


def dump_bytes(value: JSONValue, *, newline: bool = False) -> bytes:
    encoded = dumps(value).encode("utf-8")
    return encoded + (b"\n" if newline else b"")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    file_path = Path(path)
    try:
        with file_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValidationError(f"cannot hash {file_path}: {exc}") from exc
    return digest.hexdigest()


def require_object(value: Any, location: str) -> dict[str, JSONValue]:
    if not isinstance(value, dict):
        raise ValidationError(f"{location}: expected an object")
    return value


def require_exact_keys(
    value: Mapping[str, Any],
    required: set[str],
    *,
    optional: set[str] | None = None,
    location: str,
) -> None:
    optional = optional or set()
    keys = set(value)
    missing = required - keys
    extra = keys - required - optional
    if missing:
        raise ValidationError(f"{location}: missing keys: {', '.join(sorted(missing))}")
    if extra:
        raise ValidationError(f"{location}: unknown keys: {', '.join(sorted(extra))}")


def require_string(value: Any, location: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise ValidationError(f"{location}: expected a {qualifier}string")
    _validate_string(value, location)
    return value


def require_int(
    value: Any,
    location: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{location}: expected an integer")
    if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
        raise ValidationError(f"{location}: integer is outside the JSON safe range")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{location}: expected an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValidationError(f"{location}: expected an integer <= {maximum}")
    return value


def require_bool(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{location}: expected a boolean")
    return value


def require_sorted_unique_strings(
    value: Any,
    location: str,
    *,
    nonempty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise ValidationError(f"{location}: expected a {qualifier}string array")
    strings = [require_string(item, f"{location}[{index}]") for index, item in enumerate(value)]
    expected = sorted(set(strings), key=utf16_sort_key)
    if strings != expected:
        raise ValidationError(f"{location}: expected UTF-16-sorted unique strings")
    return strings


class AtomicFile:
    """Same-directory temporary output published with atomic ``os.replace``."""

    def __init__(self, final_path: str | Path):
        self.final_path = Path(final_path)
        self.temp_path: Path | None = None
        self.stream: BinaryIO | None = None

    def __enter__(self) -> BinaryIO:
        descriptor: int | None = None
        try:
            self.final_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(
                prefix=f".{self.final_path.name}.",
                suffix=".tmp",
                dir=self.final_path.parent,
            )
            self.temp_path = Path(name)
            self.stream = os.fdopen(descriptor, "wb")
            descriptor = None
            return self.stream
        except OSError as exc:
            if descriptor is not None:
                os.close(descriptor)
            if self.temp_path is not None:
                self.temp_path.unlink(missing_ok=True)
            raise RunnerError(
                f"cannot create temporary output for {self.final_path}: {exc}"
            ) from exc

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        assert self.stream is not None and self.temp_path is not None
        try:
            if exc_type is None:
                self.stream.flush()
                os.fsync(self.stream.fileno())
            self.stream.close()
            if exc_type is None:
                os.replace(self.temp_path, self.final_path)
                _fsync_directory(self.final_path.parent)
            else:
                self.temp_path.unlink(missing_ok=True)
        except OSError as io_error:
            self.temp_path.unlink(missing_ok=True)
            if exc_type is None:
                raise RunnerError(
                    f"cannot publish {self.final_path}: {io_error}"
                ) from io_error
        return False


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def atomic_write(path: str | Path, data: bytes) -> None:
    with AtomicFile(path) as stream:
        stream.write(data)


def remove_completion_marker(path: str | Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as exc:
        raise RunnerError(
            f"cannot remove stale completion marker {path}: {exc}"
        ) from exc


def read_canonical_json(path: str | Path) -> dict[str, JSONValue]:
    file_path = Path(path)
    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {file_path}: {exc}") from exc
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n") or b"\r" in raw:
        raise ValidationError(f"{file_path}: canonical JSON must have exactly one final LF")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValidationError(f"{file_path}: UTF-8 BOM is not allowed")
    try:
        value = loads(raw[:-1].decode("utf-8"), source=str(file_path))
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{file_path}: file is not valid UTF-8") from exc
    obj = require_object(value, str(file_path))
    if dump_bytes(obj, newline=True) != raw:
        raise ValidationError(f"{file_path}: JSON is not in canonical form")
    return obj


def iter_canonical_jsonl_bytes(
    data: bytes, *, source: str = "JSONL snapshot"
) -> Iterator[dict[str, JSONValue]]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValidationError(f"{source}: UTF-8 BOM is not allowed")
    if not data:
        return
    if not data.endswith(b"\n"):
        raise ValidationError(f"{source}: missing final LF")
    for line_number, payload in enumerate(data.split(b"\n")[:-1], 1):
        if not payload:
            raise ValidationError(f"{source}:{line_number}: empty lines are not allowed")
        if b"\r" in payload:
            raise ValidationError(f"{source}:{line_number}: CR is not allowed")
        try:
            value = loads(payload.decode("utf-8"), source=f"{source}:{line_number}")
        except UnicodeDecodeError as exc:
            raise ValidationError(f"{source}:{line_number}: invalid UTF-8") from exc
        obj = require_object(value, f"{source}:{line_number}")
        if dump_bytes(obj) != payload:
            raise ValidationError(f"{source}:{line_number}: JSON is not canonical")
        yield obj


def iter_canonical_jsonl(path: str | Path) -> Iterator[dict[str, JSONValue]]:
    file_path = Path(path)
    try:
        data = file_path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {file_path}: {exc}") from exc
    yield from iter_canonical_jsonl_bytes(data, source=str(file_path))


def write_jsonl(
    path: str | Path,
    records: Iterable[dict[str, JSONValue]],
    *,
    validator: Callable[[dict[str, JSONValue], int], None] | None = None,
) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    count = 0
    byte_length = 0
    with AtomicFile(path) as stream:
        for count, record in enumerate(records, 1):
            if validator is not None:
                validator(record, count)
            encoded = dump_bytes(record, newline=True)
            stream.write(encoded)
            digest.update(encoded)
            byte_length += len(encoded)
    return count, byte_length, digest.hexdigest()
