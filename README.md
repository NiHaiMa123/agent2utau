# agent2utau

One-shot DiffSinger cover pipeline driving the local OpenUtau install with
the Yousa (泠鸢) voicebank. See `plan.md` for the full implementation plan and
`docs/agent-contract.md` for the CLI/JSON contract.

## Status

M0 + M1 minimal pass-through: **working**.

- `doctor` — environment probe (files_found / singer_loaded / render_passed /
  automation_passed split).
- `inspect-reference` — parses the 5 reference USTX projects.
- `migrate-phrase` — migrates a short vocal phrase from an old-format project
  to `YousaV1.65b` (singer id, `clr` color indices remapped by name, `clNN`
  curve semantics preserved, missing audio refs dropped).
- `render-smoke` — headless render through `a2u-bridge` (a small exe deployed
  into the OpenUtau install dir that reuses `OpenUtau.Core` to load, phonemize
  and render via `PlaybackManager.RenderToFiles`). Verified: 3 different
  phrases render non-silent mono 44.1k WAV in seconds; load/save roundtrip
  preserves notes/lyrics; runs are repeatable.

Not yet implemented: audio separation/ASR/F0 (M2), full-song `cover` (M3),
style transfer (M4).

## Layout

```
src/agent2utau/     Python pipeline + CLI
bridge/OuBridge/    .NET headless render driver (deployed into OpenUtau dir)
configs/            defaults + local overrides (local.yaml git-ignored)
docs/               agent contract
schemas/            JSON schemas (state/analysis/score/evaluation)
tests/fixtures/     self-made small projects & structured test data
runs/               per-run outputs (git-ignored)
```

## Usage

```powershell
uv pip install -e .
agent2utau doctor
agent2utau inspect-reference "E:\data\project_opentuau"
agent2utau migrate-phrase --project "<ref>.ustx" --track 0 --out runs/x/phrase.ustx
agent2utau render-smoke --project runs/x/phrase.ustx
```

Bridge deploy (only needed once or after bridge code changes):

```powershell
agent2utau deploy-bridge
```

## Render path decision (plan §6.2)

Option 1 (CLI) does not exist: `Program.Main` only forwards a project path to
the GUI. Option 3 was taken: `a2u-bridge` is a self-contained exe placed in the
install dir (no OpenUtau files modified; `a2u-bridge.deps.json` cloned from
`OpenUtau.deps.json` so assembly resolution is identical). It reuses the app's
own `Formats`/`DocManager`/`PhonemizerRunner`/`RenderEngine` — no reimplemented
inference. UI automation (option 2) remains a fallback if the bridge breaks on
an app update.
