# GAME diagnostic report — 《年轮》 (M2.1.1 corrected)

source: `E:\data\music\年轮 - 张碧晨.flac`  
run: `diag-20260917-181538-6aec`  

## Variant note counts

| variant | sung notes | rests | sung duration |
|---|---|---|---|
| A_raw | 428 | 76 | 179.4s |
| B_zh | 420 | 78 | 179.23s |
| C_forced_boundaries | 762 | 84 | 179.25s |

## Variant alignment (onset-time matching, no index zip)

- A_vs_B: matched=388, a_only=5, b_only=1, pitch_disagree>1st=0, median_onset_drift=0.0ms
- A_vs_C_forced: matched=110, a_only=8, b_only=53, pitch_disagree>1st=0, median_onset_drift=-0.0ms
- consensusA_vs_consensusB: matched=381, a_only=7, b_only=6, pitch_disagree>1st=5, median_onset_drift=0.0ms

## M2.1.2 GAME stochastic consensus

runs: 5 per config

- raw note counts: [417, 420, 419, 425, 428]
- zh note counts: [420, 427, 426, 421, 419]
- consensus raw: {'n_events': 401, 'GAME_STABLE': 358, 'GAME_VARIABLE': 1, 'GAME_UNSTABLE': 42, 'structure_varies': 38}
- consensus zh: {'n_events': 398, 'GAME_STABLE': 357, 'GAME_VARIABLE': 3, 'GAME_UNSTABLE': 38, 'structure_varies': 38}


## M2.3 residual-error triage

- `baseline_notes`: 428
- `GAME_LIKELY_CORRECT`: 341
- `AMBIGUOUS_ORNAMENT`: 16
- `STRUCTURE_CANDIDATE`: 45
- `F0_EXTRACTOR_CONFLICT`: 19
- `NEEDS_LISTENING_REVIEW`: 6
- `PITCH_HARD_SUSPICIOUS`: 1
- `decisions`: keep_baseline=311, auto_resolved=50, needs_phrase_review=46, resolved_change_candidate=21
- `safe_retune_candidates`: 1


## GAME-raw suspicious regions (RMVPE structural evidence)

flagged: **240** / 428 voiced notes

- `high_dispersion`: 236
- `wrong_pitch`: 45
- `very_short_isolated_note`: 3
- `possible_octave_error`: 2

## Lyric-boundary matching (overlay, never forced)

- `possible_snap`: 265
- `matched`: 56
- `unsupported_lyric_boundary`: 27
- `possible_missing_boundary`: 1

## Artifacts

- `game_raw.*` — variant A baseline (ustx + vocal render)
- `game_zh.json` — variant B (language=zh)
- `game_forced_boundaries.*` — EXPERIMENTAL variant C
- `rmvpe_f0.npz`, `structural_f0.npz` — evidence layer
- `raw_evidence_packets.json`, `raw_suspicious_regions.json`
- `lyric_boundary_matches.json`, `variant_alignment.json`
- `alignment/line_*.json` — whisper-DTW char boundaries

听音顺序建议：game_raw → 与原唱对轨；forced-boundary 仅实验对照。
