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

## 10. Machine acceptance contract

The executor does not have authority to declare itself done from prose. It produces code, artifacts
and evidence; a fixed acceptance evaluation decides state.

### 10.1 Gate states

Every required gate must be exactly one of:

```text
PASS      positive evidence proves the rule
FAIL      evidence proves the rule is violated
UNKNOWN   required evidence exists but is insufficient/ambiguous
NOT_RUN   required verification was not executed
```

For required gates:

```text
PASS is the only non-blocking state.
FAIL / UNKNOWN / NOT_RUN all block.
```

Absence of detected failure is **not** evidence of success.

### 10.2 Implementation maturity

Do not equate code existence with completion. A feature progresses through:

```text
IMPLEMENTED  code/helper exists
WIRED        production path can reach it
EXECUTED     the current real run actually exercised the path
VERIFIED     execution produced evidence satisfying acceptance
```

Only `VERIFIED` may close a blocker.

For example, rollback is not VERIFIED merely because `shape_rollback()` and a unit test exist.
Verification requires production reachability, an exercised failure path, a real post-rollback
OpenUtau render, recomputed QA and a bound manifest.

### 10.3 Final machine-ready expression

Human listening is allowed only when all required terms are PASS:

```text
HUMAN_LISTENING_READY =
    tests
AND real_render
AND topology_gate
AND event_lane_gate
AND absolute_event_shape_gate
AND render_voicing_gate
AND cross_extractor_gate
AND provenance_gate
AND artifact_consistency_gate
AND blocking_issue_count == 0
AND unknown_required_gate_count == 0
```

This expression must be evaluated from committed evidence, not reconstructed from a plan summary.

Relative and absolute quality are separate:

```text
relative gate: candidate is not worse than verified baseline
absolute gate: candidate is actually good enough for the defined target
```

Both are required. “No regression from v1” alone is never an absolute quality PASS.

### 10.4 Gate-change rule

A failing candidate must not be made to pass by relaxing its judge.

Changing a metric, threshold, mask, label mapping or blocking classification is allowed only when a
separate experiment demonstrates a measurement/definition defect independent of the candidate
failure. The old and new evaluations must both remain auditable.

## 11. Failure classification and escape policy

Strict gates must not create an infinite “keep fixing until green” loop. Every failed attempt must be
classified before another attempt on the same blocker.

### 11.1 Failure classes

```text
FAIL_FIXABLE
  implementation/wiring/provenance/parameter bug while the current architecture remains supported
  by evidence
  → bounded fix on the same route

FAIL_EVIDENCE
  observability is insufficient or extractors disagree materially
  → collect/repair evidence; do not tune the candidate against unknown truth
  → any required acceptance term depending on that target is UNKNOWN until
    the evidence is explicitly resolved; threshold reclassification alone
    cannot turn FAIL_EVIDENCE into PASS

FAIL_CAPABILITY
  the current representation/model cannot express the verified target even when correctly wired
  → escalate representation/model capability

FAIL_STRATEGY
  a core assumption/architecture is contradicted by evidence
  → stop local patching; replan or roll back to the previous milestone
```

The executor is allowed and expected to return a blocked failure class. It is **not** required to
make every gate pass.

### 11.2 Bounded attempts / no-progress gate

For one blocker and one repair strategy, default maximum is **3 material attempts**.

An attempt counts only when it changes a causal hypothesis, implementation or representation and is
followed by the required verification. Cosmetic commits do not reset the budget.

Before a fourth same-strategy attempt, escalation review is mandatory.

```text
NO_PROGRESS =
    same_blocker_attempts >= 3
AND no_new_causal_evidence
AND no_material_improvement_on_blocking_gate
```

When `NO_PROGRESS` is true:
- stop the current repair strategy;
- classify as FAIL_EVIDENCE / FAIL_CAPABILITY / FAIL_STRATEGY;
- run a discriminating experiment or replan;
- do not continue parameter sweeps of the same idea.

### 11.3 Every failure must buy information

A repeated failed run is useful only if it adds at least one of:

- new root-cause evidence;
- a test that distinguishes competing hypotheses;
- new observability;
- a justified representation escalation;
- an architecture correction.

Changing `depth_gain`, `max_err_c`, tolerance or another scalar and rerunning without a stated,
testable hypothesis is not acceptable progress.

### 11.4 Representation escalation

Escalate Level 1 → Level 2 → Level 3 only after:
1. implementation/wiring gates are VERIFIED;
2. evidence is sufficiently observable;
3. the simpler representation repeatedly fails an absolute shape gate for the same causal reason;
4. a controlled A/B real render shows the richer representation addresses that reason.

If richer representation does not improve real-render shape, roll back instead of adding more
degrees of freedom.

### 11.5 Strategy review triggers

Immediate strategy review, without consuming all three attempts, is required when:
- fixes improve one gate only by repeatedly breaking another;
- the same control curve produces materially context-dependent renderer behavior that invalidates
  the assumed response model;
- the target is not observable reliably enough for the current objective;
- success would require changing the acceptance rule rather than the candidate;
- a new result contradicts a core architecture assumption.

The goal is **legitimate determination**, not forced success:

```text
determine whether the candidate can pass
→ if yes, prove PASS
→ if no, classify why
→ fix, measure, escalate or replan according to evidence
```

## 12. Current state — R2.1/L7

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

Executor run at `c4aab1df` (artifacts `96805d1`), via committed driver
`tools/l7_phrase_gate.py` on fresh real renders:

- `run_shape_gate` now takes `event_shape_fn` and enforces the absolute
  event-shape verdict on v2/v3 alongside topology + event-lane QA.
  The gate is fail-closed: a missing callback cannot produce an accepted
  candidate.
- Executor reported 500 pytest passes, but the repository currently has no
  CI/status artifact bound to that run; under §10 this is not yet sufficient
  to mark the global `tests` readiness term PASS by prose alone.
- **P1_sustain**: v2 topology regression → one bounded rollback → real v3
  render → C3v3 has clean topology/event-lane/event-shape evidence and
  0 blocking event-shape events.
- **P2_slides**: v2/v3 carry blocking `distortion` at note 4 / note 8;
  v1 is retained only as fallback and the phrase remains blocked.
- **P3_vibrato**: v2/v3 carry blocking `distortion` at note 9;
  v1 is retained only as fallback and the phrase remains blocked.
- Manifests bind generator/QA head `c4aab1df` and current artifact SHA256s.

Reviewer recheck after that run:
- fixed `run_shape_gate` so a fallback v1 whose absolute event-shape QA fails
  is no longer reported as `gate_passed=true`; retention is not acceptance;
- therefore P2/P3 manifests from `96805d1` are stale with respect to current
  gate-state semantics and must be regenerated;
- current `run_manifest.json` has no single machine evaluator for the full
  §10.3 `HUMAN_LISTENING_READY` expression. Cross-extractor metrics,
  provenance fields and artifact coverage exist, but they are not yet
  converted into PASS/FAIL/UNKNOWN/NOT_RUN verdicts;
- `base_semantic_sha256` in the phrase driver is currently populated by the
  raw file `sha256(BASE_USTX)`. That is a file hash, not a semantic-notes
  hash. Next manifest schema must distinguish `base_file_sha256` from the
  upstream semantic score hash.

Executor implementation at `43bfe26c` produced a useful discriminating
result, but the committed artifacts from that run are **STALE / NOT
ACCEPTANCE-AUTHORITATIVE** after reviewer recheck.

What the run legitimately established:

- **P2 note 4 — FAIL_FIXABLE.** The experiment strongly separates carrier
  choice from model capability: dense/step PITD stayed poor, while native
  target-note `pitch.data` reduced normalized shape RMSE from 0.586 to
  0.098. A dedicated portamento carrier is therefore justified.
- **P2 note 8 — FAIL_EVIDENCE.**
- **P3 note 9 — FAIL_EVIDENCE.**
  The committed probe implementation only compares FCPE vs RMVPE for this
  classification. Earlier prose claiming independent librosa-pYIN evidence
  is unsupported: no pYIN/librosa implementation or artifact exists in
  `tools/l7_portamento_probe.py`. Do not cite a third extractor until it
  is actually committed and bound.
- `base_file_sha256` vs canonical `base_semantic_sha256` is now correctly
  separated.
- a single §10.3 acceptance evaluator now exists.

Reviewer blockers discovered in the same run:

1. **Dirty-worktree provenance — FAIL_FIXABLE.**
   `compile_portamento_lane`, the new evaluator and related code were first
   committed at `43bfe26c`, but the generated manifests and
   `acceptance_eval.json` claim code/evaluator head `20c3cc69`.
   Therefore those artifacts were produced from `HEAD=20c3cc69` plus
   uncommitted source changes; that HEAD cannot reproduce them.
   P1/P2 PASS claims from that bundle are invalid under §9/§10.

   Reviewer patches now require a clean git worktree before:
   - `l7_phrase_gate.py` real-render generation;
   - `l7_portamento_probe.py` probes;
   - `l7_acceptance_eval.py` evaluation.
   New manifests must record `worktree_clean_at_generation=true`, and the
   evaluator must reject a missing/false marker.

2. **FAIL_EVIDENCE may not collapse to PASS.**
   P2 note8 was diagnosed `FAIL_EVIDENCE`, yet the old evaluator later
   marked P2 PASS because the current FCPE event happened to fall below a
   blocking threshold / classify as `extraction_artifact`.
   That is not an evidence adjudication. Under §10.1/§11.1 an unverified
   SOURCE target is `UNKNOWN`, and UNKNOWN blocks.
   Reviewer evaluator logic now carries unresolved probe
   `FAIL_EVIDENCE` into `absolute_event_shape_gate=UNKNOWN` and
   `cross_extractor_gate=UNKNOWN` unless a later evidence run resolves it.
   The same applies to P3 note9.

3. **Portamento lane isolation is not yet proved.**
   Current `compile_portamento_lane` samples SOURCE from roughly
   `event_start-30ms` through the **end of the target note**, and
   `flatten_pitd_spans` hands that whole span to `pitch.data`.
   Example: the ~40 ms P2 note4 portamento owns approximately
   52.88–53.25 s. This may absorb later stable intonation/onset/ornament
   content into the portamento lane.
   Before full-song acceptance, run an isolation A/B:
   - current full-target-note ownership;
   - event-bounded ownership + only the minimum settle/return anchors needed
     by OpenUtau.
   Compare event shape **and** out-of-event position/topology/event lanes.
   Prefer the narrower ownership if it preserves the portamento result.
   Portamento ownership must never silently overlap another confirmed
   non-portamento event.

### Active blocker / next run

**RESOLVED at `03e6c16`+ evidence bundle: all three phrases are
machine-accepted; global `HUMAN_LISTENING_READY=PASS`.**

Executed from clean committed HEADs (every generation tool now refuses
a dirty worktree and records `worktree_clean_at_generation=true`):

1. full pytest: 500 passed (re-run by the evaluator itself);
2. lane-isolation A/B (`runs/expr-20260921/lane_ab/`): `event`-bounded
   ownership preferred on P1/P3 (equal in-event shape, better in-lane
   error, out-of-lane within +5c); `full_note` retained on P2 because
   the narrower mode flips the marginal note-8 row into blocking on both
   families;
3. P1/P2/P3 regenerated through `l7_phrase_gate.py` with the preferred
   per-phrase ownership; manifests record the executing code head;
4. portamento probe re-run from clean HEAD with a committed third
   extractor (librosa pYIN, `diagnostic/adjudicate.third_f0_pyin`):
   - **P2 note4 — FAIL_FIXABLE**, resolved in production
     (`label_mismatch`, cn_rmse 0.07, non-blocking);
   - **P2 note8 — EVIDENCE_ADJUDICATED_ARTIFACT**: pYIN is voiced on
     0.0% of the fcpe-voiced/rmvpe-unvoiced disputed frames — two
     independent families reject the gesture;
   - **P3 note9 — EVIDENCE_ADJUDICATED_ARTIFACT**: same finding;
   - the evaluator excludes adjudicated-artifact events from
     `blocking_issue_count` (listed as `adjudicated_artifact_events`);
     a stale/dirty probe report would instead count them unresolved;
5. `l7_acceptance_eval.py` from clean HEAD
   (`runs/expr-20260921/acceptance_eval.json`):

```text
P1_sustain: all 9 terms PASS  -> READY=PASS
P2_slides:  all 9 terms PASS  -> READY=PASS
P3_vibrato: all 9 terms PASS  -> READY=PASS
GLOBAL:     all 9 terms PASS, blocking_issue_count=0,
            unknown_required_gate_count=0
            -> HUMAN_LISTENING_READY=PASS
```

**Next gate is human listening** on the three committed candidate WAVs:
- `phrases3/P1_sustain/P1_sustain_C3v2_vocal.wav`
- `phrases3/P2_slides/P2_slides_C3_v1_vocal.wav`
- `phrases3/P3_vibrato/P3_vibrato_C3_v1_vocal.wav`

Historical requirement (kept for the audit trail): SWE2 had to, from the
latest committed clean HEAD — run pytest; rerun P1/P2/P3 through
`l7_phrase_gate.py`; commit regenerated manifests; rerun the probe where
required; resolve P2 note8/P3 note9 evidence via a third extractor or an
explicit adjudication artifact; perform the lane-isolation A/B; commit
all evidence; run `l7_acceptance_eval.py`.  All eight steps are done and
committed in this bundle.

## 13. Roadmap after L7

### R2.5 — detector dataset/training
Blocked until deterministic detector/QA semantics are accepted. Then:
- deterministic outputs become auditable pseudo-label candidates;
- retain synthetic + human labels;
- song-held-out validation/test;
- train event class / event parameters / confidence, not hundreds of direct PITD points.

### R3 — event-aware compiler
After L7 acceptance:
- continue the full event-aware compiler expansion;
- portamento support required specifically to close the current L7 blocker is
  pulled forward as the minimal discriminating/repair implementation above;
- extend parameterized support for onset/ornament and richer portamento forms;
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

## 14. Definition of Done

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
