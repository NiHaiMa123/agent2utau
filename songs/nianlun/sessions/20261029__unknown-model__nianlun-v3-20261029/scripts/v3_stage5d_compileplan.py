"""阶段5d：knowledge_context（显式检索 + 逐ID决策）+ freeze intent lock + 完整 compile plan。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.knowledge import collect_context
from agent2utau.openutau.ustx import sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'; SCORE = NEW/'score'/'v3_score.ustx'
SRC = NEW/'inputs/stems/vocals.wav'

# 与本次任务直接相关：
#  PER:S1 支撑/实的听感、EVT:P2 慢趋势、EVT:P3 换音事件、ACO:P4 F0周期调制
#  ACO:T2 音素时长、EVT:T6 释放/收声、EVT:T7 呼吸声事件、EVT:T9 间隙/静音组织
#  参数：C01.01 音符tone、C03.01 PITD、C10.01 DYN、C11.01 VOIC、C12.01 BREC、C13.01 TENC
ENT = ['PER:S1', 'EVT:P2', 'EVT:P3', 'ACO:P4', 'ACO:T2', 'EVT:T6', 'EVT:T7', 'EVT:T9']
PAR = ['PARAM:C01.01', 'PARAM:C03.01', 'PARAM:C10.01',
       'PARAM:C11.01', 'PARAM:C12.01', 'PARAM:C13.01']
RESP = ['RESP-001']

pkt = collect_context(ENT, PAR, RESP, absence_reason='')
out = D/'knowledge_context.json'
out.write_text(json.dumps(pkt, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'knowledge context: {out}')
print(f'  records {len(pkt["records"])}, sources {len(pkt["sources"])}')
for r in pkt['records']:
    print(f"   {r['id']:12s} ({r['kind']})")

# per-ID decisions (Skill: 每个取回ID各一条 use/reject/extrapolate/keep_unknown)
decisions = []
for r in pkt['records']:
    i = r['id']
    if i == 'PER:S1':
        d = dict(decision='use', reason='整曲虚实一致性是本次目标之一；用于判断发声层要不要做逐句设计',
                 condition_match='同声库(YousaV1.65c)、同曲、中文', limitations='听感标签来自其它曲；本曲未试听')
    elif i == 'EVT:P2':
        d = dict(decision='use', reason='慢趋势是音高主体设计对象；本次用三段中值+稀疏节点表达',
                 condition_match='通用机制', limitations='慢趋势幅度未在本曲校准')
    elif i == 'EVT:P3':
        d = dict(decision='use', reason='换音事件决定字界与入口设计；用GAME音符+实测三段判断',
                 condition_match='中文流行', limitations='GAME是音符事件不是逐帧F0')
    elif i == 'ACO:P4':
        d = dict(decision='use', reason='F0周期调制用于长音支撑；仅 >=0.42s 且有依据时启用',
                 condition_match='长元音', limitations='检测器下限可能漏掉浅周期')
    elif i == 'ACO:T2':
        d = dict(decision='use', reason='音素时长决定可唱性；设 0.10s 下限并修复碎字',
                 condition_match='当前声库', limitations='最短可唱时长未做听感校准')
    elif i == 'EVT:T6':
        d = dict(decision='use', reason='收声关系用于 release 类字的尾部设计',
                 condition_match='句尾/连唱', limitations='辅音归属未经人耳核对')
    elif i == 'EVT:T7':
        d = dict(decision='use', reason='呼吸事件用于 AP 放置；只用真实静默，不铺满',
                 condition_match='本曲有真实换气', limitations='生理吸气不能由能量确认')
    elif i == 'EVT:T9':
        d = dict(decision='use', reason='间隙组织决定 AP/SP 与句界；用能量+有声段判定',
                 condition_match='本曲', limitations='静默阈值是经验值')
    elif i == 'PARAM:C01.01':
        d = dict(decision='use', reason='音符 tone 是旋律身份；用 GAME/实测中值定，不量化掉半音内精度给 PITD',
                 condition_match='当前 OpenUtau', limitations='整数 tone 仍有 ±50c 量化，余量交 PITD')
    elif i == 'PARAM:C03.01':
        d = dict(decision='use', reason='PITD 承载全部表达曲线；本次为核心输出通道',
                 condition_match='当前工程声明范围', limitations='量化到 5tick 网格')
    elif i == 'PARAM:C10.01':
        d = dict(decision='use', reason='DYN 用于句级强弱，不用来掩盖发声问题',
                 condition_match='当前实现 ×0.1dB', limitations='未做本曲听感校准')
    elif i == 'PARAM:C11.01':
        d = dict(decision='explain_only' if False else 'use',
                 reason='VOIC 用于发声层；100 是零人工增量，正增量需核实声明范围',
                 condition_match='当前声库', limitations='单位不是 dB')
    elif i == 'PARAM:C12.01':
        d = dict(decision='use', reason='BREC 用于气声走向；与 VOIC 不是互为正负旋钮',
                 condition_match='当前声库', limitations='特征变化不等于听感变化')
    elif i == 'PARAM:C13.01':
        d = dict(decision='use', reason='TENC 用于张力支撑；不把高音一律加张力',
                 condition_match='当前声库', limitations='正增量无普遍增响保证')
    else:
        d = dict(decision='keep_unknown', reason='本条为历史DYN接受索引，条件与本曲不同，不直接迁移剂量',
                 condition_match='不同曲/不同段', limitations='旧接受不代表本曲')
    decisions.append(dict(id=i, **d))

# ---------- compile plan ----------
plan_native = json.load(io.open(D/'plan_native.json', encoding='utf-8'))
pitch = json.load(io.open(NAT/'baseline_pitch.json', encoding='utf-8'))

# input hashes
ih = {}
def rel(p):
    try: return str(Path(p).resolve().relative_to(D.resolve()))
    except ValueError: return str(Path(p).resolve())
ih[rel(SCORE)] = sha256(SCORE)
ih[rel(SRC)] = sha256(SRC)

phrases = []
for i, (np_, pl) in enumerate(zip(pitch['phrases'], plan_native['phrases'])):
    phrases.append(dict(part_index=0 if False else None, position=np_['position'], design=pl))

# part_index comes from the native phrase's part; resolve by part_position
doc_parts = None
import yaml
doc = yaml.safe_load(SCORE.read_text(encoding='utf-8'))
pos_to_part = {}
for pi, part in enumerate(doc['voice_parts']):
    pos_to_part[part['position']] = pi
out_ph = []
for np_, pl in zip(pitch['phrases'], plan_native['phrases']):
    pi = pos_to_part.get(np_['part_position'])
    if pi is None:
        raise SystemExit(f"cannot resolve part for part_position {np_['part_position']}")
    out_ph.append(dict(part_index=pi, position=np_['position'], design=pl))

full = dict(schema_version=2, project=rel(SCORE), source_audio=rel(SRC),
            input_hashes=ih, scope='whole_song', phrases=out_ph,
            knowledge_context=dict(path='knowledge_context.json',
                                   sha256=sha256(out),
                                   decisions=decisions))
cp = D/'compile_plan.json'
cp.write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\ncompile plan: {cp}')
print(f'  phrases {len(out_ph)}  input_hashes {list(ih)}')
print('  knowledge decisions:', len(decisions))
