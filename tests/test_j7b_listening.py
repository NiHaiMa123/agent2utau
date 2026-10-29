import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import l7j7b_rules as j7b


def test_listening_tracks_clone_renderable_candidate_track():
    candidate = {
        "tracks": [
            {"singer": "YousaV1.65c", "phonemizer": "DiffSingerChinese",
             "renderer_settings": {"renderer": "DIFFSINGER"},
             "track_name": "main", "mute": True, "solo": True},
            {"phonemizer": "Default", "renderer_settings": {}},
        ],
        "voice_parts": [{"track_no": 0}],
    }
    tracks = j7b._listening_tracks(candidate)
    assert len(tracks) == 3
    assert [track["track_name"] for track in tracks] == [
        "A0_neutral", "B_j7b_event_geometry", "C_human_reference"]
    assert all(track["singer"] == "YousaV1.65c" for track in tracks)
    assert all(track["phonemizer"] == "DiffSingerChinese" for track in tracks)
    assert all(track["renderer_settings"] == {"renderer": "DIFFSINGER"}
               for track in tracks)
    assert all(not track["mute"] and not track["solo"] for track in tracks)
    tracks[0]["track_name"] = "changed"
    assert tracks[1]["track_name"] == "B_j7b_event_geometry"
