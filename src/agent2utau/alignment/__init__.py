"""Lyric <-> note alignment: locked identities, normalized clock, mapping.

The modules are deliberately small and independent:

* ``lyrics``       - locked text -> stable syllable ids
* ``notes``        - GAME note events -> stable note ids and one-grid ticks
* ``observations`` - ASR/HFA evidence and the input manifest
* ``candidates``   - deterministic monotonic mapping and window candidates
* ``validator``    - the hard constraints of plan.md P1

``phonemes`` (native phoneme baseline) and ``patch`` (write-back) belong to
P2 and are not implemented here.
"""

from .lyrics import (
    Syllable,
    build_locked_lyrics_document,
    load_locked_lyrics,
    parse_locked_lyrics,
)
from .notes import NoteEvent, load_game_notes, note_anomalies, normalize_notes
from .observations import (
    Observation,
    build_observations_manifest,
    file_entry,
    load_asr_observations,
    load_hfa_observations,
    match_observations,
    sha256_file,
)
from .candidates import (
    MappingConfig,
    SyllableEvidence,
    build_evidence,
    line_intervals,
    map_syllables_to_notes,
    mapping_to_ustx_rows,
)
from .status import (
    STATUS_INCOMPLETE,
    STATUS_INVALID,
    STATUS_VALID,
    classify,
    exit_code,
)
from .validator import validate_locked_lyrics, validate_mapping, validate_ustx_rows

__all__ = [
    "Syllable",
    "build_locked_lyrics_document",
    "load_locked_lyrics",
    "parse_locked_lyrics",
    "NoteEvent",
    "load_game_notes",
    "note_anomalies",
    "normalize_notes",
    "Observation",
    "build_observations_manifest",
    "file_entry",
    "load_asr_observations",
    "load_hfa_observations",
    "match_observations",
    "sha256_file",
    "MappingConfig",
    "SyllableEvidence",
    "build_evidence",
    "line_intervals",
    "map_syllables_to_notes",
    "mapping_to_ustx_rows",
    "STATUS_VALID",
    "STATUS_INCOMPLETE",
    "STATUS_INVALID",
    "classify",
    "exit_code",
    "validate_locked_lyrics",
    "validate_mapping",
    "validate_ustx_rows",
]
