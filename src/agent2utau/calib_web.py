"""Local web UI for M2.5 structure calibration adjudication (§10.1.5).

A thin read/decide layer over the calibration store — every decision still
goes through `structure_calibration.decide()` (byte-level verify_package +
append-only revisions). The page never reveals which option is the machine
candidate; OPTION_0/OPTION_1 are shown as A/B exactly as stored.
"""
from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .structure_calibration import (calib_dir, current_decision, decide,
                                    rebuild_calibration_state)

_PAGE = r"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>Structure Calibration — M2.5</title>
<style>
:root{--bg:#14161a;--panel:#1c1f26;--line:#2c313c;--fg:#e8eaf0;--dim:#9aa3b2;
--acc:#4f9cf9;--ok:#3fbf7f;--warn:#e0b34e;--bad:#e06060}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 system-ui,Segoe UI,sans-serif;display:flex;height:100vh}
#list{width:300px;min-width:300px;overflow-y:auto;border-right:1px solid var(--line);
background:var(--panel)}
#list .it{padding:10px 14px;border-bottom:1px solid var(--line);cursor:pointer}
#list .it:hover{background:#232834}#list .it.cur{background:#24304a}
#list .it .id{font-weight:600;font-size:13px}
#list .it .meta{font-size:12px;color:var(--dim)}
.badge{display:inline-block;padding:1px 8px;border-radius:9px;font-size:11px;
background:#333a47;color:var(--dim)}
.badge.done{background:#1f4433;color:var(--ok)}
#main{flex:1;overflow-y:auto;padding:24px 32px}
h1{font-size:17px;margin:0 0 4px}h2{font-size:14px;color:var(--dim);
font-weight:400;margin:0 0 20px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:16px 20px;margin-bottom:14px;max-width:860px}
.card h3{margin:0 0 10px;font-size:13px;color:var(--dim);font-weight:600;
letter-spacing:.04em}
audio{width:100%;height:36px}
.row{display:flex;gap:14px;flex-wrap:wrap}.row>div{flex:1;min-width:300px}
button{cursor:pointer;border:1px solid var(--line);background:#242a36;
color:var(--fg);border-radius:8px;padding:9px 18px;font-size:14px}
button:hover{border-color:var(--acc)}
button.a{border-color:#3a5f95}button.b{border-color:#3a5f95}
button.sel{background:var(--acc);border-color:var(--acc);color:#fff}
#decisions{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
#bar{height:6px;background:#2a303c;border-radius:3px;margin:10px 0 22px}
#bar>div{height:100%;background:var(--ok);border-radius:3px}
.kbd{color:var(--dim);font-size:12px}
.prev-out{margin-top:8px;font-size:13px;color:var(--warn)}
.nav{display:flex;gap:10px;margin-bottom:16px}
</style></head><body>
<div id="list"></div>
<div id="main">
<h1>M2.5 Structure Calibration</h1>
<h2 id="counts"></h2><div id="bar"><div></div></div>
<div class="nav">
<button onclick="nav(-1)">← 上一项</button>
<button onclick="nav(1)">下一项 →</button>
<button onclick="navPending()">下一个未裁决 ↷</button>
<span class="kbd" style="align-self:center;margin-left:8px">
快捷键: 3=目标原曲 4=目标人声 1/2=选项A/B·聚焦 5/6=选项A/B·整段 S=原曲整段 V=人声整段 | A/B=选择 E=差不多 X=都不对 ←→=切换</span>
</div>
<div id="detail"></div>
</div>
<script>
let items=[], cur=0, decided={};
const CH={A:'OPTION_0',B:'OPTION_1'};
const OUT={human_confirmed_machine_split:'Split 更对(已确认)',
machine_structure_false_positive:'Baseline 更对',
no_demonstrated_benefit:'都差不多',unresolved:'都不对'};
async function load(){
 const r=await fetch('/api/state');const j=await r.json();
 items=j.items;decided={};
 j.reviewed.forEach(x=>decided[x.cal_item_id]=x);
 document.getElementById('counts').textContent=
  `已裁决 ${j.reviewed_count} / ${j.total_machine_split_candidates}`+
  ` — split更对 ${j.split_preferred_count} · baseline更对 `+
  `${j.baseline_preferred_count} · 差不多 ${j.equivalent_count} · 都不对 ${j.none_correct_count}`;
 document.querySelector('#bar>div').style.width=
  (100*j.reviewed_count/Math.max(1,j.total_machine_split_candidates))+'%';
 renderList();show(cur);
}
function renderList(){
 const el=document.getElementById('list');el.innerHTML='';
 items.forEach((it,i)=>{
  const d=document.createElement('div');d.className='it'+(i===cur?' cur':'');
  const out=it.outcome;
  d.innerHTML=`<div class="id">#${i+1} ${it.note_id}
   <span class="badge${out?' done':''}">${out?OUT[out]||out:'pending'}</span></div>
   <div class="meta">${it.type} · ${it.phrase.start.toFixed(2)}–${it.phrase.end.toFixed(2)}s</div>`;
  d.onclick=()=>{cur=i;renderList();show(i)};el.appendChild(d);
 });
}
function show(i){
 const it=items[i];if(!it)return;
 const key=it.cal_item_id,pk=it.phrase_key;
 const done=decided[key];
 document.getElementById('detail').innerHTML=`
 <div class="card"><h3>TARGET — ${it.note_id} (${it.type}) · 争议区间
  ${it.region?it.region[0].toFixed(2)+'–'+it.region[1].toFixed(2)+'s':''}</h3>
 <div class="row">
  <div><h3>① 目标区域 · 原曲 ±0.6s（先听原唱几个音）</h3><audio controls src="/audio/focus/${key}/mix.wav"></audio></div>
  <div><h3>② 目标区域 · 分离人声 ±0.6s</h3><audio controls src="/audio/focus/${key}/vocal.wav"></audio></div>
 </div>
 <div class="row">
  <div><h3>原曲整段（辅助）</h3><audio controls src="/audio/phrase/${pk}/SOURCE_PHRASE_original_mix.wav"></audio></div>
  <div><h3>分离人声整段（辅助）</h3><audio controls src="/audio/phrase/${pk}/SOURCE_PHRASE_separated_vocal.wav"></audio></div>
 </div></div>
 <div class="card"><h3>③ 目标聚焦 A/B（盲选 · 从完整渲染裁出 ±0.5s — 主要判断对象）</h3>
 <div class="row">
  <div><h3>选项 A · 目标聚焦</h3><audio controls src="/audio/item/${key}/TARGET_0.wav"></audio></div>
  <div><h3>选项 B · 目标聚焦</h3><audio controls src="/audio/item/${key}/TARGET_1.wav"></audio></div>
 </div></div>
 <div class="card"><h3>④ 整段渲染 A/B（盲选 · 辅助参考 — 目标外可能有渲染器漂移）</h3>
 <div class="row">
  <div><h3>选项 A · 整段</h3><audio controls src="/audio/item/${key}/OPTION_0.wav"></audio></div>
  <div><h3>选项 B · 整段</h3><audio controls src="/audio/item/${key}/OPTION_1.wav"></audio></div>
 </div>
 <div id="decisions">
  <button class="a" onclick="vote('OPTION_0')">A 更对</button>
  <button class="b" onclick="vote('OPTION_1')">B 更对</button>
  <button onclick="vote('equivalent')">都差不多</button>
  <button onclick="vote('none_correct')">都不对</button>
 </div>
 ${done?`<div class="prev-out">已记录: ${OUT[done.outcome]||done.outcome}
  (${done.revision_id}) — 重新选择会追加 revision 覆盖</div>`:''}
 </div>`;
 document.querySelectorAll('audio').forEach(a=>{
  a.addEventListener('play',()=>{document.querySelectorAll('audio').forEach(
   b=>{if(b!==a)b.pause()})});
 });
}
async function vote(choice){
 const it=items[cur];if(!it)return;
 const r=await fetch('/api/decide',{method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cal_item_id:it.cal_item_id,choice})});
 const j=await r.json();
 if(!r.ok){alert('未保存: '+(j.error||r.status));return}
 await load();navPending();
}
function nav(d){cur=Math.min(items.length-1,Math.max(0,cur+d));renderList();show(cur)}
function navPending(){
 const i=items.findIndex(x=>!decided[x.cal_item_id]);
 if(i>=0){cur=i;renderList();show(i)}}
document.addEventListener('keydown',e=>{
 if(e.target.tagName==='INPUT')return;
 const it=items[cur];if(!it)return;
 const pk=it.phrase_key,k=it.cal_item_id;
 const play=src=>{const a=new Audio(src);a.play();
  document.querySelectorAll('audio').forEach(b=>b.pause());};
 const m={'s':`/audio/phrase/${pk}/SOURCE_PHRASE_original_mix.wav`,
  'v':`/audio/phrase/${pk}/SOURCE_PHRASE_separated_vocal.wav`,
  '3':`/audio/focus/${k}/mix.wav`,'4':`/audio/focus/${k}/vocal.wav`,
  '1':`/audio/item/${k}/TARGET_0.wav`,'2':`/audio/item/${k}/TARGET_1.wav`,
  '5':`/audio/item/${k}/OPTION_0.wav`,'6':`/audio/item/${k}/OPTION_1.wav`};
 if(m[e.key])play(m[e.key]);
 else if(e.key==='a'||e.key==='A')vote('OPTION_0');
 else if(e.key==='b'||e.key==='B')vote('OPTION_1');
 else if(e.key==='e'||e.key==='E')vote('equivalent');
 else if(e.key==='x'||e.key==='X')vote('none_correct');
 else if(e.key==='ArrowLeft')nav(-1);
 else if(e.key==='ArrowRight')nav(1);
});
load();
</script></body></html>"""

_ALLOWED = ("OPTION_0.wav", "OPTION_1.wav",
            "SOURCE_PHRASE_original_mix.wav",
            "SOURCE_PHRASE_separated_vocal.wav")


def _focus_wav(run_dir: Path, cal_item_id: str, which: str):
    """Clip the contested target region (±0.6s) from the source audio —
    the original melody is the ground truth for 'one note or two'; the
    synthesized options are only supporting evidence."""
    import soundfile as sf
    mpath = calib_dir(run_dir) / "items" / cal_item_id / "manifest.json"
    if not mpath.exists():
        return None
    man = json.loads(mpath.read_text(encoding="utf-8"))
    region = man.get("target_group", {}).get("region")
    if not region:
        return None
    from .review.render import load_run
    run = load_run(run_dir)
    src = run["original_wav"] if which == "mix" else run["vocals_wav"]
    info = sf.info(str(src))
    a = max(0, int((region[0] - 0.6) * info.samplerate))
    b = min(info.frames, int((region[1] + 0.6) * info.samplerate))
    data, sr = sf.read(str(src), start=a, stop=b,
                       dtype="float32", always_2d=True)
    import io
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _target_wav(run_dir: Path, cal_item_id: str, opt_idx: int):
    """Blind-mapped G5A target-focus wav: OPTION_i's role (baseline/
    candidate) resolves to BASELINE_TARGET/CANDIDATE_TARGET on disk —
    the page keeps showing A/B; role names never leak to the UI."""
    mpath = calib_dir(run_dir) / "items" / cal_item_id / "manifest.json"
    if not mpath.exists():
        return None
    man = json.loads(mpath.read_text(encoding="utf-8"))
    cal = man.get("calibration") or {}
    oid = f"OPTION_{opt_idx}"
    base_id, cand_id = cal.get("baseline_option"), cal.get("candidate_role")
    name = ("BASELINE_TARGET.wav" if oid == base_id
            else "CANDIDATE_TARGET.wav" if oid == cand_id else None)
    if name is None:
        return None
    p = calib_dir(run_dir) / "items" / cal_item_id / name
    return p if p.exists() else None


def _items_payload(run_dir: Path) -> dict:
    st = rebuild_calibration_state(run_dir)
    plan_p = calib_dir(run_dir) / "plan.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8")) \
        if plan_p.exists() else {"items": []}
    items = []
    for it in plan["items"]:
        rev = current_decision(run_dir, it["repair_id"])
        region = None
        mpath = calib_dir(run_dir) / "items" / it["cal_item_id"] \
            / "manifest.json"
        if mpath.exists():
            man = json.loads(mpath.read_text(encoding="utf-8"))
            region = man.get("target_group", {}).get("region")
        items.append({
            "cal_item_id": it["cal_item_id"],
            "repair_id": it["repair_id"],
            "note_id": it["note_id"], "type": it["type"],
            "region": region,
            "phrase": it["phrase"], "phrase_key": it["phrase_key"],
            "package_state": it["package_state"],
            "outcome": rev["outcome"] if rev else None,
        })
    return {**st, "items": items}


def serve(run_dir: Path, port: int = 8123,
          open_browser: bool = True) -> None:
    run_dir = Path(run_dir)

    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj):
            self._send(code, json.dumps(obj).encode("utf-8"),
                       "application/json")

        def _wav(self, path: Path):
            if not path.exists():
                return self._json(404, {"error": "missing_file"})
            self._send(200, path.read_bytes(), "audio/wav")

        def do_GET(self):
            u = urlparse(self.path).path.strip("/").split("/")
            if u == [""]:
                return self._send(200, _PAGE.encode("utf-8"), "text/html")
            if u == ["api", "state"]:
                return self._json(200, _items_payload(run_dir))
            if u[:2] == ["audio", "item"] and len(u) == 4:
                if u[3] in ("OPTION_0.wav", "OPTION_1.wav"):
                    return self._wav(calib_dir(run_dir) / "items"
                                     / u[2] / u[3])
                if u[3] in ("TARGET_0.wav", "TARGET_1.wav"):
                    p = _target_wav(run_dir, u[2],
                                    int(u[3][6]))
                    if p is not None:
                        return self._wav(p)
                    return self._json(404,
                                      {"error": "missing_target_focus"})
            if u[:2] == ["audio", "phrase"] and len(u) == 4:
                if u[3] in _ALLOWED[2:]:
                    return self._wav(calib_dir(run_dir) / "phrases"
                                     / u[2] / u[3])
            if u[:2] == ["audio", "focus"] and len(u) == 4:
                if u[3] in ("mix.wav", "vocal.wav"):
                    w = _focus_wav(run_dir, u[2], u[3][:-4])
                    if w is not None:
                        return self._send(200, w, "audio/wav")
                return self._json(404, {"error": "missing_focus"})
            return self._json(404, {"error": "not_found"})

        def do_POST(self):
            u = urlparse(self.path).path.strip("/").split("/")
            if u == ["api", "decide"]:
                n = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                    rev = decide(run_dir, body["cal_item_id"],
                                 body["choice"])
                except Exception as e:
                    return self._json(400, {"error": str(e)})
                return self._json(
                    200, {"decision": rev,
                          "state": _items_payload(run_dir)})
            return self._json(404, {"error": "not_found"})

        def log_message(self, *a):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{port}"
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    print(f"calibration web UI → {url}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
