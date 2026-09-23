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
- YousaV1.65c / DIFFSINGER rendered with the matching KakaruHayate OpenUtau `dpv2` build.

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

Periodic-expression ownership must be **explicit and causal**, not assumed exclusive.

Default representation:

```text
one periodic gesture
→ one primary owner (native/adaptive vibrato OR PITD periodic component)
→ other lanes retain trend/local non-periodic residual only
```

However, Round F demonstrated that a second periodic component can be **anti-phase compensation** for
renderer response rather than accidental additive duplication. Therefore a secondary periodic
component is allowed only when a controlled real-render A/B proves that it materially compensates a
known response defect. Such compensation must be recorded explicitly as a renderer-correction term,
with rate/depth/phase evidence and a bound render. Never delete or preserve duplicate periodic content
from curve-space reasoning alone.

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
AND candidate_arbitration_gate
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

### 11.6 Bounded execution rounds / context budget

SWE2 has a large but finite context window. Do **not** use one execution round to diagnose,
implement, regenerate all phrases, rerun every A/B, and perform final acceptance at once.

Each executor round must have:
- one primary blocker class;
- at most one tightly-coupled verification step;
- an explicit artifact/output contract;
- an explicit **STOP** condition;
- no authority to begin the next round without reviewer approval.

Default orchestration:

```text
Round A — evidence adjudication
→ STOP
→ reviewer

Round B — ownership / representation decision
→ STOP
→ reviewer

Round C — production regeneration
→ STOP
→ reviewer

Round D — final acceptance only
→ STOP
→ reviewer / human listening
```

Rules:

1. **One round does not inherit permission to execute the next round.**
   A future round may be described in this plan but remains LOCKED until reviewer marks it ACTIVE.

2. **Final acceptance is read-only with respect to generation logic.**
   Round D may run tests/evaluator and emit PASS/FAIL/UNKNOWN/NOT_RUN, but it must not modify:
   - generator/compiler code;
   - QA metric definitions;
   - thresholds/masks;
   - failure classifications;
   - artifact semantics.
   A FAIL in Round D starts a new reviewed repair round; it is not fixed in-place during acceptance.

3. **Do not carry unnecessary history into the active task.**
   The executor should use this active plan, current blocker artifacts, and directly relevant code.
   Historical reasoning remains in Git history and should not be re-expanded unless needed to test a
   specific hypothesis.

4. **STOP means stop.**
   When the round output contract is satisfied, commit the requested evidence and stop even if the
   next action appears obvious. Do not opportunistically regenerate downstream artifacts.

5. **A blocked/unknown result is a valid round completion.**
   The goal is to resolve the assigned question or classify why it cannot yet be resolved, not to
   force the project to the next milestone.


## 12. Current state — R2.1/L7

Verified direction:
- Round F disproved simple additive duplicate-periodic ownership; secondary periodic PITD may act as anti-phase renderer compensation and must be judged from real render;
- active renderer baseline is now YousaV1.65c + matching OpenUtau dpV2;
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

The `92705269` bundle is **not yet authorized for human listening**.
Its clean-worktree provenance is valid and the engineering work is useful,
but reviewer recheck found two acceptance-semantics violations.

1. **pYIN non-detection was incorrectly promoted from weak evidence to
   positive counter-evidence.**

   `diagnostic/adjudicate.third_f0_pyin` already defines the project
   evidence rule: missing / low-confidence third-F0 frames mean weak
   reliability and are never opposition.  The L7 probe nevertheless used
   `disputed_voiced_rate < 0.30` to emit
   `EVIDENCE_ADJUDICATED_ARTIFACT`.

   Therefore the old automatic adjudications for:
   - P2 note8;
   - P3 note9

   are invalid as proof that the FCPE gestures are false.  They return to
   **FAIL_EVIDENCE / UNKNOWN** until positive evidence resolves them.
   pYIN may still *rescue* an FCPE gesture when it positively traces the
   same voiced contour; simple non-detection may not reject one.

   Reviewer patch `3d8bafd0` removes the automatic artifact verdict from
   pYIN non-detection.  Any future automatic artifact adjudication must
   provide an explicit `adjudication_basis=positive_counterevidence`
   backed by committed evidence.

2. **The final evaluator ignored the production arbitration block.**

   Current P2 and P3 manifests still contain:

   ```text
   shape_gate.blocked = true
   ```

   but the `92705269` evaluator never consumed that field and could still
   emit `HUMAN_LISTENING_READY=PASS`.  This violates §8: a later reporting
   layer may not silently override a still-blocked production arbiter.

   Reviewer patch `cea558a6` adds the required
   `candidate_arbitration_gate`:
   - manifest arbitration incomplete → NOT_RUN;
   - `shape_gate.blocked=true` → FAIL;
   - final stage not explicitly `gate_passed=true` → FAIL;
   - only a non-blocked, positively accepted final stage → PASS.

   The evaluator also treats legacy
   `EVIDENCE_ADJUDICATED_ARTIFACT` reports without
   `adjudication_basis=positive_counterevidence` as unresolved.

### Lane-isolation note

The A/B itself was executed correctly, but its P2 explanation is
oversimplified.  The narrow `event` mode has a raw FCPE blocker at note8
**and** an RMVPE blocker at note9; the committed prose saying note8 became
blocking “on both families” is not accurate.

Because note8 is now UNKNOWN again, P2 `full_note` ownership is only
**provisional**.  Do not choose ownership based on a disputed target.
After evidence resolution, re-evaluate P2 A/B with the same evidence
semantics as final acceptance.  A/B must report blocking events for both
extractor families, not only aggregate counts / FCPE names.

### Current execution schedule

#### Round A — COMPLETE: evidence adjudication

Reviewer accepts executor bundle `3f4ccb03 → 4e7b886d`.

Acceptance evidence:
- task scope stayed inside Round A; no ownership, production regeneration or final evaluator run;
- probe generation was from clean `bba542eb` HEAD;
- P2 note8 reproduced:
  - verdict `EVIDENCE_EDGE_UNCERTAIN`;
  - uncertain START edge `[54.660, 54.835]`;
  - reliable core `[54.835, 55.020]`;
  - uncertain fraction `0.486`;
  - energy drop `19.2 dB`;
- P3 note9 reproduced:
  - verdict `EVIDENCE_EDGE_UNCERTAIN`;
  - uncertain END edge `[29.415, 29.520]`;
  - reliable core `[29.250, 29.415]`;
  - uncertain fraction `0.389`;
  - energy drop `25.5 dB`;
- source/base hashes and `worktree_clean_at_generation=true` are present;
- executor reports the focused evidence/contour test set passed (72 tests).

Round-A semantics are now frozen for downstream L7 work:
- uncertain edges stay UNKNOWN and visible;
- they are not reclassified as artifact or as correct pitch;
- absolute event-shape QA may use only the committed reliable core;
- raw-window mismatch remains auditable;
- core distortion still blocks under the unchanged threshold.

**Round A is CLOSED. Do not reopen evidence adjudication unless new positive evidence contradicts the
committed packets.**

#### Round B — COMPLETE: global ownership A/B exposed a real lane split

Reviewer accepts executor bundle `7095c07f → cd396809` as a valid **BLOCKED** result.

Committed evidence:

```text
all full_note:
  FCPE blockers = 0
  RMVPE blockers = 0
  non-portamento FCPE unresolved/extras = 2 / 2
  non-portamento RMVPE unresolved/extras = 1 / 5
  vibrato missing = 0
  out-of-lane med |err| = 7.0 c

all event:
  FCPE blockers = 0
  RMVPE blocker = from_note 9 distortion
  non-portamento FCPE unresolved/extras = 1 / 1
  non-portamento RMVPE unresolved/extras = 1 / 4
  vibrato missing = 0
  out-of-lane med |err| = 8.1 c
```

The trade-off is real:
- narrower ownership preserves more discrete SOURCE event content;
- full-note ownership prevents the later RMVPE shape regression.

Spatial attribution also supports the discrete-lane concern.  The extra
`full_note` ownership tails overlap real SOURCE events:

```text
lane target note 2:
  full-only tail ~52.210–52.370 s
  overlaps SOURCE scoop note2 / start of scoop note3

lane target note 5:
  full-only tail ~53.000–53.220 s
  overlaps SOURCE undershoot note6

lane target note 7:
  full-only tail ~53.940–53.960 s
  overlaps end of SOURCE scoop note7
```

However, the global A/B changes all three applied lanes simultaneously.
It cannot identify which lane causes the downstream RMVPE note9 distortion.
Therefore `full_note` vs `event` is too coarse a control variable.

**Do not unlock Round C from this BLOCKED result.**

#### Round B2 — COMPLETE: exhaustive ownership selected FEF

Reviewer accepts exhaustive executor bundle `92fe97f0 → 6d1356ce`.

All eight real-render ownership vectors over applied target-note lanes
`[2,5,7]` were committed from clean `1e52db03` generation provenance:

```text
FFF  admissible
FFE  FAIL: RMVPE from_note=9 distortion
FEF  admissible
FEE  FAIL: RMVPE from_note=9 distortion
EFF  FAIL: FCPE discrete unresolved worsens + topology missing worsens
EFE  FAIL: RMVPE from_note=9 distortion
EEF  FAIL: discrete extras/topology worsen
EEE  FAIL: RMVPE from_note=9 distortion
```

The only admissible vectors are FFF and FEF.

Deterministic selection chooses **FEF** because it has the shorter total
ownership span:

```text
target note 2 -> full_note
target note 5 -> event
target note 7 -> full_note
```

Evidence for selected FEF:
- FCPE blockers = 0;
- RMVPE blockers = 0;
- vibrato missing = 0;
- FCPE discrete lanes improve from FFF `unresolved/extras 2/2 -> 1/1`;
- RMVPE discrete lanes are non-worse `1/5 -> 1/5`;
- out-of-lane median |err| = 8.2 c, within FFF 7.0 c + 5 c;
- out-of-lane topology:
  - missing 12 == FFF 12;
  - extra 1 < FFF 2;
  - sequence edit distance 11 == FFF 11;
- total owned duration 1.24 s vs FFF 1.46 s;
- Round-A P2 source-edge evidence SHA256 `34cb9585...` is bound;
- selected USTX/WAV hashes are committed in the exhaustive report.

The earlier single-toggle conclusion that FFF was the only valid ownership
was correctly superseded by the exhaustive search.

**Round B2 is CLOSED.  P2 production ownership is frozen as FEF unless new
evidence invalidates the committed exhaustive packet.**

Reviewer production wiring:
- `4485984f`: production phrase gate gains reviewer-approved ownership presets;
- `fb1c660c`: presets are fixed as:
  - P1_sustain = `event`;
  - P2_slides = `{2:"full_note", 5:"event", 7:"full_note"}`;
  - P3_vibrato = `event`.
  Existing explicit experimental `full_note/event` CLI modes remain available.

#### Round C — COMPLETE: P2 accepted, P3 exposes fallback-arbitration defect

Reviewer accepts executor bundle `d4d8fbc0 → 9066e755` as a valid Round-C result.

### P2_slides — production closure PASS

Fresh clean-head production regeneration under reviewer-approved ownership:

```text
requested ownership = accepted
resolved ownership  = {2: full_note, 5: event, 7: full_note}
final candidate     = C3v2
shape_gate.blocked  = false
```

Evidence:
- v1 PASS;
- v2 PASS and selected;
- FCPE/RMVPE absolute event-shape blockers = 0;
- Round-A P2 reliable-core evidence is bound;
- per-lane FEF ownership is recorded in provenance;
- generator/QA head = clean `0e95f40d`.

P2 is CLOSED for this L7 cycle unless a later read-only acceptance check finds an independent
artifact/provenance inconsistency.

### P3_vibrato — expression/evidence issue resolved; arbitration semantics still wrong

Fresh production regeneration under:

```text
requested ownership = accepted
resolved ownership  = event
```

now shows:

```text
v1:
  absolute event-shape = PASS
  violations           = []
  gate_passed          = true

v2:
  absolute event-shape = PASS
  topology regression  = matched_turns / missing_turns / extra_turns

v3:
  absolute event-shape = PASS
  topology regression  = matched_turns / missing_turns
```

The previous P3 note9 blocker is resolved correctly:
- note9 = `source_edge_uncertain`;
- reliable core = `[29.250, 29.415]`;
- raw window remains auditable;
- FCPE/RMVPE event-shape families are non-blocking.

The remaining `shape_gate.blocked=true` is therefore **not evidence that v1 is bad**.
It is caused by the current arbiter contract in `run_shape_gate`:

```text
v2 FAIL
→ try bounded rollback v3
→ v3 FAIL
→ retain v1
→ unconditionally blocked = true
```

That rule was necessary when v1 itself failed the required absolute event-shape gate.
It is too strict once v1 is a verified clean baseline.

A closed-loop correction is optional. If both correction attempts regress relative topology,
the safe behavior is to retain a v1 that already satisfies all required absolute gates.

#### Round C2 — COMPLETE / REVIEWER ACCEPTED

Reviewer decision: **ACCEPT**. Round C/C2 is closed and must not be reopened during final acceptance.

Accepted implementation/evidence:
- fallback arbitration fix: `97da2b5`;
- clean P3 regeneration/evidence: `91d72f8`;
- P3 final candidate = `C3/v1`;
- `shape_gate.blocked=false`;
- `fallback_reason=verified_v1_after_regressive_improvements`;
- v1 absolute gate remains PASS with zero blocking event-shape issues;
- v2/v3 remain recorded as regressive attempts rather than being threshold-relaxed into PASS;
- candidate USTX/WAV hashes and generation-head provenance are recorded.

Interpretation:
- this closes an **arbitration/state-machine defect**, not a claim that v2/v3 improved P3;
- the verified v1 baseline is retained because both optional correction attempts regress;
- do not tune P3 further merely because v2/v3 failed;
- do not rename/refactor fallback semantics during Round D. Any cosmetic/generalization cleanup belongs to a later reviewed maintenance round.

Round C2 is now immutable for purposes of L7 final acceptance.

#### Round D — COMPLETE: frozen machine acceptance passed

Round D executed from clean `4e83c57` and is closed.

Committed evidence:
- full pytest: **512 passed**;
- frozen 10-term `l7_acceptance_eval.py`: all required terms PASS;
- `blocking_issue_count=0`;
- `unknown_required_gate_count=0`;
- machine verdict: `HUMAN_LISTENING_READY=PASS`;
- evaluation-only scope was respected: no generation, QA, threshold, gate, ownership, or candidate semantics changed.

This machine PASS authorized human listening only. It did **not** prove perceptual quality.

#### L7-E human listening — COMPLETE: P1 PASS / P2 FAIL / P3 FAIL

Human listening over the assembled accepted-candidate OpenUtau project produced:

```text
P1_sustain  = PASS
P2_slides   = FAIL
P3_vibrato  = FAIL
```

Committed post-listening evidence (`724ffc4`) demonstrates metric blind spots rather than a reason to override the human verdict.

Observed evidence:
- **P3** accepted C3/v1 has a ~30 ms render pitch-glitch cluster near 29.26–29.28 s,
  including >300 c local deviations and detrended F0 RMS 62.5 c; rejected v2/v3 are materially
  smoother at 12.7 / 15.7 c. Existing topology/event-shape arbitration did not measure final-render
  stability strongly enough.
- **P2** accepted C3v2 has major gesture-range compression on specific notes
  (e.g. 560 c → 89 c and 287 c → 41 c), opposing note-centre offsets, and a ~140 ms render
  phonation dropout where SOURCE is voiced. Existing gates did not directly measure gesture-range
  fidelity / phonation continuity.
- **P1** remains the positive listening control.

The human FAIL is authoritative for this L7 listening round. Do not make P2/P3 PASS by reinterpreting
the old machine metrics.

#### Environment migration — COMPLETE: YousaV1.65c + OpenUtau dpV2

Environment commit `8176ceb` migrates execution to:
- singer: `YousaV1.65c`;
- matching KakaruHayate OpenUtau `dpv2` build containing group-aware duration-model support;
- rebuilt bridge against that OpenUtau.Core;
- full pytest remains 512 PASS.

The new duration model/editor pair changes the renderer under test. Therefore pre-migration P1/P2/P3
renders are no longer sufficient evidence for deciding which remaining defects belong to the
expression compiler versus the duration/render stack.

Legacy `YousaV1.65b -> YousaV1.65c` junction compatibility is allowed only for migration smoke tests.
New acceptance/re-baseline artifacts must identify `YousaV1.65c` explicitly in USTX and provenance.

Before producing new renderer evidence, configuration must resolve unambiguously to the dpV2 install.
If any fallback path still points to the old OpenUtau install, classify that as an environment
precondition defect and fix only that path before the re-baseline; do not change expression logic.

#### Round E — COMPLETE / REVIEWER ACCEPTED: 1.65c + dpV2 re-baseline

Reviewer accepts executor bundle `58bc93e → ac08257 → 4bbf37b` as the new renderer baseline.

Round-E contract was respected:
- P1/P2/P3 accepted expression states were copied with only `tracks[0].singer`
  changed to `YousaV1.65c`;
- recursive structural comparison reports zero unexpected semantic differences;
- all three were rendered through the matching dpV2 bridge;
- evidence reused the existing post-listening blind-spot measurements rather than redefining them;
- generation provenance is bound to clean `ac08257`;
- OpenUtau executable/Core/bridge hashes and 46 voicebank material hashes, including
  `dsdur/0923_dpv2_nogru.dur.onnx`, are committed.

Human listening of the new 1.65c project establishes:

```text
P1_sustain:
  perceptually acceptable / control remains stable

P3_vibrato:
  previous major discomfort is gone
  old 29.26–29.28 s glitch is no longer a compiler blocker
  remaining issues are local performance-shape defects:
    - “涩” onset sounds slightly front-pushed / juvenile
    - final “根” vibrato sounds constant-rate/constant-depth and does not decay naturally

P2_slides:
  hard FAIL
  “我的笨” is piercing / excessively shaky
```

Renderer attribution:
- P3 >300 c glitch cluster: `3 → 0`;
- P3 detrended F0 RMS: `62.5 c → 12.0 c`;
- identical P3/v1 expression now renders cleanly at that old glitch location;
- therefore the old 29.26–29.28 s failure is **renderer-attributable** and must not be repaired in the
  compiler.

P2 persistent evidence on the new renderer:
- note0 gesture range ratio remains severely compressed: `0.16 → 0.14`;
- note10 remains severely compressed: `0.14 → 0.17`;
- note5/note6 opposing offsets persist at approximately `+56 c / -24 c`;
- old 54.70–54.83 s fully-voiced dropout disappears under 1.65c/dpV2, so that old dropout is not a
  compiler repair target;
- new render-energy collapses remain renderer/performance evidence and must not be assigned to the
  compiler without a discriminating experiment.

P3 local parameter evidence:
- “涩” = P3 note3, start near 26.40 s;
- its note-local `pitch.data` is flat, but surrounding PITD contains a sharp onset excursion
  approximately `+103 c → -102 c → -205 c`;
- final “根” native vibrato currently uses approximately:
  `length=100%`, `period=148.6 ms`, `depth=70.3 c`, `out=3.5%`;
- this representation is effectively constant-rate/constant-depth with almost no release decay.

P2 “我的笨” mapping:
- phrase span begins around note8;
- final “笨” native vibrato currently uses approximately:
  `length=98.3%`, `period=141.4 ms`, `depth=74.2 c`, `out=0%`;
- the same note also carries substantial oscillatory PITD (roughly `-38 c … +95 c`), creating a
  credible duplicate-modulation hypothesis.

**Round E is CLOSED.** Old 1.65b renderer artifacts remain historical evidence only. Current repair
work must use YousaV1.65c + matching dpV2 OpenUtau.

#### Round F — COMPLETE / REVIEWER ACCEPTED: duplicate ownership hypothesis falsified

Reviewer accepts executor bundle `fc33674 → 357ed3d → eb4fb00 → acb2e9d` as a valid causal
discrimination result.

Verdict:

```text
FAIL_STRATEGY
```

What was proved:
- P2 note11 / “笨” has genuine overlapping periodic representations:
  - native vibrato: ~7.07 Hz / 74.2 c;
  - PITD periodic component: ~6.87 Hz / 97.1 c;
- but the two components are **not additively causing the shake**;
- removing the periodic PITD made the rendered modulation much worse:
  - baseline A periodic depth = 179.8 c;
  - ownership-removal B = 318.0 c;
  - SOURCE = 157.1 c;
- therefore the PITD component is anti-phase compensation for an over-deep native-vibrato response.

This falsifies the earlier simple rule “duplicate periodic ownership is itself the material cause”.
The architecture rule is revised accordingly: periodic ownership must be explicit and causal, while
evidence-backed compensation is permitted.

Capability evidence:
- SOURCE note11 modulation envelope decays roughly `196 c → 121 c p2p`;
- current native vibrato is fixed-rate/fixed-depth with `out=0`;
- Level-1 parameters alone do not obviously explain the SOURCE envelope;
- however baseline A's aggregate periodic depth is already relatively near SOURCE, so this evidence
  does **not** prove that Level-2 vibrato is the main cause of the user's “刺耳、颤抖” complaint.

Important unresolved fact:
- human P2 FAIL remains;
- the dominant perceptual defect may instead lie in:
  - the pre-vibrato / non-vibrato portion around ~54.85–55.55 s;
  - cycle waveform/phase rather than aggregate rate/depth;
  - onset/transition geometry;
  - phonation/timbre/energy rather than F0 trajectory alone.

No Round-F candidate is accepted. Variant B is diagnostic evidence only.

#### Round F2 — ACTIVE: localize the P2 perceptual failure before further repair

**Single goal:** determine which measurable subsystem actually corresponds to the human complaint
“我的笨完全不行，刺耳，颤抖” on the current 1.65c/dpV2 baseline.

This is an **evidence/localization round**, not a production repair round.

Do not assume:
- Level-2 adaptive vibrato is the answer;
- duplicate periodic ownership is bad;
- F0 alone explains “刺耳”;
- a lower pointwise/source error necessarily sounds better.

### Frozen target and segmentation

Freeze the current 1.65c P2 baseline. Analyze notes 8–11 / approximately 54.35–56.71 s.

At minimum split evidence into:

```text
S1: note8 / “我” onset + transition region
S2: note9–10 / “的” + continuation, pre-vibrato region
S3: note11 / “笨” vibrato-owned tail
```

Exact boundaries must come from the committed score/phoneme/render evidence rather than the prose
labels above.

### Required diagnostic families

For SOURCE and baseline render, measure each segment separately.

1. **F0 trajectory geometry**
   - isolated spike magnitude/duration;
   - local slope and acceleration/jerk;
   - reversal density and reversal timing;
   - overshoot / settling structure;
   - note-centre offset;
   - local gesture-range ratio.

2. **Periodic / vibrato structure**
   - instantaneous/cycle rate;
   - cycle depth;
   - rate envelope;
   - depth envelope;
   - cycle-to-cycle variation;
   - phase / zero-crossing alignment where observable;
   - waveform-shape residual after fitting the dominant periodic component.

3. **Phonation / render quality**
   - voiced continuity;
   - local energy envelope / collapses;
   - harmonic-periodicity evidence (existing ACF metric or a better committed equivalent);
   - spectral roughness/flatness already available in the repository;
   - do not infer a pitch defect when F0 is plausible but acoustic quality is abnormal.

4. **Singing-motion grammar, diagnostic only**
   Classify local motion where evidence permits into:

   ```text
   preparation
   transition
   overshoot / undershoot
   settling
   sustain / fine fluctuation
   vibrato
   release
   unknown
   ```

   Flag geometrically implausible patterns (spike, unsupported rapid reversal, unstructured zig-zag,
   abrupt periodic start/stop), but **do not create global PASS/FAIL thresholds in Round F2**.

### Controls / anti-overfit requirement

Compare P2 diagnostics against committed known controls:
- P1 current positive listening control;
- old 1.65b P3 29.26–29.28 s glitch as a known hard abnormal example;
- current 1.65c P3 as a case where that hard abnormality disappeared.

The purpose is to verify that proposed features separate at least obvious normal vs obvious abnormal
behaviour before using them to explain P2.

Do not claim a feature explains P2 merely because P2 has a large value. The feature must have a
causal or comparative interpretation.

### Optional discriminating A/B

Only if the diagnostics identify one concrete F0-localized suspect interval, one minimal A/B is
allowed:
- change only that suspect component;
- preserve the rest of P2 byte-semantically;
- real-render both variants;
- produce a P2-only listening artifact.

Do not perform more than one candidate-changing A/B in this round.

If diagnostics instead indicate that F0 motion is broadly plausible while acoustic
phonation/timbre is abnormal, do **not** modify pitch curves; record the route as render/phonation.

### Round-F2 routing

End the round with exactly one primary classification:

```text
F0_LOCAL_DEFECT
  a specific onset/transition/periodic trajectory defect corresponds to the human-fail region
  → authorize one later bounded expression repair

VIBRATO_CAPABILITY
  fixed Level-1 vibrato cannot reproduce the verified SOURCE cycle/rate/depth envelope and the
  mismatch corresponds to the perceptual failure
  → authorize a separate Level-2 adaptive-vibrato implementation round

PHONATION_RENDER_DEFECT
  F0 trajectory is plausible enough, but render acoustic/phonation evidence is abnormal
  → leave pitch compiler unchanged and investigate render/voice parameters

MIXED_DEFECT
  independently supported pitch and acoustic defects coexist
  → split them into separate later rounds

FAIL_EVIDENCE
  available evidence cannot localize the complaint reliably
  → STOP; improve observability, do not tune
```

Commit the diagnostic packet and **STOP**. P1 and P3 remain frozen.

#### Round G — LOCKED: P3 local polish

Do not execute until Round F is reviewed/closed.

P3 is no longer a hard L7 renderer-stability blocker. Remaining work is local and must be split into
two discriminating subproblems:

1. **“涩” onset (~26.40 s)**  
   Test whether the front-pushed / juvenile onset comes from the sharp local PITD excursion or from
   1.65c phoneme/timbre timing. First A/B only the onset PITD support; do not alter phonemes and pitch
   simultaneously.

2. **final “根” vibrato**  
   Current fixed `period/depth` with `out≈3.5%` does not match the heard decay. Measure SOURCE
   cycle-by-cycle `periods_ms[]` and `cycle_depths[]` first. If constant Level-1 vibrato cannot
   reproduce the verified rate/depth envelope, classify `FAIL_CAPABILITY` and escalate to Level-2
   adaptive vibrato with low-DOF rate/depth envelopes and explicit tail decay.

P3's old 29.26–29.28 s glitch is permanently excluded from compiler-repair scope unless new positive
evidence contradicts Round E.

#### Round H — LOCKED: human singing plausibility gate

Do not execute until the current P2/P3 localized defects have produced enough positive/negative
examples for calibration.

**Goal:** add a source-independent first-pass judge that asks whether a rendered pitch trajectory is
plausible as human singing before asking how closely it matches the target singer.

This is a **general system capability**, not a special-case repair for P2/P3.

The gate must model structured singing motion rather than “smoothness” alone. Candidate feature
families include:
- preparation / transition / overshoot / settling structure;
- isolated spikes;
- unsupported rapid reversals / zig-zag density;
- local slope / acceleration / jerk;
- sustain fine fluctuation;
- vibrato rate/depth and their envelopes;
- cycle-to-cycle rate/depth variation;
- vibrato onset/release naturalness;
- voiced continuity.

Known replay cases for initial validation:
- P1 current render: positive control;
- old P3 29.26–29.28 s `+423 / -1210 / +611 c` cluster: must be a hard abnormal case;
- P3 “涩” onset: should be at least suspicious/context-dependent rather than blindly accepted;
- P3 final “根” constant-feeling vibrato: should expose low naturalness / envelope mismatch if the
  rendered cycles are indeed over-regular;
- P2 “我的笨”: must be evaluated with both pitch-motion and phonation/render evidence; a pure F0
  plausibility score is not allowed to claim coverage if it misses the human FAIL.

Do **not** begin with arbitrary universal constants such as `rate > 7 Hz = FAIL`.
Initial thresholds/prior ranges must come from real-singing data and/or robust control distributions.
Prefer conditional distributions by motion state and note context.

The eventual acceptance architecture should distinguish:

```text
human_pitch_plausibility
source_expression_fidelity
phonation_render_plausibility
```

A candidate must not be made acceptable merely because source-similarity is numerically high while
its local motion is implausible.

Round H must be developed and calibrated separately from candidate repair; metric construction and
candidate tuning must not occur in the same execution round.

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
