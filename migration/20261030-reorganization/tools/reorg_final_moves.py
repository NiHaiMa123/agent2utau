"""收尾移动：对剩余 51 个 scratch 文件逐个给出证据化归属（能判的搬，不能判的登记不动）。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")
V3 = "songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029"
V1 = "songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-20261028"
V2 = "songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-v2-20261028"
LP = "songs/lastpage/sessions/20261027__unknown-model__zuihouyiye-from-scratch-20261027"

# file -> (target dir, evidence)
DECISIONS = {}
for name in ("v9_compile.log", "v9_render.log", "v11_compile.log", "v11_render.log",
             "v12_compile.log", "v12_render.log", "v13_compile.log", "v13_render.log",
             "v14_compile.log", "v14_render.log", "v15_compile.log", "v18_compile.log",
             "v18_render.log", "v19_compile.log", "v19_render.log", "v20_compile.log",
             "v20_render.log", "v21_compile.log", "v21_render.log", "v22_compile.log",
             "v22_render.log", "v3_render.log", "v3b_compile.log", "v3e_render.log",
             "v3f_render.log", "v3g_compile.log", "v3h_compile.log", "v3h_render.log",
             "v3i_compile.log", "v3k_render.log", "v5_compile.log"):
    DECISIONS[name] = (f"{V3}/reports", "同前缀 vN 脚本已归入 nianlun-v3-20261029 session，本日志是同批次产物")
DECISIONS["final_render.log"] = (f"{V3}/reports", "日志正文解码后指向 runs/production/nianlun-v3-20261029")
DECISIONS["_tmp.py"] = (f"{V3}/scripts", "正文为“阶段5f”，对应同 session 的 v3_stage5f_fix.py")
for n in ("audit_nianlun_grading.json", "audit_nianlun_phrases.json", "second_half_lyrics.txt",
          "notes_55_88.txt", "full_structure_compare.txt", "nianlun_phrase_tones.json"):
    DECISIONS[n] = (f"{V1}/reports", "年轮 from-scratch 首版（51 句 v1）的逐句审查与词表产物")
DECISIONS["v1_v2_compare.json"] = (f"{V2}/reports", "v1 与 v2 的同口径比较结果，属 v2 制作 session")
DECISIONS["v2_review_observations.json"] = (f"{V2}/reports", "v2 复检用的实图审观察记录")
for n in ("test_p29_A_solid_vocal.review.json", "test_p29_B_strong_vocal.review.json",
          "test_p29_baseline_vocal.review.json"):
    DECISIONS[n] = (f"{LP}/reports", "p29 变体渲染收据，与同 session 的 render_p29_variants.py 同批")

remaining = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files", "scratch/"],
                                       capture_output=True, text=True, encoding="utf-8",
                                       errors="replace").stdout.split("\n") if l]
moved, kept = [], []
for p in remaining:
    name = Path(p).name
    if name in DECISIONS:
        target_dir, why = DECISIONS[name]
        new = f"{target_dir}/{name}"
        r = subprocess.run(["git", "-C", str(ROOT), "mv", p, new], capture_output=True, text=True)
        print(("OK  " if r.returncode == 0 else "FAIL"), p, "->", new)
        if r.returncode == 0:
            moved.append((p, new, why))
        else:
            kept.append((p, "mv failed: " + r.stderr.strip()[:80]))
    else:
        kept.append((p, "正文/目录无法确证歌曲归属，按计划登记 uncertain 并保留原址"))
print("moved:", len(moved), "kept:", len(kept))
for k in kept:
    print("   keep:", k[0], "|", k[1])
json.dump(dict(moved=[dict(old_path=a, new_path=b, reason=c) for a, b, c in moved],
               kept=[dict(old_path=a, reason=b) for a, b in kept]),
          open(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_final_moves.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
