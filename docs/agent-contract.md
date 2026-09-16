# agent2utau agent contract

All commands print one JSON object on stdout; diagnostics go to stderr.
JSON fields: `schema_version`, `status`, plus command-specific fields.
Status values: `ok | completed | completed_with_warnings | needs_input | failed`.

## Commands (implemented)

- `agent2utau doctor` — probe OpenUtau install, singer, tools, GPU, bridge.
  Split reporting: `files_found` / `singer_loaded` / `render_passed` /
  `automation_passed`.
- `agent2utau inspect-reference <dir>` — parse all `*.ustx`: versions,
  tracks/singers, parts, notes, curves, missing wave files, tempo map.
- `agent2utau migrate-phrase --project <ustx> --track N --out <ustx>`
  [--min-notes --min-ms --max-ms --singer] — extract a ~4-12s sung phrase into
  a minimal single-track project migrated to `YousaV1.65b`; remaps `clr` note
  values by color name and keeps `clNN` curves (same subbank order).
- `agent2utau render-smoke --project <ustx>` — headless render via a2u-bridge
  into `runs/smoke-<ts>/`, then WAV checks (non-silent, duration, clipping).
- `agent2utau roundtrip --project <ustx> --out <ustx>` — load -> save ->
  reload -> re-validate; reports note/phrase counts and lyric equality.
- `agent2utau deploy-bridge [--no-build]` — build+copy a2u-bridge into the
  OpenUtau install dir (generates a2u-bridge.deps.json from OpenUtau.deps.json).

- `agent2utau cover <audio> --singer yousa [--lyrics file.lrc] [--lines a:b]
  [--segments s:e,s:e] [--auto-segments N --seg-len S] [--timeout-min M]`
  — M2 pipeline: ffmpeg decode -> audio-separator (UVR-MDX-NET-Voc_FT, ONNX
  CPU) -> torchfcpe F0 -> recording-matched LRC + acoustic DTW char alignment (or
  faster-whisper ASR fallback when --lyrics is absent) -> notes with melisma
  splits -> fresh USTX (fixed 120bpm axis, one part per line, absolute
  positions) -> bridge render -> mix over instrumental -> pitch/timing eval.
  Writes `report.json`, `score.json`, `cover.ustx`, `audio/vocal_render*.wav`,
  `audio/mix.wav` under `runs/cover-<ts>-<pid>/`. Decode/separate/F0 are
  cached per-source under `runs/_cache/<hash>/`.

## Known limits (M2)

- ASR input arrays must be resampled to 16 kHz (fixed 2026-09-16).
  ASR on singing can still hallucinate with faster-whisper large-v3-turbo on CPU
  (observed "优优独播剧场"/"感谢观看" garbage on 年轮) — pass `--lyrics`
  with timestamped LRC for usable output; the ASR path stays as a
  low-confidence fallback and is marked `lyrics_source: asr:*`.
- Note positions in built USTX are **part-relative** ticks; part.position is
  absolute. (Absolute note ticks render at 2x position — verified bug.)
  Quantize start/end on the same absolute grid before subtracting the part
  anchor. Independently rounding durations can overlap/drop syllables.
- Pitch eval compares rendered vs source F0 per note window; short notes and
  consonant-heavy windows often lack voiced frames -> reported as
  `n_unvoiced`, excluded from cent stats but counted in `coverage` and
  `accuracy_all_notes_100c`. Historical pre-fix F0 metrics are invalid.
- `pitch_confidence` is a measurement heuristic (weak-F0 share, accuracy,
  coverage); `quality_confidence` stays `unverified` pending listening.
- CPU-only: torch+cpu, onnxruntime CPU provider. RTX 5080 unused so far.

## a2u-bridge (internal)

`a2u-bridge.exe` lives inside the OpenUtau install dir (portable mode makes
`PathManager` resolve `Singers/`, `Cache/`, `prefs.json` from its own
directory). Subcommands: `doctor | inspect | roundtrip | render`.
`render --project X --out dir/name.wav` writes `dir/name_<track>.wav` per
non-muted track (mono 16-bit WAV). `--mixdown` writes the project mixdown.

It emulates the Avalonia main thread with a single-thread pump
(`UiScheduler` + `PostOnUIThread`), initializes `DocManager`, searches
singers, loads the project (USTX version auto-upgrades), waits for
phonemization + phrase build, then calls `PlaybackManager.RenderToFiles` /
`RenderMixdown`. Errors are captured through an `ICmdSubscriber` and
returned in the JSON result.
Rendering also rejects note/phoneme validation errors before exporting;
`inspect` includes `invalidNotes` and `invalidPhonemes` per part.

`cover` M4 flags:

- `--iters N` (default 2): render variants. iter0 = baseline; iter1 injects a
  `pitd` curve built from measured source F0 per note
  (`analysis/pitchcurve.py`, smoothed, partial-coverage windows).
  `--pitch-strength 0..1` blends measured cents toward the base tone.
  The variant with better pitch metrics is chosen; both artifacts stay under
  `iterations/` and per-iteration metrics are in `report.json.iterations`.
- `--voice-color NAME` (default `Yousa_Normal`): per-phoneme `clr` expression
  on every note (indices 0-7; unqueried indices are harmless). Name must be
  one of the singer's sorted `voice_color_names`.
- `--compare-colors`: additionally renders all 5 colors on the first segment
  into `iterations/colors/<color>_vocal.wav` for audition; listed in
  `report.json.color_comparison`.
- Lyric auto-discovery: without `--lyrics`, `cover` tries
  `<audio-stem>.lrc` sidecar then `data/lyrics/index.yaml` exact source-SHA256
  match before falling back to ASR. `report.json.lyrics_source` records
  which (`lrc:sidecar:`/`lrc:source-sha256:`/`lrc:<path>`/asr).
  Filename/title alone is not proof of arrangement or timing. Empty timed
  LRC lines end singing before instrumental gaps. Collapsed character
  alignments fail explicitly instead of inventing note durations.
- Mixing measures active vocal windows, matches reference stem level and
  enforces a vocal/accompaniment balance floor. `mix.balance`, effective
  gains and common peak attenuation are recorded in the report.
- Successful automatic renders remain `completed_with_warnings` pending
  perceptual review. Audio existence and low cents error do not establish
  intelligible/correct lyrics. `alignment_verified_by_listener` is false.
- `--no-breaths`: by default an `AP` breath note is auto-inserted at phrase
  starts where a real gap >=0.55s exists (reference-project convention:
  ~0.1-0.75s AP, tone borrowed from the next note). Breaths are excluded
  from pitch evaluation; count is in `report.json.n_breaths`.

- `agent2utau status <run-id>` — read `state.json` + condensed `report.json`.
- `agent2utau resume <run-id>` — re-execute the stored `request.json` in the
  same run dir; per-source cache makes decode/separate/F0 instant, and
  identical phrases hit the OpenUtau render cache.

## Runs

Each `render-smoke`/`cover` creates `runs/<run-id>/` with `state.json`
(atomically written), `run.lock`, `request.json`, `audio/`, `iterations/`,
`debug/`. Per-source deterministic artifacts (decoded wav, separated stems,
f0.npz) live under `runs/_cache/<md5-of-source-path>/` and are reused by any
run of the same file. Original assets, model weights and caches are never
committed to git.
