"""A4 §5.4/§5.5 regressions: separator cache provenance binds actual
resolved model bytes + config, never a guessed library-internal path."""
import hashlib
import json

from agent2utau.diagnostic.run import _cache_fresh


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _manifest(tmp_path, model_bytes=b"model-bytes", cfg=None):
    model = tmp_path / "actual_model.onnx"
    model.write_bytes(model_bytes)
    cfg = cfg or {"model": "m.onnx", "output_format": "WAV",
                  "backend": "onnxruntime-cpu"}
    return {
        "schema": "s1",
        "source_sha256": "src123",
        "separator_model": "m.onnx",
        # actual resolved path recorded by separate() — could be anywhere
        "separator_model_path": str(model),
        "separator_model_sha256": _sha(model),
        "separator_config_sha256": hashlib.sha256(
            json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
    }


def test_a4_cache_hit_when_everything_matches(tmp_path):
    man = _manifest(tmp_path)
    cfg_sha = man["separator_config_sha256"]
    assert _cache_fresh(man, "src123", "m.onnx", cfg_sha, "s1", _sha)


def test_a4_model_bytes_change_invalidates(tmp_path):
    man = _manifest(tmp_path)
    cfg_sha = man["separator_config_sha256"]
    # same path, same name — bytes swapped underneath
    (tmp_path / "actual_model.onnx").write_bytes(b"tampered")
    assert not _cache_fresh(man, "src123", "m.onnx", cfg_sha, "s1", _sha)


def test_a4_config_change_invalidates(tmp_path):
    man = _manifest(tmp_path)
    assert not _cache_fresh(man, "src123", "m.onnx", "other-cfg-sha",
                          "s1", _sha)


def test_a4_source_change_invalidates(tmp_path):
    man = _manifest(tmp_path)
    cfg_sha = man["separator_config_sha256"]
    assert not _cache_fresh(man, "srcDIFFERENT", "m.onnx", cfg_sha,
                          "s1", _sha)


def test_a4_missing_model_file_invalidates(tmp_path):
    man = _manifest(tmp_path)
    (tmp_path / "actual_model.onnx").unlink()
    assert not _cache_fresh(man, "src123", "m.onnx",
                          man["separator_config_sha256"], "s1", _sha)


def test_a4_guessed_path_never_used(tmp_path):
    # manifest must point at the actual resolved path; if the recorded
    # actual path doesn't exist we are stale — even if some guessed
    # default location happens to hold a model file.
    man = _manifest(tmp_path)
    man["separator_model_path"] = str(tmp_path / "nonexistent" / "m.onnx")
    assert not _cache_fresh(man, "src123", "m.onnx",
                          man["separator_config_sha256"], "s1", _sha)
