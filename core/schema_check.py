"""
core.schema_check
===================

A small JSON Schema checker (2026-10-05, Engine Phase 1), standard
library only, for the parts of draft 2020-12 MIA's published schemas use
(docs/schema/): type, enum, required, properties, additionalProperties,
items, pattern and local $ref. Other surfaces can validate the same
schema with any full JSON Schema library; MIA uses this so the device
needs nothing extra. Pure logic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "docs" / "schema"

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def errors(value, schema: dict, root: dict = None, path: str = "$") -> list[str]:
    """Every way `value` doesn't fit `schema`, as "path: problem" lines."""
    root = root if root is not None else schema
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            target = target[part]
        return errors(value, target, root, path)
    found: list[str] = []
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](value) for t in types):
            return [f"{path}: expected {' or '.join(types)}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        found.append(f"{path}: {value!r} doesn't match {schema['pattern']}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                found.append(f"{path}: missing '{key}'")
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                found += errors(item, properties[key], root, f"{path}.{key}")
            elif extra is False:
                found.append(f"{path}: unexpected '{key}'")
            elif isinstance(extra, dict):
                found += errors(item, extra, root, f"{path}.{key}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            found += errors(item, schema["items"], root, f"{path}[{index}]")
    return found
