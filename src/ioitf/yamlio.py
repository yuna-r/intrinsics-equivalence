"""Strict YAML 1.2 JSON-schema input for human-authored case packs."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.tokens import AliasToken, AnchorToken, DirectiveToken, TagToken

from .canonical import JSONValue, validate_json_value
from .errors import ValidationError


class _JSONSchemaLoader(yaml.SafeLoader):
    """SafeLoader with YAML 1.2's deliberately small JSON scalar schema."""


# Copying the resolver table is important: changing it on this subclass must
# not silently alter PyYAML's process-global SafeLoader behavior.
_JSONSchemaLoader.yaml_implicit_resolvers = {}
_JSONSchemaLoader.add_implicit_resolver(
    "tag:yaml.org,2002:null", re.compile(r"^(?:null)$"), ["n"]
)
_JSONSchemaLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$"), ["t", "f"]
)
_JSONSchemaLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int",
    re.compile(r"^-?(?:0|[1-9][0-9]*)$"),
    list("-0123456789"),
)
_JSONSchemaLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(
        r"^-?(?:(?:0|[1-9][0-9]*)\.[0-9]+(?:[eE][+-]?[0-9]+)?|"
        r"(?:0|[1-9][0-9]*)[eE][+-]?[0-9]+)$"
    ),
    list("-0123456789"),
)


def _construct_unique_mapping(
    loader: _JSONSchemaLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "mapping keys must be scalar values",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate mapping key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_JSONSchemaLoader.add_constructor(
    "tag:yaml.org,2002:map", _construct_unique_mapping
)


def _reject_merge_keys(value: Any, *, location: str = "$") -> None:
    if isinstance(value, dict):
        if "<<" in value:
            raise ValidationError(f"{location}: YAML merge keys are not allowed")
        for key, item in value.items():
            _reject_merge_keys(item, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_merge_keys(item, location=f"{location}[{index}]")


def load_yaml_text(text: str, *, source: str) -> JSONValue:
    """Load one strict YAML document already embedded in another artifact."""
    try:
        for token in yaml.scan(text, Loader=_JSONSchemaLoader):
            if isinstance(token, (AliasToken, AnchorToken)):
                raise ValidationError(
                    f"{source}: YAML anchors and aliases are not allowed"
                )
            if isinstance(token, TagToken):
                raise ValidationError(f"{source}: explicit YAML tags are not allowed")
            if isinstance(token, DirectiveToken):
                raise ValidationError(f"{source}: YAML directives are not allowed")
        value = yaml.load(text, Loader=_JSONSchemaLoader)
        _reject_merge_keys(value)
        validate_json_value(value)
    except ValidationError:
        raise
    except yaml.YAMLError as exc:
        raise ValidationError(f"{source}: invalid YAML: {exc}") from exc
    return value


def load_yaml_file(path: str | Path) -> JSONValue:
    """Load one strict YAML document into the canonical JSON data model."""

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
    return load_yaml_text(text, source=str(file_path))
