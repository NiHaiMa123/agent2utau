"""Selected separator bundle and cache migration regressions."""
import copy
import hashlib
import importlib
import json

import pytest

module = importlib.import_module("agent2utau.audio.separate")


def test_source_and_separator_conditions_get_distinct_cache_keys():
    settings = {"model": module.DEFAULT_MODEL, "model_sha256": "weight1",
                "config_sha256": "yaml1", "audio_separator_version": "0.47",
                "mdxc_params": {"batch_size": 1}}
    original = module.separation_cache_key("source1", settings)
    assert module.separation_cache_key("source2", settings) != original
    for field in ("model", "model_sha256", "config_sha256", "audio_separator_version"):
        changed = dict(settings, **{field: "changed"})
        assert module.separation_cache_key("source1", changed) != original
    changed = copy.deepcopy(settings)
    changed["mdxc_params"]["batch_size"] = 2
    assert module.separation_cache_key("source1", changed) != original
    assert module.separation_cache_key("source1", dict(reversed(list(settings.items())))) == original


def test_bundle_requires_matching_weight_and_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "MODEL_DIR", tmp_path)
    files = {}
    for filename in (module.DEFAULT_MODEL, module.CONFIG_FILE, "download_checks.json"):
        data = filename.encode()
        (tmp_path / filename).write_bytes(data)
        files[filename] = {"sha256": hashlib.sha256(data).hexdigest()}
    (tmp_path / "manifest.json").write_text(json.dumps({"files": files}))
    settings = module.separation_settings()
    assert settings["model_path"] == str(tmp_path / module.DEFAULT_MODEL)
    (tmp_path / module.CONFIG_FILE).write_text("changed")
    with pytest.raises(RuntimeError, match="bundle missing or changed"):
        module.separation_settings()


def test_observation_cli_has_no_automatic_cover_route():
    from agent2utau.cli import build_parser
    parser = build_parser()
    assert parser.parse_args(['observe-source','song.wav','--out','runs/new']).steps == 'separate,asr,game,fcpe,rmvpe'
    with pytest.raises(SystemExit): parser.parse_args(['cover','song.wav'])
