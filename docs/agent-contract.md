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

## Commands (stubbed)

- `agent2utau cover <audio>` — full pipeline; requires M2 (separation/ASR/F0).

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

## Runs

Each `render-smoke`/`cover` creates `runs/<run-id>/` with `state.json`
(atomically written), `run.lock`, `audio/`, `iterations/`, `debug/`.
Original assets, model weights and caches are never committed to git.
