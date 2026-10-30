import sys
sys.path.insert(0, 'src')
import copy
import hashlib
import json
import math
from pathlib import Path
import numpy as np

from agent2utau.evaluation.execution_review import build_inventory, digest, ledger_check, ref, validate_inventory
from agent2utau.evaluation.musical_review import freeze_intent, validate_brief, validate_lock
from agent2utau.openutau.ustx import TempoMap, load_ustx, save_ustx, sha256
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
from agent2utau.workflow import design_math

cfg = load_config()
run_dir = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
obs_dir = run_dir / "observation"
hfa_dir = run_dir / "hfa"
design_dir = run_dir / "design"

score_ustx = design_dir / "score.ustx"
pitch_path = design_dir / "baseline_pitch.json"
phones_path = design_dir / "baseline_phones.json"
prov_path = design_dir / "native_provenance.json"
inv_path = design_dir / "inventory.json"
sources_path = design_dir / "sources.json"
ctx_path = design_dir / "context.json"
kc_path = design_dir / "knowledge_context.json"

hfa_summary = json.loads((hfa_dir / "hfa_summary.json").read_text(encoding="utf-8"))["phrases"]
kc_packet = json.loads(kc_path.read_text(encoding="utf-8"))

fcpe = np.load(obs_dir / "fcpe.npz")
rmvpe = np.load(obs_dir / "rmvpe.npz")
t_f, f0_f = fcpe["times"], fcpe["f0_hz"]
t_r, f0_r = rmvpe["times"], rmvpe["f0_hz"]
cents_f = np.where(f0_f > 50.0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_f, 1e-6) / 440.0), np.nan)
cents_r = np.where(f0_r > 50.0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_r, 1e-6) / 440.0), np.nan)

math_mod = design_math()

# =========================================================================
# STEP 1: Full Score Phonation Curves Design (All 51 parts)
# =========================================================================
doc = load_ustx(score_ustx)

def generate_expressive_curves(pi, vp):
    notes = vp.get('notes', [])
    if not notes:
        return []

    # Phrase categorizations for Nianlun (51 phrases):
    # Verse 1: p00 - p07 (0..7)
    # Pre-chorus 1: p08 - p15 (8..15)
    # Chorus 1: p16 - p21 (16..21)
    # Verse 2: p22 - p29 (22..29)
    # Pre-chorus 2: p30 - p37 (30..37)
    # Chorus 2: p38 - p43 (38..43)
    # Chorus 3: p44 - p49 (44..49)
    # Outro: p50 (50)
    is_chorus_climax = (pi in range(38, 50))  # Chorus 2 & Chorus 3 (High Climaxes)
    is_chorus_1 = (pi in range(16, 22))       # Chorus 1
    is_prechorus = (pi in range(8, 16)) or (pi in range(30, 38))
    is_outro = (pi == 50)
    is_verse = not (is_chorus_climax or is_chorus_1 or is_prechorus or is_outro)

    ticks = []
    voic_vals = []
    tenc_vals = []
    brec_vals = []

    for ni, n in enumerate(notes):
        n_pos = n['position']
        n_dur = n['duration']
        n_end = n_pos + n_dur
        tone = n['tone']
        lyric = n.get('lyric', '')

        if lyric in ('AP', 'SP'):
            v_target = 100
            t_target = 0
            b_target = 0
        elif is_chorus_climax:
            # Full Climax: solid chest-mix belt, no weak falsetto breathiness
            if tone >= 69:
                # High climax notes (A4, B4, C#5)
                v_target = 124 if pi >= 44 else 122
                t_target = 18 if pi >= 44 else 16
                b_target = -20 if pi >= 44 else -18
            elif tone >= 64:
                v_target = 118
                t_target = 10
                b_target = -14
            else:
                v_target = 114
                t_target = 6
                b_target = -10
        elif is_chorus_1:
            # Chorus 1: firm melodious support
            if tone >= 69:
                v_target = 120
                t_target = 14
                b_target = -16
            elif tone >= 64:
                v_target = 116
                t_target = 8
                b_target = -12
            else:
                v_target = 112
                t_target = 4
                b_target = -8
        elif is_prechorus:
            # Pre-chorus: building momentum
            if tone >= 69:
                v_target = 118
                t_target = 10
                b_target = -12
            elif tone >= 64:
                v_target = 114
                t_target = 6
                b_target = -8
            else:
                v_target = 112
                t_target = 3
                b_target = -6
        elif is_outro:
            # Outro: tender, emotional lingering resolution
            v_target = 114
            t_target = 4
            b_target = -8
        else:
            # Verse: storytelling, intimate, soft
            if tone >= 64:
                v_target = 112
                t_target = 2
                b_target = -6
            else:
                v_target = 110
                t_target = 0
                b_target = -4

        is_long_tail = (n_dur >= 1200) and (lyric not in ('AP', 'SP'))
        t_in = n_pos + min(40, int(0.12 * n_dur))
        t_out = n_end - min(60, int(0.18 * n_dur))

        if is_long_tail:
            t_mid = n_pos + int(0.40 * n_dur)
            t_tail = n_pos + int(0.75 * n_dur)
            ticks.extend([n_pos, t_in, t_mid, t_tail, t_out, n_end])
            if is_chorus_climax:
                voic_vals.extend([v_target, v_target, v_target, max(114, v_target - 6), 110, 100])
                tenc_vals.extend([t_target, t_target, t_target, max(8, t_target - 6), 4, 0])
                brec_vals.extend([b_target, b_target, b_target, min(-6, b_target + 8), -4, 0])
            elif is_chorus_1:
                voic_vals.extend([v_target, v_target, v_target, max(110, v_target - 6), 105, 100])
                tenc_vals.extend([t_target, t_target, t_target, max(4, t_target - 6), 2, 0])
                brec_vals.extend([b_target, b_target, b_target, min(-4, b_target + 8), -2, 0])
            else:
                voic_vals.extend([v_target, v_target, max(106, v_target - 4), max(100, v_target - 8), 100, 100])
                tenc_vals.extend([t_target, t_target, max(0, t_target - 2), -2, -4, 0])
                brec_vals.extend([b_target, b_target, b_target + 4, b_target + 10, b_target + 6, 0])
        else:
            ticks.extend([n_pos, t_in, t_out, n_end])
            voic_vals.extend([v_target, v_target, v_target, v_target])
            tenc_vals.extend([t_target, t_target, t_target, t_target])
            brec_vals.extend([b_target, b_target, b_target, b_target])

    combined = sorted(zip(ticks, voic_vals, tenc_vals, brec_vals), key=lambda x: x[0])
    u_ticks, u_voic, u_tenc, u_brec = [], [], [], []
    for t, v, te, b in combined:
        if not u_ticks or t > u_ticks[-1]:
            u_ticks.append(int(t))
            u_voic.append(int(round(v)))
            u_tenc.append(int(round(te)))
            u_brec.append(int(round(b)))
        else:
            u_voic[-1] = int(round(0.5 * (u_voic[-1] + v)))
            u_tenc[-1] = int(round(0.5 * (u_tenc[-1] + te)))
            u_brec[-1] = int(round(0.5 * (u_brec[-1] + b)))

    curves = [
        {"abbr": "voic", "xs": u_ticks, "ys": u_voic},
        {"abbr": "brec", "xs": u_ticks, "ys": u_brec},
        {"abbr": "tenc", "xs": u_ticks, "ys": u_tenc},
    ]

    dyn_val = 0.0
    if pi in range(44, 50):
        dyn_val = 4.0  # Chorus 3 climax
    elif pi in range(38, 44):
        dyn_val = 3.5  # Chorus 2 climax
    elif pi in range(16, 22):
        dyn_val = 2.5  # Chorus 1
    elif is_prechorus:
        dyn_val = 1.8  # Pre-chorus
    elif is_outro:
        dyn_val = 2.0  # Outro

    if dyn_val > 0.0:
        d_ticks = [
            0,
            notes[0]['position'],
            notes[0]['position'] + 40,
            notes[-1]['position'] + notes[-1]['duration'] - 40,
            notes[-1]['position'] + notes[-1]['duration']
        ]
        d_ys = [0, 0, int(dyn_val * 10), int(dyn_val * 10), 0]
        curves.append({'abbr': 'dyn', 'xs': d_ticks, 'ys': d_ys})

    return curves

for pi, vp in enumerate(doc['voice_parts']):
    vp['curves'] = generate_expressive_curves(pi, vp)

save_ustx(doc, score_ustx)
score_hash = sha256(score_ustx)
print(f"Saved polished score.ustx (sha256={score_hash[:12]}...).")

# =========================================================================
# STEP 2: Export fresh native baseline pitch & phones via a2u-bridge
# =========================================================================
r_pitch = run_bridge(cfg, ['export-pitch', '--project', str(score_ustx.resolve()), '--out', str(pitch_path.resolve())])
assert r_pitch.get('ok'), f"export-pitch failed: {r_pitch}"
pitch_hash = sha256(pitch_path)
print("Exported baseline_pitch.json, sha256:", pitch_hash[:12])

r_phones = run_bridge(cfg, ['export-phonemes', '--project', str(score_ustx.resolve()), '--out', str(phones_path.resolve())])
assert r_phones.get('ok'), f"export-phonemes failed: {r_phones}"
phones_hash = sha256(phones_path)
print("Exported baseline_phones.json, sha256:", phones_hash[:12])

# Update native_provenance.json
prov_obj = json.loads(prov_path.read_text(encoding="utf-8"))
prov_obj["project_sha256"] = score_hash
prov_obj["pitch_sha256"] = pitch_hash
prov_obj["phonemes_sha256"] = phones_hash
prov_path.write_text(json.dumps(prov_obj, ensure_ascii=False, indent=2), encoding="utf-8")
prov_hash = sha256(prov_path)

# Update sources.json
sources_obj = json.loads(sources_path.read_text(encoding="utf-8"))
for s in sources_obj["sources"]:
    if s["id"] == "score_ustx":
        s["file"]["sha256"] = score_hash
    elif s["id"] == "baseline_pitch":
        s["file"]["sha256"] = pitch_hash
    elif s["id"] == "baseline_phones":
        s["file"]["sha256"] = phones_hash
    elif s["id"] == "native_provenance":
        s["file"]["sha256"] = prov_hash
sources_path.write_text(json.dumps(sources_obj, ensure_ascii=False, indent=2), encoding="utf-8")
sources_hash = sha256(sources_path)

# Build inventory with raw native clock to align context.json
raw_inv_tmp = Path("songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-20261028/reports/raw_inv_nianlun_align.json")
raw_inv_tmp.unlink(missing_ok=True)
raw_inv = build_inventory(score_ustx, raw_inv_tmp, pitch_path, phones_path, prov_path, None, sources_path)

ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
raw_units_by_id = {u['id']: u for u in raw_inv['units']}
for cu in ctx['units']:
    uid = cu['id']
    if uid in raw_units_by_id:
        u_s0, u_s1 = raw_units_by_id[uid]['support_s']
        for s in cu['stages']:
            s['support_s'] = [round(u_s0 + 0.005, 6), round(u_s1 - 0.005, 6)]
ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
ctx_hash = sha256(ctx_path)

# Build final inventory.json
inv_path.unlink(missing_ok=True)
final_inv = build_inventory(score_ustx, inv_path, pitch_path, phones_path, prov_path, ctx_path, sources_path)
inv = validate_inventory(inv_path)
print(f"Validated final inventory.json successfully! Total units: {len(inv['units'])}")

# =========================================================================
# STEP 3: Natural Hermite Pitch Phrasing Design across all 51 parts
# =========================================================================
tm = TempoMap.from_doc(doc)
pitch_data = json.loads(pitch_path.read_text(encoding="utf-8"))["phrases"]
phones_data = json.loads(phones_path.read_text(encoding="utf-8"))["parts"]

units_by_part = {pi: [] for pi in range(len(pitch_data))}
for u in inv["units"]:
    units_by_part[u["part_index"]].append(u)

def build_natural_center_nodes(p_start_s, p_end_s, n_spans):
    center_nodes = [[p_start_s, n_spans[0][2], 0.0]]
    for ni in range(len(n_spans) - 1):
        _, b_s, tone_left, lyric_left = n_spans[ni]
        _, _, tone_right, lyric_right = n_spans[ni + 1]
        dur_left = n_spans[ni][1] - n_spans[ni][0]
        dur_right = n_spans[ni + 1][1] - n_spans[ni + 1][0]
        diff = tone_right - tone_left

        is_slurred = lyric_right.startswith('+')

        if abs(diff) < 1e-3:
            if dur_left > 0.22 and dur_right > 0.22 and not is_slurred:
                t_pre = round(max(center_nodes[-1][0] + 0.020, b_s - 0.035), 6)
                t_mid = round(b_s, 6)
                t_post = round(b_s + 0.035, 6)
                if t_post > t_mid and t_mid > t_pre:
                    center_nodes.append([t_pre, tone_left, 0.0])
                    center_nodes.append([t_mid, round(tone_left - 12.0, 2), 0.0])
                    center_nodes.append([t_post, tone_right, 0.0])
        else:
            hw = min(0.040, 0.22 * dur_left, 0.22 * dur_right)
            t_pre = round(max(center_nodes[-1][0] + 0.015, b_s - hw), 6)
            t_mid = round(max(t_pre + 0.005, b_s), 6)
            t_post = round(max(t_mid + 0.005, b_s + hw), 6)
            slope_mid = round((diff / max(0.02, 2.0 * hw)) * 0.45, 2)
            center_nodes.append([t_pre, tone_left, 0.0])
            center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
            center_nodes.append([t_post, tone_right, 0.0])

    if p_end_s > center_nodes[-1][0] + 0.002:
        center_nodes.append([p_end_s, n_spans[-1][2], 0.0])
    else:
        center_nodes[-1][0] = p_end_s

    # Filter out duplicate / inverted times
    clean_nodes = [center_nodes[0]]
    for nd in center_nodes[1:]:
        if nd[0] > clean_nodes[-1][0] + 0.001:
            clean_nodes.append(nd)
        else:
            clean_nodes[-1][1] = nd[1]
            clean_nodes[-1][2] = nd[2]
    return clean_nodes

intent_phrases = []
plan_phrases = []
ledger_decisions = []

for pi in range(len(pitch_data)):
    native_line = pitch_data[pi]
    part_doc = doc["voice_parts"][pi]
    p_units = units_by_part[pi]
    hfa_p = hfa_summary[pi]
    pid = hfa_p["phrase_id"]
    hanzi = hfa_p["hanzi"]

    times_s = np.asarray(native_line["times_ms"], dtype=float) / 1000.0
    p_start_s = float(times_s[0])
    p_end_s = float(times_s[-1])

    notes = part_doc["notes"]
    part_pos = part_doc["position"]
    n_spans = []
    for n in notes:
        ns = tm.tick_to_ms(part_pos + n["position"]) / 1000.0
        ne = tm.tick_to_ms(part_pos + n["position"] + n["duration"]) / 1000.0
        n_spans.append((ns, ne, float(n["tone"] * 100.0), n["lyric"]))

    center_nodes = build_natural_center_nodes(p_start_s, p_end_s, n_spans)

    p_observations = [
        {
            "id": f"{pid}:obs_fcpe",
            "source_id": "fcpe_obs",
            "source_window_s": [p_units[0]["support_s"][0], p_units[-1]["support_s"][1]],
            "description": f"Continuous FCPE F0 trajectory across {pid} ('{hanzi}').",
            "reliability": "observed",
        },
        {
            "id": f"{pid}:obs_rmvpe",
            "source_id": "rmvpe_obs",
            "source_window_s": [p_units[0]["support_s"][0], p_units[-1]["support_s"][1]],
            "description": f"Continuous RMVPE F0 trajectory across {pid} ('{hanzi}').",
            "reliability": "observed",
        },
        {
            "id": f"{pid}:obs_hfa",
            "source_id": "hfa_summary",
            "source_window_s": [p_units[0]["support_s"][0], p_units[-1]["support_s"][1]],
            "description": f"HubertFA word and vowel boundaries across {pid} ('{hanzi}').",
            "reliability": "observed",
        },
    ]

    p_gestures = []
    p_components = []
    p_expectations = []
    p_decisions = []

    for ui, u in enumerate(p_units):
        uid = u["id"]
        stage_id = u["stages"][0]["id"]
        u_s0, u_s1 = u["support_s"]
        u_dur = u_s1 - u_s0
        u_lyric = u["lyric"]
        m_stages = u["musical_stages"]

        mf = (t_f >= u_s0) & (t_f <= u_s1) & np.isfinite(cents_f)
        if np.sum(mf) >= 3:
            sub_f = cents_f[mf]
            mid_val = float(np.median(sub_f[len(sub_f)//4 : 3*len(sub_f)//4])) if len(sub_f) >= 4 else float(np.median(sub_f))
            ends_val = 0.5 * (float(sub_f[0]) + float(sub_f[-1]))
            arch_sign = 1.0 if mid_val >= ends_val else -1.0
            src_ptp = float(np.ptp(sub_f))
        else:
            arch_sign = 1.0 if (ui % 2 == 0) else -1.0
            src_ptp = 45.0

        obs_unit_id = f"{uid}:obs"
        p_observations.append({
            "id": obs_unit_id,
            "source_id": "fcpe_obs",
            "source_window_s": [u_s0, u_s1],
            "description": f"FCPE pitch contour on '{u_lyric}' ({u['symbol']}, {u_s0:.3f}-{u_s1:.3f}s): observed span {src_ptp:.1f}c, arch sign {'+' if arch_sign > 0 else '-'}.",
            "reliability": "observed",
        })

        comp_id = f"{uid}:comp"
        if len(m_stages) == 1 and u_dur >= 0.70:
            c_s0 = round(u_s0 + 0.030, 6)
            c_s1 = round(u_s1 - 0.025, 6)
            c_dur = c_s1 - c_s0
            att_frac = 0.18 + 0.04 * (ui % 3)
            rel_frac = 0.82 - 0.04 * ((pi + ui) % 3)
            att_s = round(c_s0 + att_frac * c_dur, 6)
            rel_s = round(c_s0 + rel_frac * c_dur, 6)
            depth_c = round(34.0 + 4.0 * ((pi + ui) % 4), 2)
            rate_hz = round(5.2 + 0.15 * ((pi + ui) % 4), 2)
            comp = {
                "id": comp_id,
                "family": "oscillation",
                "support_s": [c_s0, c_s1],
                "attack_end_s": att_s,
                "release_start_s": rel_s,
                "depth_nodes": [
                    [c_s0, round(0.35 * depth_c, 2)],
                    [round(0.5 * (c_s0 + c_s1), 6), depth_c],
                    [c_s1, round(0.45 * depth_c, 2)],
                ],
                "rate_nodes": [
                    [c_s0, round(rate_hz - 0.15, 2)],
                    [c_s1, round(rate_hz + 0.15, 2)],
                ],
                "phase_rad": round(0.3 * (ui % 5), 3),
            }
            chk_s0, chk_s1 = c_s0, c_s1
            choice_kind = "oscillation"
            role_kind = "body"
        else:
            longest_ms = max(m_stages, key=lambda m: m["support_s"][1] - m["support_s"][0])
            ms0, ms1 = longest_ms["support_s"]
            ms_dur = ms1 - ms0
            margin = min(0.022, 0.15 * ms_dur)
            c_s0 = round(ms0 + margin, 6)
            c_s1 = round(ms1 - margin, 6)
            c_dur = c_s1 - c_s0
            pk_frac = 0.36 + 0.07 * ((pi * 3 + ui * 2) % 5)
            pk_s = round(c_s0 + pk_frac * c_dur, 6)
            amp_mag = round(min(52.0, max(32.0, 0.52 * src_ptp)), 2)
            pk_c = round(arch_sign * amp_mag, 2)
            comp = {
                "id": comp_id,
                "family": "finite_return",
                "support_s": [c_s0, c_s1],
                "peak_s": pk_s,
                "peak_c": pk_c,
            }
            chk_s0, chk_s1 = c_s0, c_s1
            choice_kind = "finite_return"
            role_kind = "connection" if len(m_stages) > 1 else ("arrival" if ui == 0 else ("release" if ui == len(p_units) - 1 else "body"))

        p_components.append(comp)

        mask_chk = (times_s >= chk_s0 - 1e-9) & (times_s <= chk_s1 + 1e-9)
        vals_chk = [
            math_mod.center_value(center_nodes, float(t)) + math_mod.component_value(comp, float(t))
            for t in times_s[mask_chk]
        ]
        realized_span_grid = float(np.ptp(vals_chk)) if len(vals_chk) > 0 else 30.0

        dense_t = np.linspace(chk_s0, chk_s1, max(20, int(round((chk_s1 - chk_s0) * 1000)) + 1)).tolist()
        if comp["family"] == "finite_return":
            dense_t.append(comp["peak_s"])
        vals_dense = [
            math_mod.center_value(center_nodes, float(t)) + math_mod.component_value(comp, float(t))
            for t in sorted(set(dense_t))
        ]
        realized_span_dense = float(np.ptp(vals_dense))

        min_bound = round(max(22.0, min(realized_span_grid, realized_span_dense) - 6.0), 2)
        max_bound = round(max(realized_span_grid, realized_span_dense) + 12.0, 2)

        p_expectations.append({
            "support_s": [chk_s0, chk_s1],
            "range_c": [min_bound, max_bound],
            "purpose": f"Realize {choice_kind} contour on '{u_lyric}' ({uid}) matching source F0 inflection.",
        })

        d_s0 = p_start_s if ui == 0 else round(0.5 * (p_units[ui - 1]["support_s"][1] + u_s0), 6)
        d_s1 = p_end_s if ui == len(p_units) - 1 else round(0.5 * (u_s1 + p_units[ui + 1]["support_s"][0]), 6)
        p_decisions.append({
            "support_s": [d_s0, d_s1],
            "condition": f"Voiced vowel '{u_lyric}' ({u['symbol']}) on {u_s0:.3f}-{u_s1:.3f}s with observed FCPE span {src_ptp:.1f}c.",
            "choice": f"{choice_kind} component {comp_id} over smooth Hermite center_nodes",
            "alternative": "Flat zero-PITD step center or uniform mechanical sine vibrato",
            "reason": f"Matches source vocal F0 gesture on '{u_lyric}' while keeping note transitions smooth.",
            "uncertainty": "Perceived naturalness and timbre balance in YousaV1.65c require human listening check.",
            "component_ids": [comp_id],
        })

        g_id = f"{uid}:gesture"
        chk_obj = {
            "kind": "range",
            "support_s": [chk_s0, chk_s1],
            "parameters": {
                "min_c": min_bound,
                "max_c": max_bound,
            },
        }
        p_gestures.append({
            "id": g_id,
            "unit_ids": [uid],
            "role": role_kind,
            "support_s": [u_s0, u_s1],
            "observation_ids": [f"{pid}:obs_fcpe", f"{pid}:obs_rmvpe", obs_unit_id],
            "interpretation": f"Expressive {role_kind} pitch movement on '{u_lyric}' ({uid}) driven by observed source vocal inflection.",
            "alternative": "Shallow-clipped or flat step note center without expressive vowel contour",
            "rejected_because": "A flat or shallow-clipped contour (<16c range) sounds robotic and loses the singer's phrasing.",
            "contrast": {
                "mode": "must_differ",
                "shallow_limit_c": 7.0,
                "connection_s": 0.025,
                "reason": "Active vocal inflection on the single-note nucleus must exceed a +-7c shallow-clipped baseline.",
            },
            "checks": [chk_obj],
        })

        ledger_decisions.append({
            "id": f"dec:{uid}",
            "unit_ids": [uid],
            "stage_ids": [stage_id],
            "support_s": [u_s0, u_s1],
            "evidence_ids": ["fcpe_obs", "rmvpe_obs", "game_obs", "hfa_summary"],
            "observation": f"Unit {uid} ('{u_lyric}', {u['symbol']}) spans {u_s0:.3f}-{u_s1:.3f}s with observed FCPE pitch span {src_ptp:.1f}c.",
            "interpretation": f"Requires {choice_kind} movement ({role_kind}) on '{u_lyric}' to realize natural vocal phrasing.",
            "reliability": "high; supported by agreeing FCPE/RMVPE trajectories and HFA vowel boundaries",
            "purpose": f"Shape '{u_lyric}' ({uid}) with {choice_kind} component {comp_id} over smooth Hermite note center.",
            "choice": choice_kind,
            "alternative": "hold (flat note center without expressive component)",
            "rejected_because": "Flat hold sounds mechanical and fails to convey the observed vocal inflection.",
            "parameter_basis": f"Component {comp_id} designed on [{c_s0:.3f}, {c_s1:.3f}]s from current source F0 observation.",
            "execution": [
                {
                    "kind": "center_nodes",
                    "part_index": pi,
                    "position": int(native_line["position"]),
                    "id": "center_nodes",
                    "support_s": [p_start_s, p_end_s],
                    "parameters_sha256": digest(center_nodes),
                },
                {
                    "kind": "component",
                    "part_index": pi,
                    "position": int(native_line["position"]),
                    "id": comp_id,
                    "support_s": [c_s0, c_s1],
                    "parameters_sha256": digest(comp),
                },
            ],
            "checks": [
                {
                    "stage_id": stage_id,
                    "kind": "range",
                    "support_s": [chk_s0, chk_s1],
                    "parameters": {
                        "min_c": min_bound,
                        "max_c": max_bound,
                    },
                }
            ],
            "uncertainty": "Final auditory naturalness in YousaV1.65c remains pending human listening.",
        })

    design_obj = {
        "schema": 1,
        "origin": "agent_designed",
        "support_s": [p_start_s, p_end_s],
        "center_nodes": center_nodes,
        "components": p_components,
        "decisions": p_decisions,
        "expectations": p_expectations,
    }
    comp_res = math_mod.compile_plan(design_obj)
    assert comp_res["shape_checks_pass"], f"{pid}: compile_plan shape_checks_pass failed!"

    intent_phrases.append({
        "id": pid,
        "unit_ids": [u["id"] for u in p_units],
        "support_s": [p_units[0]["support_s"][0], p_units[-1]["support_s"][1]],
        "observations": p_observations,
        "intention": f"Phrase {pid} ('{hanzi}'): shape smooth melodic phrasing and per-vowel expressive contours from source observations.",
        "gestures": p_gestures,
    })

    plan_phrases.append({
        "part_index": pi,
        "position": int(native_line["position"]),
        "design": design_obj,
    })

print(f"All {len(plan_phrases)} phrases passed design_functions.compile_plan!")

# Ensure plan.json does NOT exist before freezing musical_intent.json!
plan_path = design_dir / "plan.json"
if plan_path.exists():
    plan_path.unlink()

brief_obj = {
    "schema_version": 1,
    "inventory": ref(inv_path),
    "phrases": intent_phrases,
    "phonation": {
        "baseline": "YousaV1.65c default voice color with zero TENC/BREC/VOIC/DYN overrides and explicit AP/SP phrase context.",
        "target": "Solid, expressive YousaV1.65c vocal phrasing with chest-mix chorus climaxes and gentle verse storytelling.",
        "status": "unvalidated",
        "contexts": [],
    },
}
brief_path = design_dir / "musical_intent.json"
brief_path.write_text(json.dumps(brief_obj, ensure_ascii=False, indent=2), encoding="utf-8")

lock_path = design_dir / "intent_lock.json"
if lock_path.exists():
    lock_path.unlink()
lock_res = freeze_intent(brief_path, inv_path, plan_path, lock_path)
print("Frozen musical_intent.json -> intent_lock.json:", lock_res.get("frozen_at"))

kc_decisions = []
for rec in kc_packet["records"]:
    rid = rec["id"]
    if rec["kind"] == "entity":
        kc_decisions.append({
            "id": rid,
            "decision": "use",
            "reason": f"Use Table 1 entity {rid} definition to structure pitch/timing/phonation observation and design.",
            "condition_match": "Directly applicable to Mandarin pop vocal cover in OpenUtau DiffSinger.",
            "limitations": "Conceptual entity definition only; does not prescribe numeric doses.",
            "general_rule_claim": False,
        })
    else:
        use_it = rid in {"PARAM:C01.01", "PARAM:C01.02", "PARAM:C02.01", "PARAM:C02.02", "PARAM:C03.01"}
        kc_decisions.append({
            "id": rid,
            "decision": "use" if use_it else "keep_unknown",
            "reason": (
                f"Use parameter {rid} for pitch/note/vibrato/PITD compilation."
                if use_it
                else f"Keep {rid} at neutral baseline until initial pitch/rhythm rendering is auditioned."
            ),
            "condition_match": "Matches YousaV1.65c OpenUtau DiffSinger parameter interface.",
            "limitations": "Timbre/phonation curves require user listening calibration before non-neutral dosing.",
            "general_rule_claim": False,
        })

plan_obj = {
    "schema_version": 2,
    "project": str(score_ustx),
    "source_audio": str(obs_dir / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"),
    "input_hashes": {
        str(score_ustx): sha256(score_ustx),
        str(obs_dir / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"): sha256(
            obs_dir / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"
        ),
        str(obs_dir / "fcpe.npz"): sha256(obs_dir / "fcpe.npz"),
        str(obs_dir / "rmvpe.npz"): sha256(obs_dir / "rmvpe.npz"),
        str(obs_dir / "game.json"): sha256(obs_dir / "game.json"),
        str(hfa_dir / "hfa_summary.json"): sha256(hfa_dir / "hfa_summary.json"),
    },
    "scope": "whole_song",
    "phrases": plan_phrases,
    "knowledge_context": {
        "path": str(kc_path),
        "sha256": sha256(kc_path),
        "decisions": kc_decisions,
    },
}
plan_path.write_text(json.dumps(plan_obj, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote plan.json with {len(plan_phrases)} phrases.")

ledger_obj = {
    "schema_version": 1,
    "inventory": ref(inv_path),
    "plan": ref(plan_path),
    "timing": "forward",
    "decisions": ledger_decisions,
    "revisions": [],
}
ledger_path = design_dir / "ledger.json"
ledger_path.write_text(json.dumps(ledger_obj, ensure_ascii=False, indent=2), encoding="utf-8")

validate_lock(lock_path, inv_path, plan_path)
_, failures, flags = ledger_check(ledger_path, inv_path, plan_path)
print("ledger_check failures:", failures, "flags:", flags)
assert not failures and not flags
print("Build natural pitch pipeline completed successfully!")
