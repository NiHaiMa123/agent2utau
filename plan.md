# agent2utau — Active Expression Transfer Plan

> Active specification only. Historical experiments, superseded blockers, old metrics and failed
> prototypes remain recoverable from Git history and committed run artifacts; they are intentionally
> not repeated here.
>
> Authority split:
> - `pipeline.md`: verified transcription / lyric / base-score pipeline and immutable upstream facts.
> - `plan2.md`: frozen written-score adjudication history/contract.
> - `plan.md` (this file): current expression-transfer implementation, QA and acceptance work.

## 1. Goal

Input:
- SOURCE vocal/reference;
- the verified GAME + HubertFA base USTX from `pipeline.md`;
- YousaV1.65b / DIFFSINGER.

Output:
- an editable USTX whose written score / lyrics / timing remain unchanged;
- auditable pitch-expression transfer: stable intonation, onset gestures, portamento,
  ornament and vibrato;
- later: DYN / TENC / BREC / VOIC / color/style;
- every accepted candidate bound to real render, QA, hashes and code provenance.

The system is not trying to minimize one F0 error number. It must reproduce the perceptually
important **shape and timing of pitch gestures** while preserving the trusted score.

## 2. Fixed architecture

```text
verified base score
→ Yousa neutral render
→ SOURCE / neutral measured on the same absolute time axis
→ dense residual + frame/evidence state
→ SOURCE and neutral event detection separately
→ event matching / expression delta
→ lowest-complexity valid representation
→ OpenUtau parameter compilation
→ real OpenUtau render
→ topology + event-shape + cross-extractor QA
→ bounded closed-loop correction / rollback
→ machine acceptance
→ human listening
```

There is **no default SOURCE↔neutral DTW/time warp**. A deterministic global transport offset may
only be corrected from independent transport evidence, never from an F0 best-lag search.

Agent/LLM responsibility is limited to high-level diagnosis, experiment choice and bounded
parameter strategy. Signal measurement, candidate generation, rendering and acceptance must be
deterministic/reproducible code.

## 3. Non-negotiable invariants

1. Expression work must not alter trusted note count / identity / lyric / base timing.
2. Current song authority is the 392-note semantic base recorded by `pipeline.md`.
3. Yousa neutral uses the verified Normal color semantics; do not silently depend on option indices.
4. HFA nucleus is carrier/lyric evidence, not a free warp control point.
5. SOURCE and neutral events are detected separately before expression deltas are computed.
6. Missing/low-confidence evidence is **unknown**, not positive or negative evidence.
7. Large residuals are classified before filtering; do not discard them solely by magnitude.
8. Native OpenUtau parameters are used first when they can represent the gesture.
9. Closed-loop correction fixes renderer response/residual error; it must not compensate for a
   knowingly wrong native parameterization.
10. Pointwise cents improvement cannot compensate for worse topology/gesture shape.
11. Same-extractor self-scoring cannot alone authorize PASS; cross-extractor evidence is required.
12. Every machine claim must be tied to committed artifacts. A prose summary is not evidence.
13. Changing a metric/threshold is not a candidate fix unless the metric itself is independently
    shown to be defective.

## 4. Dense evidence layer

At each ~10 ms frame, preserve enough evidence to distinguish at least:

```text
both_voiced
source_only
neutral_only
both_unvoiced
extractor_conflict
note_transition
phoneme_transition / gap
```

Primary residual, only where valid:

```text
residual(t) = SOURCE_F0(t) - neutral_F0(t)
```

Use FCPE + RMVPE as independent measurement families; third-F0 is for material conflicts.
Store raw measurements, residual disagreement, consensus, frame state and confidence before any
simplification.

Do not convert source-only / neutral-only / extractor-conflict frames into high-confidence PITD just
to recover a missing turn.

## 5. Event decomposition

Required structured event families:

- stable trend / intonation;
- scoop / overshoot / undershoot;
- portamento / cross-note transition;
- ornament / short multi-turn gesture;
- vibrato / modulation;
- artifact / timing / phoneme / voicing conflict.

Every `PitchEvent` must retain:
- type, note identities, start/end;
- parameters and confidence;
- extractor/evidence provenance;
- enough local features to reproduce QA.

### 5.1 Vibrato

SOURCE and neutral vibrato must be independently measured with at least:

```text
start/end
rate_hz
depth_c
phase_rad + phase_origin
periods_ms[]
period_cv
cycle_depths/depth_envelope
depth_cv
stable/evidence cycle counts
drift / confidence
```

OpenUtau `shift` must receive the detected phase mapping. Never default `shift=0` and ask PITD or
closed-loop to repair the resulting phase error.

### 5.2 Portamento

Detect real departure and arrival around adjacent notes rather than treating an arbitrary boundary
window as the gesture.

Retain:
- departure/arrival timing;
- span/duration/direction;
- trajectory type;
- normalized trajectory;
- slope/curvature profiles;
- relaxed-arrival flag/offset when SOURCE itself sustains an off-nominal landing.

A relaxed landing is still explicit evidence; it must not be silently converted to a clean match.

## 6. Representation ladder

Use the **lowest complexity representation that passes real-render shape acceptance**.

### Level 1 — native regular vibrato

```text
V(t) = A * sin(phi(t))
phi'(t) ≈ constant
```

Use OpenUtau native length/period/depth/shift/in/out.

### Level 2 — adaptive vibrato

```text
V(t) = A(t) * sin(phi0 + 2π∫f(t)dt)
```

Use only low-DOF amplitude/rate envelopes anchored to measured cycles.

Initial limits:
- amplitude knots: normally 3–6;
- rate knots: normally 2–5;
- no dense 10 ms free-parameter fitting.

### Level 3 — irregular local gesture

```text
Pitch(t)
= WrittenScore(t)
+ TrendResidualSpline(t)
+ AdaptivePeriodicComponent(t)
+ LocalGestureResidual(t)
```

Use local cubic/Hermite/Bézier-style support for nonperiodic/asymmetric gestures. Do not use a
high-order global polynomial.

Escalate representation only when a simpler level fails on **real rendered shape** despite correct
wiring/evidence. Better mathematical fit without better render is not evidence of improvement.

## 7. Real-render QA

Required candidate QA covers:

### 7.1 Position / topology
- median/p90/p95 position error;
- matched / missing / extra turns;
- turn timing/amplitude/prominence;
- sequence edit distance;
- edge-uncertain turns retained separately for audit.

Confirmed-turn non-regression relative to v1 requires:

```text
matched_candidate >= matched_v1
missing_candidate <= missing_v1
extra_candidate   <= extra_v1
edit_candidate    <= edit_v1
```

### 7.2 Event lanes
At minimum portamento and vibrato matched/missing state must not regress relative to v1.

### 7.3 Absolute event shape
For matched portamento/gesture events compare normalized SOURCE / neutral / render overlays and
classify evidence explicitly, e.g.:

```text
match
label_mismatch
boundary_shift
source_irregular
extraction_artifact
shared_voicing_gap
render_voicing_loss
distortion
```

Clean-evidence `distortion` is blocking. Render-only voicing loss is blocking. Evidence defects may
be non-blocking only when the defect is explicitly demonstrated and retained in the artifact.

### 7.4 Cross extractor
Final conclusions must survive an independent F0 family sufficiently to rule out obvious
single-extractor self-scoring.

## 8. Closed-loop and rollback

Normal flow:

```text
v1 first render
→ closed-loop v2
→ topology/event-lane gate
→ PASS: candidate may continue to absolute QA
→ FAIL: one bounded local rollback → real-render v3 → re-QA
→ still FAIL: keep verified baseline and remain blocked
```

`shape_rollback()` is local remediation, not an unlimited optimizer. Maximum automatic rollback
attempts for the same candidate path: 1 unless the plan explicitly authorizes a new experiment.

No candidate is accepted from curve-space evidence alone; rollback must be followed by a real
OpenUtau render and new QA.

## 9. Artifact / provenance contract

For each final candidate retain at least:

```text
candidate USTX
real rendered WAV
source/neutral/render events
position/slope/curvature/topology/modulation QA
vibrato/portamento/event-shape QA
cross-extractor QA
run_manifest.json
```

Manifest must distinguish:

```text
generator_code_head
qa_code_head
base_semantic_sha256
candidate_ustx_sha256
render_wav_sha256
candidate variant
gate verdicts
```

`generator_code_head` must name code capable of producing the committed candidate bytes. Reusing an
older code head merely because the run lineage began there is invalid provenance.

## 10. Current state — R2.1/L7

Verified direction:
- native phase→`shift`;
- neutral-only suppression no longer depends on closed-loop;
- closed-loop event-lane protection exists;
- turning-point edge uncertainty is preserved rather than silently discarded;
- production `run_shape_gate` can execute v1→v2→rollback→real v3→re-QA;
- P1/P3 have exercised real rollback paths; P2 has exercised direct v2 acceptance;
- absolute event-shape artifacts exist;
- provenance is split into generator vs QA code heads.

Reviewer patches after the latest executor run:
- final-candidate manifests were corrected so `generator_code_head` points to
  `8be5bd1bf84c86f282ae85a3bb31af10b88e4775`, the implementation that can actually
  produce the changed candidates;
- event-shape QA now distinguishes:
  - render-only dropout → `render_voicing_loss` → blocking;
  - render + neutral shared dropout → `shared_voicing_gap` → non-blocking;
- corresponding regression coverage was added.

### Active blocker

Human listening remains blocked until the latest HEAD proves, on fresh P1/P2/P3 real renders:

1. full pytest passes;
2. topology gate passes;
3. event-lane gate passes;
4. **absolute event-shape verdict is wired into final candidate acceptance**, not merely emitted as
   a JSON report;
5. `event_shape_metrics.json` has zero blocking events under the corrected voicing logic;
6. manifests bind the actual generator/QA code heads and current artifact hashes;
7. all required evidence is present and internally consistent.

Only after this machine closure may L7-E human listening begin.

## 11. Roadmap after L7

### R2.5 — detector dataset/training
Blocked until deterministic detector/QA semantics are accepted. Then:
- deterministic outputs become auditable pseudo-label candidates;
- retain synthetic + human labels;
- song-held-out validation/test;
- train event class / event parameters / confidence, not hundreds of direct PITD points.

### R3 — event-aware compiler
After L7 acceptance:
- compile verified event deltas;
- extend parameterized support for portamento/onset/ornament;
- use representation ladder event-by-event;
- synthetic test first, then real-song validation.

### R4 — closed-loop calibration
- learn/bound renderer response;
- 1–3 bounded corrections only when explicitly justified;
- objective includes topology and event shape, not just cents.

### R5 — other expression lanes
- DYN;
- BREC/VOIC;
- TENC experimental;
- lane-isolated QA.

### R6/R7 — controller and Yousa style
- evidence-aware Agent controller;
- rollback/replan;
- five-color calibration;
- Yousa style prior from reference songs.

### R8 — full-song acceptance
Run the complete song with immutable score, auditable event pipeline, machine QA and targeted human
listening.

## 12. Definition of Done

The project is done only when it can take a verified base score and reproducibly:

1. render a controlled neutral baseline;
2. measure SOURCE-neutral evidence on the fixed absolute time axis;
3. decompose perceptually important pitch gestures into auditable events;
4. compile the lowest-complexity representation that reproduces those gestures;
5. real-render and re-measure the result;
6. reject or rollback pointwise improvements that damage shape;
7. separate measurement uncertainty from actual candidate defects;
8. preserve written score / lyrics / timing;
9. bind every accepted artifact to generator code, QA code and file hashes;
10. pass machine acceptance before human listening;
11. when human listening exposes a metric blind spot, create an explicit evidence artifact and improve
    the metric/representation rather than overriding the listening result with a lower cents score.
