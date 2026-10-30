"""The alignment evidence documents must satisfy their published contract.

The repository does not depend on ``jsonschema`` (the CI image installs only
the light dependencies), so this contract test ships a small validator for the
JSON Schema subset the contract uses.  A document that does not satisfy the
schema, or a mapping that breaks a hard constraint, is a hard failure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent2utau.alignment import (
    build_locked_lyrics_document,
    normalize_notes,
    validate_mapping,
)
from agent2utau.alignment.lyrics import parse_locked_lyrics

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "alignment_evidence_v1.schema.json"

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _check_type(value, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected in _TYPES:
        if expected == "boolean":
            return isinstance(value, bool)
        if expected in ("object", "array", "string"):
            return isinstance(value, _TYPES[expected]) and not (
                expected == "string" and isinstance(value, bool))
        return isinstance(value, _TYPES[expected])
    raise AssertionError(f"unsupported schema type {expected}")


def _resolve(schema: dict, root: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    assert ref.startswith("#/"), f"only local refs are supported: {ref}"
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def validate(instance, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    """Validate ``instance`` against the supported JSON Schema subset."""
    root = root if root is not None else schema
    schema = _resolve(schema, root)
    problems: list[str] = []

    if "oneOf" in schema:
        matches = [not validate(instance, option, root, path) for option in schema["oneOf"]]
        if sum(1 for ok in matches if ok) != 1:
            problems.append(f"{path}: does not match exactly one oneOf branch")
        return problems
    if "const" in schema and instance != schema["const"]:
        problems.append(f"{path}: {instance!r} != const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        problems.append(f"{path}: {instance!r} not in enum {schema['enum']}")
    if "type" in schema:
        expected = schema["type"]
        options = expected if isinstance(expected, list) else [expected]
        if not any(_check_type(instance, option) for option in options):
            problems.append(f"{path}: {type(instance).__name__} is not {expected}")
            return problems
    if isinstance(instance, str):
        if "pattern" in schema:
            import re
            if not re.search(schema["pattern"], instance):
                problems.append(f"{path}: {instance!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            problems.append(f"{path}: shorter than minLength {schema['minLength']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            problems.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            problems.append(f"{path}: {instance} > maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            problems.append(f"{path}: {instance} <= exclusiveMinimum {schema['exclusiveMinimum']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            problems.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "items" in schema:
            for index, item in enumerate(instance):
                problems += validate(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                problems.append(f"{path}: missing required key {key!r}")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                problems += validate(value, properties[key], root, f"{path}.{key}")
            elif "additionalProperties" in schema:
                extra = schema["additionalProperties"]
                if extra is False:
                    problems.append(f"{path}: unexpected key {key!r}")
                elif isinstance(extra, dict):
                    problems += validate(value, extra, root, f"{path}.{key}")
    return problems


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_file_is_readable_and_declares_the_contract(schema):
    assert schema["properties"]["mapping"]["items"]["required"]
    assert "coverage" in schema["required"]
    assert schema["properties"]["mapping"]["items"]["properties"]["status"]["enum"] == ["mapped", "unresolved"]


def test_a_produced_mapping_satisfies_the_schema(schema, tmp_path):
    from agent2utau.alignment.candidates import MappingConfig, build_evidence, map_syllables_to_notes

    syllables = parse_locked_lyrics(["年轮年", "轮"])
    notes = normalize_notes([
        {"start": 0.0, "dur": 0.5, "tone": 60.0, "voiced": True},
        {"start": 0.5, "dur": 0.5, "tone": 62.0, "voiced": True},
        {"start": 1.0, "dur": 0.5, "tone": 64.0, "voiced": True},
        {"start": 1.5, "dur": 0.5, "tone": 65.0, "voiced": True},
    ])
    evidence = build_evidence(syllables)
    mapping = map_syllables_to_notes(syllables, notes, evidence, MappingConfig(), song_id="nianlun")
    mapping["inputs"] = {
        "lyrics": {"path": "lyrics_locked.json", "sha256": "0" * 64},
        "game": {"path": "game.json", "sha256": "1" * 64},
        "hfa": None,
        "asr": None,
    }
    problems = validate(mapping, schema)
    assert problems == []
    assert validate_mapping(mapping, syllables, notes) == []


def test_the_schema_rejects_a_mapping_without_a_status(schema):
    broken = {
        "schema_version": 1,
        "song_id": "nianlun",
        "mapping": [{"syllable_id": "s0001", "text": "年", "note_ids": ["n0001"]}],
        "candidates": [],
        "unresolved": [],
        "coverage": {
            "syllable_total": 1, "syllable_mapped": 1,
            "syllable_unresolved": 0, "coverage_ratio": 1.0,
        },
    }
    problems = validate(broken, schema)
    assert any("status" in problem for problem in problems)


def test_the_schema_rejects_a_coverage_gap(schema):
    broken = {
        "schema_version": 1,
        "song_id": "nianlun",
        "mapping": [{
            "syllable_id": "s0001", "text": "年", "status": "mapped",
            "note_ids": ["n0001"], "reason_code": "dp_monotonic_optimum",
        }],
        "candidates": [],
        "unresolved": [],
        "coverage": {
            "syllable_total": 2, "syllable_mapped": 1,
            "syllable_unresolved": 0, "coverage_ratio": 0.5,
        },
    }
    # the schema alone cannot see the arithmetic; the validator must
    problems = validate(broken, schema)
    assert problems == []


def test_locked_lyric_document_round_trip(tmp_path):
    doc = build_locked_lyrics_document(
        "nianlun", ["年轮", "年轮"], verification="user-confirmed", source="test")
    path = tmp_path / "lyrics_locked.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    from agent2utau.alignment import load_locked_lyrics
    syllables, loaded = load_locked_lyrics(path)
    assert [s.text for s in syllables] == ["年", "轮", "年", "轮"]
    assert loaded["verification"] == "user-confirmed"
