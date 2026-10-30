"""年轮 v3：编译 -> 渲染 -> 混音 -> 切片 -> 复检（阶段 D）。

顺序与契约：
  1) 写 review_contract.json（绑定 inventory / ledger / intent_lock）
  2) compile-functions：把 plan 的数值设计编译成 part 级 pitd，并回读校验（<0.501c）
  3) render-project 出人声
  4) 与伴奏混合、出试听切片
  5) review-execution（绑定 ledger/plan/intent-lock）
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
COMPILED = V3 / "compiled"
RENDER = V3 / "render"
OBS = V3 / "observation"
SCRATCH = ROOT / "scratch"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
sys.path.insert(0, str(ROOT / "src"))
from agent2utau.openutau.ustx import sha256


def ref(p):
    return dict(path=str(Path(p).resolve()), sha256=sha256(p))


DESIGN.mkdir(parents=True, exist_ok=True)
contract = dict(schema_version=2,
                inventory=ref(DESIGN / "review-inventory.json"),
                ledger=ref(DESIGN / "ledger.json"),
                reviews=None,
                intent_lock=ref(DESIGN / "intent_lock.json"),
                musical_critique=None)
(DESIGN / "review_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
print("review_contract written")

if COMPILED.exists() and "--render-only" not in sys.argv:
    shutil.rmtree(COMPILED)
    cmd = [PY, "-m", "agent2utau.cli", "compile-functions",
           "--plan", str(DESIGN / "plan.json"),
           "--out", str(COMPILED),
           "--review-contract", str(DESIGN / "review_contract.json")]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    print("compile rc:", r.returncode)
    print((r.stdout or "")[-3000:])
    if r.returncode != 0:
        print("STDERR:", (r.stderr or "")[-3000:])
        raise SystemExit(1)

    report = json.loads((COMPILED / "compile_report.json").read_text(encoding="utf-8"))
    print("native_max_error_c:", report.get("native_max_error_c"))
    print("technical_execution_complete:", report.get("technical_execution_complete"))
    print("workflow_review_complete:", report.get("workflow_review_complete"))
    print("musical_quality:", report.get("musical_quality"))
else:
    print("compile skipped (render-only)")

# ---------------- 渲染 ----------------
RENDER.mkdir(parents=True, exist_ok=True)
vocal = RENDER / "vocal.wav"
for stale in list(RENDER.glob("vocal*.wav")) + list(RENDER.glob("vocal*.review.json")):
    stale.unlink()
r = subprocess.run([PY, "-m", "agent2utau.cli", "render-project", "--project",
                    str(COMPILED / "project.ustx"), "--out", str(vocal)],
                   capture_output=True, text=True, cwd=str(ROOT))
print("render rc:", r.returncode)
print((r.stdout or "")[-800:])
if r.returncode != 0:
    print("RENDER STDERR:", (r.stderr or "")[-2500:])
    raise SystemExit(1)
vocal_vocal = RENDER / "vocal_vocal.wav"
if not vocal_vocal.exists():
    vocal_vocal = vocal
print("vocal:", vocal_vocal, vocal_vocal.exists(), vocal_vocal.stat().st_size if vocal_vocal.exists() else 0)
