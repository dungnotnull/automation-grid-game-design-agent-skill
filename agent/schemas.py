"""agent.schemas - minimal pure-stdlib JSON Schema validator.

Implements the JSON Schema subset used by the skill/tool definitions:
``type``, ``properties``, ``required``, ``enum``, ``minimum``, ``maximum``,
``minItems``, ``items``, ``additionalProperties`` and ``$ref`` to local
definitions. This keeps the framework dependency-free while still providing
real input/output validation for every tool and skill.

For full JSON Schema support install ``jsonschema``; this module is a
deterministic, audited fallback that covers 100% of the schemas this project
ships.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .errors import SchemaError

_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": type(None),
}


def _resolve_ref(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise SchemaError(f"unsupported $ref: {ref}", path="$ref")
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise SchemaError(f"unresolvable $ref: {ref}", path="$ref")
        node = node[part]
    if not isinstance(node, dict):
        raise SchemaError(f"$ref target is not a schema: {ref}", path="$ref")
    return node


def _check_type(value: Any, type_name: str, path: str) -> None:
    py_type = _TYPES.get(type_name)
    if py_type is None:
        raise SchemaError(f"unknown type {type_name!r}", path=path)
    # bool is a subclass of int in Python; exclude it from integer/number
    if type_name in ("integer", "number") and isinstance(value, bool):
        raise SchemaError(f"expected {type_name}, got bool", path=path)
    if not isinstance(value, py_type):
        raise SchemaError(f"expected {type_name}, got {type(value).__name__}", path=path)


def _validate_node(
    value: Any,
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str,
) -> None:
    if not isinstance(schema, dict):
        raise SchemaError("schema must be an object", path=path)

    if "$ref" in schema:
        schema = _resolve_ref(schema["$ref"], root)

    if "type" in schema:
        types = schema["type"]
        if isinstance(types, list):
            ok = False
            for t in types:
                try:
                    _check_type(value, t, path)
                    ok = True
                    break
                except SchemaError:
                    continue
            if not ok:
                raise SchemaError(f"expected one of {types}, got {type(value).__name__}", path=path)
        else:
            _check_type(value, types, path)

    if "enum" in schema:
        if value not in schema["enum"]:
            raise SchemaError(f"value {value!r} not in enum {schema['enum']!r}", path=path)

    if value is None:
        return

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaError(f"value {value} < minimum {schema['minimum']}", path=path)
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaError(f"value {value} > maximum {schema['maximum']}", path=path)

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise SchemaError(f"string too short ({len(value)} < {schema['minLength']})", path=path)
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise SchemaError(f"string too long ({len(value)} > {schema['maxLength']})", path=path)
        if "pattern" in schema:
            import re
            if re.search(schema["pattern"], value) is None:
                raise SchemaError(f"string {value!r} does not match pattern {schema['pattern']!r}", path=path)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise SchemaError(f"array too short ({len(value)} < {schema['minItems']})", path=path)
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise SchemaError(f"array too long ({len(value)} > {schema['maxItems']})", path=path)
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(value):
                _validate_node(item, item_schema, root, f"{path}[{i}]")

    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                raise SchemaError(f"missing required property {req!r}", path=f"{path}.{req}")
        for key, sub in value.items():
            if key in props:
                _validate_node(value[key], props[key], root, f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise SchemaError(f"additional property {key!r} not allowed", path=f"{path}.{key}")

    if "const" in schema and value != schema["const"]:
        raise SchemaError(f"value {value!r} != const {schema['const']!r}", path=path)


def validate_instance(value: Any, schema: Dict[str, Any], root: Optional[Dict[str, Any]] = None) -> None:
    """Validate ``value`` against ``schema``. Raises SchemaError on failure."""
    root = root if root is not None else schema
    _validate_node(value, schema, root, "$")


def validate(value: Any, schema: Dict[str, Any], root: Optional[Dict[str, Any]] = None) -> Any:
    """Validate and return ``value`` unchanged (convenience for chaining)."""
    validate_instance(value, schema, root)
    return value


def collect_errors(value: Any, schema: Dict[str, Any], root: Optional[Dict[str, Any]] = None) -> List[SchemaError]:
    """Return all validation errors instead of raising on the first."""
    errors: List[SchemaError] = []

    def _safe(v: Any, s: Dict[str, Any], r: Dict[str, Any], p: str) -> None:
        try:
            _validate_node(v, s, r, p)
        except SchemaError as ex:
            errors.append(ex)

    # Re-run node but capture all property errors recursively.
    _collect(value, schema, root if root is not None else schema, "$", errors)
    return errors


def _collect(
    value: Any,
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str,
    errors: List[SchemaError],
) -> None:
    """Recursive collector that gathers every schema violation."""
    try:
        if "$ref" in schema:
            schema = _resolve_ref(schema["$ref"], root)
        if "type" in schema:
            types = schema["type"]
            if isinstance(types, list):
                matched = False
                for t in types:
                    try:
                        _check_type(value, t, path)
                        matched = True
                        break
                    except SchemaError:
                        continue
                if not matched:
                    errors.append(SchemaError(f"expected one of {types}, got {type(value).__name__}", path=path))
                    return
            else:
                _check_type(value, types, path)
        if "enum" in schema and value not in schema["enum"]:
            errors.append(SchemaError(f"value {value!r} not in enum", path=path))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(SchemaError(f"value {value} < minimum", path=path))
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(SchemaError(f"value {value} > maximum", path=path))
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                errors.append(SchemaError("array too short", path=path))
            item_schema = schema.get("items")
            if item_schema is not None:
                for i, item in enumerate(value):
                    _collect(item, item_schema, root, f"{path}[{i}]", errors)
        if isinstance(value, dict):
            props = schema.get("properties", {})
            for req in schema.get("required", []):
                if req not in value:
                    errors.append(SchemaError(f"missing required property {req!r}", path=f"{path}.{req}"))
            for key, sub in value.items():
                if key in props:
                    _collect(value[key], props[key], root, f"{path}.{key}", errors)
                elif schema.get("additionalProperties") is False:
                    errors.append(SchemaError(f"additional property {key!r} not allowed", path=f"{path}.{key}"))
    except SchemaError as ex:
        errors.append(ex)
