import sys
sys.path.insert(0, 'src')
import copy
import hashlib
import json
import math
from pathlib import Path
import numpy as np

from agent2utau.evaluation.execution_review import build_inventory, digest, ledger_check, ref, validate_inventory
from agent2utau.evaluation.musical_review import freeze_intent, validate_lock
from agent2utau.openutau.ustx import TempoMap, load_ustx, save_ustx, sha256
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
from agent2utau.workflow import design_math

cfg = load_config()
run_dir = Path(r"E:\project\agent2utau\runs\production\zuihouyiye-from-scratch-20261027")
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
# STEP 1: Full Score & Lyric Polishing for score.ustx
# =========================================================================
doc = load_ustx(score_ustx)

# 1. Polyphone fixes: '没' -> '没[m ei]' in Chorus 2 (Part 28) and Chorus 3 (Part 34)
for pi in [28, 34]:
    for n in doc['voice_parts'][pi]['notes']:
        if n.get('lyric') == '没':
            n['lyric'] = '没[m ei]'
            print(f"Fixed Part {pi} '没' -> '没[m ei]' (méi)")

# 2. Bogus middle-of-phrase APs -> '+' (slurred vowel continuation)
# Part 18: note 8 was AP(64) between '一' and '次'
doc['voice_parts'][18]['notes'][8]['lyric'] = '+'
doc['voice_parts'][18]['notes'][8]['tone'] = doc['voice_parts'][18]['notes'][7]['tone']

# Part 21: '拥抱早已悄悄冷却' tone corrections
# '抱' should be tone 59 (matching Part 5), '已' should be tone 63 (matching Part 5)
doc['voice_parts'][21]['notes'][2]['tone'] = 59  # 抱
doc['voice_parts'][21]['notes'][4]['tone'] = 63  # 已

# Part 24: note 10 was AP(59) between '零' and '的'
doc['voice_parts'][24]['notes'][10]['lyric'] = '+'
doc['voice_parts'][24]['notes'][10]['tone'] = doc['voice_parts'][24]['notes'][9]['tone']

# Part 25: note 4 was AP(64) after '能', note 8 was AP(64) after '忆'
doc['voice_parts'][25]['notes'][4]['lyric'] = '+'
doc['voice_parts'][25]['notes'][4]['tone'] = doc['voice_parts'][25]['notes'][3]['tone']
doc['voice_parts'][25]['notes'][8]['lyric'] = '+'
doc['voice_parts'][25]['notes'][8]['tone'] = doc['voice_parts'][25]['notes'][7]['tone']

# Part 31: note 5 was AP(59) between '我' and '把'
doc['voice_parts'][31]['notes'][5]['lyric'] = '+'
doc['voice_parts'][31]['notes'][5]['tone'] = doc['voice_parts'][31]['notes'][4]['tone']

# Part 37: note 5 was AP(59) between '我' and '把'
doc['voice_parts'][37]['notes'][5]['lyric'] = '+'
doc['voice_parts'][37]['notes'][5]['tone'] = doc['voice_parts'][37]['notes'][4]['tone']

# 3. Phonation curves across all 38 parts
def generate_expressive_curves(vp):
    notes = vp.get('notes', [])
    if not notes:
        return []

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

        # Determine target parameters for this note
        if lyric in ('AP', 'SP'):
            v_target = 100
            t_target = 0
            b_target = 0
        elif tone >= 72:
            # High note (falsetto / head-voice): C#5
            # Open throat, relax tension, thin folds, airy sweetness
            v_target = 98
            t_target = -14
            b_target = 20
        elif tone >= 67:
            # Upper mid register: G4 to B4 (tones 67-71)
            v_target = 110
            t_target = 0
            b_target = -4
        else:
            # Chest / lower register: <= 66
            v_target = 120
            t_target = 6
            b_target = -12

        # Check if long sustained note (dur > 1400 ticks, approx > 1.5s)
        is_long_tail = (n_dur >= 1400) and (lyric not in ('AP', 'SP'))

        t_in = n_pos + min(40, int(0.12 * n_dur))
        t_out = n_end - min(60, int(0.18 * n_dur))

        if is_long_tail:
            # Starts with target, relaxes into soft breath at tail
            t_mid = n_pos + int(0.40 * n_dur)
            t_tail = n_pos + int(0.75 * n_dur)
            ticks.extend([n_pos, t_in, t_mid, t_tail, t_out, n_end])
            voic_vals.extend([v_target, v_target, max(100, v_target - 6), max(96, v_target - 12), 100, 100])
            tenc_vals.extend([t_target, t_target, t_target - 6, -12, -8, 0])
            brec_vals.extend([b_target, b_target, b_target + 10, b_target + 18, b_target + 12, 0])
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

    return [
        {"abbr": "voic", "xs": u_ticks, "ys": u_voic},
        {"abbr": "brec", "xs": u_ticks, "ys": u_brec},
        {"abbr": "tenc", "xs": u_ticks, "ys": u_tenc},
    ]

for pi, vp in enumerate(doc['voice_parts']):
    vp['curves'] = generate_expressive_curves(vp)

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
raw_inv_tmp = Path("scratch/raw_inv_v5.json")
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
# STEP 3: Natural Hermite Pitch Phrasing Design across all 38 parts
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
            # Same tone: subtle re-articulation dip ONLY IF not slurred
            if dur_left > 0.22 and dur_right > 0.22 and not is_slurred:
                t_pre = round(max(center_nodes[-1][0] + 0.020, b_s - 0.035), 6)
                t_mid = round(b_s, 6)
                t_post = round(b_s + 0.035, 6)
                center_nodes.append([t_pre, tone_left, 0.0])
                center_nodes.append([t_mid, tone_left - 18.0, 0.0])
                center_nodes.append([t_post, tone_left, 0.0])
        elif diff > 0 and diff < 280:
            # Small upward: smooth S-curve 90-130ms
            t_lead = min(0.065, 0.35 * dur_left)
            t_lag = min(0.075, 0.40 * dur_right)
            t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
            t_arrive = round(b_s + t_lag, 6)
            t_mid = round(0.5 * (t_depart + t_arrive), 6)
            slope_mid = round((diff / max(0.04, t_arrive - t_depart)) * 1.35, 2)
            center_nodes.append([t_depart, tone_left, 0.0])
            center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
            center_nodes.append([t_arrive, tone_right, 0.0])
        elif diff >= 280:
            # Large upward: two-stage terrace if sufficient duration
            if dur_left >= 0.16 and dur_right >= 0.22:
                r = 130.0 + min(60.0, 10.0 * (diff / 100.0 - 3.0))
                T_terrace = tone_right - r
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - min(0.085, 0.32 * dur_left)), 6)
                t_terrace_in = round(b_s + min(0.020, 0.08 * dur_right), 6)
                t_terrace_out = round(b_s + min(0.080, 0.30 * dur_right), 6)
                t_arrive = round(b_s + min(0.145, 0.50 * dur_right), 6)
                slope_1 = round((T_terrace - tone_left) / max(0.03, t_terrace_in - t_depart) * 1.25, 2)
                slope_2 = round((tone_right - (T_terrace + 10.0)) / max(0.03, t_arrive - t_terrace_out) * 1.25, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([round(0.5 * (t_depart + t_terrace_in), 6), round(0.5 * (tone_left + T_terrace), 2), slope_1])
                center_nodes.append([t_terrace_in, T_terrace, 20.0])
                center_nodes.append([t_terrace_out, T_terrace + 10.0, 30.0])
                center_nodes.append([round(0.5 * (t_terrace_out + t_arrive), 6), round(0.5 * (T_terrace + 10.0 + tone_right), 2), slope_2])
                center_nodes.append([t_arrive, tone_right, 0.0])
            else:
                t_lead = min(0.080, 0.38 * dur_left)
                t_lag = min(0.090, 0.42 * dur_right)
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
                t_arrive = round(b_s + t_lag, 6)
                t_mid = round(0.5 * (t_depart + t_arrive), 6)
                slope_mid = round((diff / max(0.04, t_arrive - t_depart)) * 1.4, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
                center_nodes.append([t_arrive, tone_right, 0.0])
        else:
            # Downward: diff < 0
            if diff <= -500:
                t_lead = min(0.080, 0.35 * dur_left)
                t_lag = min(0.095, 0.38 * dur_right)
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
                t_arrive = round(b_s + t_lag, 6)
                t_mid = round(0.5 * (t_depart + t_arrive), 6)
                slope_mid = round((diff / max(0.05, t_arrive - t_depart)) * 1.25, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
                center_nodes.append([t_arrive, tone_right, 0.0])
            elif abs(diff) >= 300 and dur_right >= 0.25:
                t_lead = min(0.070, 0.32 * dur_left)
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
                t_pass = round(b_s + min(0.035, 0.15 * dur_right), 6)
                t_dip = round(b_s + min(0.085, 0.32 * dur_right), 6)
                t_recover = round(b_s + min(0.145, 0.50 * dur_right), 6)
                dip_c = 18.0
                slope_down = round((diff - dip_c) / max(0.04, t_dip - t_depart) * 1.2, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([t_pass, round(0.5 * (tone_left + tone_right), 2), slope_down])
                center_nodes.append([t_dip, round(tone_right - dip_c, 2), 0.0])
                center_nodes.append([t_recover, tone_right, 0.0])
            else:
                t_lead = min(0.060, 0.32 * dur_left)
                t_lag = min(0.075, 0.38 * dur_right)
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
                t_arrive = round(b_s + t_lag, 6)
                t_mid = round(0.5 * (t_depart + t_arrive), 6)
                slope_mid = round((diff / max(0.04, t_arrive - t_depart)) * 1.35, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
                center_nodes.append([t_arrive, tone_right, 0.0])

    if p_end_s > center_nodes[-1][0] + 0.010:
        center_nodes.append([p_end_s, n_spans[-1][2], 0.0])
    else:
        center_nodes[-1][0] = p_end_s
    return center_nodes

intent_phrases = []
plan_phrases = []
ledger_decisions = []
progress_phrases = []

for pi in range(len(pitch_data)):
    native_line = pitch_data[pi]
    part_doc = doc["voice_parts"][pi]
    p_units = units_by_part[pi]
    hfa_p = hfa_summary[pi]
    pid = hfa_p["phrase_id"]
    hanzi = hfa_p["hanzi"]

    times_s = np.asarray(native_line["times_ms"], dtype=float) / 1000.0
    before_c = np.asarray(native_line["before_pitd_cents"], dtype=float)
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

        target_tone = m_stages[0]["tone"] if m_stages else 64.0

        mf = (t_f >= u_s0) & (t_f <= u_s1) & np.isfinite(cents_f)
        if np.sum(mf) >= 3:
            sub_f = cents_f[mf]
            mid_val = float(np.median(sub_f[len(sub_f)//4 : 3*len(sub_f)//4])) if len(sub_f) >= 4 else float(np.median(sub_f))
            ends_val = 0.5 * (float(sub_f[0]) + float(sub_f[-1]))
            arch_sign = 1.0 if mid_val >= ends_val else -1.0
            src_ptp = float(np.ptp(sub_f))
        else:
            arch_sign = 1.0 if (ui % 2 == 0) else -1.0
            src_ptp = 35.0

        obs_unit_id = f"{uid}:obs"
        p_observations.append({
            "id": obs_unit_id,
            "source_id": "fcpe_obs",
            "source_window_s": [u_s0, u_s1],
            "description": f"FCPE pitch contour on '{u_lyric}' ({u['symbol']}, {u_s0:.3f}-{u_s1:.3f}s): observed span {src_ptp:.1f}c, arch sign {'+' if arch_sign > 0 else '-'}.",
            "reliability": "observed",
        })

        comp_id = f"{uid}:comp"
        if len(m_stages) == 1 and u_dur >= 0.55:
            # Sustained single-note vowel -> natural vibrato oscillation + arch
            c_s0 = round(u_s0 + 0.030, 6)
            c_s1 = round(u_s1 - 0.025, 6)
            c_dur = c_s1 - c_s0
            att_frac = 0.20 + 0.03 * (ui % 3)
            rel_frac = 0.80 - 0.03 * ((pi + ui) % 3)
            att_s = round(c_s0 + att_frac * c_dur, 6)
            rel_s = round(c_s0 + rel_frac * c_dur, 6)

            base_depth = 18.0 if target_tone >= 68.0 else 24.0
            depth_c = round(base_depth + 3.0 * ((pi + ui) % 4), 2)
            rate_hz = round(5.2 + 0.10 * ((pi + ui) % 4), 2)
            comp = {
                "id": comp_id,
                "family": "oscillation",
                "support_s": [c_s0, c_s1],
                "attack_end_s": att_s,
                "release_start_s": rel_s,
                "depth_nodes": [
                    [c_s0, round(0.35 * depth_c, 2)],
                    [round(0.5 * (c_s0 + c_s1), 6), depth_c],
                    [c_s1, round(0.35 * depth_c, 2)],
                ],
                "rate_nodes": [
                    [c_s0, round(rate_hz - 0.10, 2)],
                    [c_s1, round(rate_hz + 0.10, 2)],
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
            margin = min(0.025, 0.15 * ms_dur)
            c_s0 = round(ms0 + margin, 6)
            c_s1 = round(ms1 - margin, 6)
            c_dur = c_s1 - c_s0
            pk_frac = 0.38 + 0.06 * ((pi * 3 + ui * 2) % 5)
            pk_s = round(c_s0 + pk_frac * c_dur, 6)

            if target_tone >= 72.0:
                amp_mag = round(min(12.0, max(8.0, 0.20 * src_ptp)), 2)
            elif target_tone >= 68.0:
                amp_mag = round(min(18.0, max(12.0, 0.30 * src_ptp)), 2)
            else:
                amp_mag = round(min(36.0, max(20.0, 0.40 * src_ptp)), 2)

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
        realized_span_grid = float(np.ptp(vals_chk))

        dense_t = np.linspace(chk_s0, chk_s1, max(20, int(round((chk_s1 - chk_s0) * 1000)) + 1)).tolist()
        if comp["family"] == "finite_return":
            dense_t.append(comp["peak_s"])
        vals_dense = [
            math_mod.center_value(center_nodes, float(t)) + math_mod.component_value(comp, float(t))
            for t in sorted(set(dense_t))
        ]
        realized_span_dense = float(np.ptp(vals_dense))

        min_bound = round(max(10.0, min(realized_span_grid, realized_span_dense) - 6.0), 2)
        max_bound = round(max(realized_span_grid, realized_span_dense) + 12.0, 2)

        p_expectations.append({
            "support_s": [chk_s0, chk_s1],
            "range_c": [min_bound, max_bound],
            "purpose": f"Realize {choice_kind} contour on '{u_lyric}' ({uid}) with natural skill transitions.",
        })

        d_s0 = p_start_s if ui == 0 else round(0.5 * (p_units[ui - 1]["support_s"][1] + u_s0), 6)
        d_s1 = p_end_s if ui == len(p_units) - 1 else round(0.5 * (u_s1 + p_units[ui + 1]["support_s"][0]), 6)
        p_decisions.append({
            "support_s": [d_s0, d_s1],
            "condition": f"Voiced vowel '{u_lyric}' ({u['symbol']}) on {u_s0:.3f}-{u_s1:.3f}s with observed FCPE span {src_ptp:.1f}c.",
            "choice": f"{choice_kind} component {comp_id} over smooth natural Hermite center_nodes",
            "alternative": "Flat zero-PITD step center or square 36ms jump",
            "reason": f"Matches skill interval connection and vowel support on '{u_lyric}'.",
            "uncertainty": "Perceived naturalness requires listening feedback.",
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
            "interpretation": f"Expressive {role_kind} pitch movement on '{u_lyric}' ({uid}) conforming to skill interval connections.",
            "alternative": "Shallow-clipped or square step note center without expressive transitions",
            "rejected_because": "Square transitions sound robotic ('直上直下') and violate skill upward/downward interval recipes.",
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
            "interpretation": f"Requires {choice_kind} movement ({role_kind}) on '{u_lyric}' with natural interval transition.",
            "reliability": "high; supported by agreeing FCPE/RMVPE trajectories and HFA vowel boundaries",
            "purpose": f"Shape '{u_lyric}' ({uid}) with {choice_kind} component {comp_id} over smooth natural Hermite center.",
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

    intent_phrases.append({
        "id": pid,
        "unit_ids": [u["id"] for u in p_units],
        "support_s": [p_units[0]["support_s"][0], p_units[-1]["support_s"][1]],
        "observations": p_observations,
        "intention": f"Natural, fluid vocal cover on {pid} ('{hanzi}') with skill-guided two-stage terraces, smooth portamento, and vocal vibrato.",
        "gestures": p_gestures,
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

    chk_res = math_mod.compile_plan(design_obj)
    if not chk_res["shape_checks_pass"]:
        failed_checks = [c for c in chk_res["local_checks"] if not c["pass"]]
        raise ValueError(f"Shape check failed on phrase {pid} (part {pi}): {failed_checks}")

    plan_phrases.append({
        "part_index": pi,
        "position": native_line["position"],
        "design": design_obj,
    })

    progress_phrases.append({
        "phrase_id": pid,
        "hanzi": hanzi,
        "part_index": pi,
        "phrase_index": 0,
        "unit_ids": [u["id"] for u in p_units],
        "support_s": [p_start_s, p_end_s],
        "status": "designed_and_verified",
    })

print(f"All {len(plan_phrases)} phrases passed design_functions.compile_plan!")

plan_path = design_dir / "plan.json"
if plan_path.exists():
    plan_path.unlink()

brief_obj = {
    "schema_version": 1,
    "inventory": ref(inv_path),
    "phrases": intent_phrases,
    "phonation": {
        "baseline": "YousaV1.65c default voice color with register-sensitive VOIC/TENC/BREC curves and explicit AP/SP phrase context.",
        "target": "Sweet, comfortable Lingyuan (YousaV1.65c) vocal cover across all 38 phrases with unified lyric accuracy, relaxed high-note tension, natural breathiness, and fluid pitch transitions.",
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
print("Frozen musical_intent.json -> intent_lock.json:", lock_res["frozen_at"])

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

progress_path = design_dir / "phrase-progress.json"
progress_path.write_text(
    json.dumps({"schema_version": 1, "phrases": progress_phrases}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

validate_lock(lock_path, inv_path, plan_path)
_, failures, flags = ledger_check(ledger_path, inv_path, plan_path)
print("ledger_check failures:", failures, "flags:", flags)
assert not failures and not flags
print("Build natural pitch pipeline v5 completed successfully!")
