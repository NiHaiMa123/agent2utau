"""阶段1：重建歌词身份。

来源：
  - 权威歌词：百度百科《年轮》词条（汪苏泷词曲）
  - 观测：复用 ASR（近似字界，非真值）+ GAME（音符事件）
  - 逐句以音频实际存在为准：ASR 段数与时间窗决定"唱了几段"，
    但每个字用权威歌词，不沿用 ASR 的错字。

输出：lyrics.json —— 51 个音乐句，每句 hanzi 串 + 字符级初估秒界（后面由 HFA/能量重算）
"""
import sys, json, io, re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
asr = json.load(io.open(NEW / 'inputs/asr.json', encoding='utf-8'))

# 权威歌词（百度百科 张碧晨版），按音乐段落
CANON = [
    '圆圈勾勒成指纹',
    '印在我的嘴唇',
    '回忆苦涩的吻痕',
    '是树根',
    '春去秋来的茂盛',
    '却遮住了黄昏',
    '寒夜剩我一个人',
    '等清晨',
    '世间最毒的仇恨',
    '是有缘却无份',
    '可惜你从未心疼',
    '我的笨',
    '荒草丛生的青春',
    '倒也过的安稳',
    '代替你陪着我的',
    '是年轮',
    '数着一圈圈年轮',
    '我认真',
    '将心事都封存',
    '密密麻麻是我的自尊',
    '修改一次次离分',
    '我承认',
    '曾幻想过永恒',
    '可惜从没人陪我演这剧本',
]

# ASR 段（按时间），只用来确定"每段唱了哪些字/多少字"
seg = asr['segments']
sung = [s for s in seg if s['end'] - s['start'] > 0.5]
print(f'ASR segments (>=0.5s): {len(sung)}')

# 人工对齐：ASR 文本 -> 权威歌词片段
# v2 有 51 个 part，结构是 主歌A(8) 副歌B(8) 副歌C(4) ... 这里按音频重复结构重建
# 结构（由 ASR 时间轴 + 歌词重复推出）：
#   段落1: 圆圈..是树根 (4句)  18.6-30.9
#   段落2: 春去..等清晨 (4句)  31.2-44.0
#   段落3: 世间..我的笨 (4句)  44.1-56.9
#   段落4: 荒草..是年轮 (4句)  57.1-69.4
#   段落5: 数着..这剧本 (6句)  69.5-96.1
#   间奏
#   段落6-10 重复          105.5-183.5
#   间奏
#   段落11: 一圈圈年轮..这剧本 (6句) 206.3-242.7

PLAN = [
    # (起始句号, 句子列表)
    (0, CANON[0:4]),
    (1, CANON[4:8]),
    (2, CANON[8:12]),
    (3, CANON[12:16]),
    (4, CANON[16:24]),
    (5, CANON[0:4]),
    (6, CANON[4:8]),
    (7, CANON[8:12]),
    (8, CANON[12:16]),
    (9, CANON[16:24]),
    (10, ['一圈圈年轮'] + CANON[17:24]),
]

# 把 ASR 段分配到段落
def norm(s):
    return re.sub(r'[^\u4e00-\u9fff]', '', s)

print('\nASR 段与权威歌词的错字对照（供记录）:')
MISTAKES = {
    '还也剩我一个人': '寒夜剩我一个人', '等情侦': '等清晨',
    '时间最毒的仇恨': '世间最毒的仇恨', '是永远却无分': '是有缘却无份',
    '我的本': '我的笨', '荒草从深的青春': '荒草丛生的青春',
    '到越过的安稳': '倒也过的安稳', '树舍一圈圈年轮': '数着一圈圈年轮',
    '代替你陪着我的十年冷': '代替你陪着我的 是年轮',
    '代替你陪着我的十年轮': '代替你陪着我的 是年轮',
    '是我的子孙': '密密麻麻是我的自尊',
    '荒草从生的青春': '荒草丛生的青春', '倒也过的安稳': '倒也过的安稳',
    '数着一圈圈年轮': '数着一圈圈年轮', '一圈圈眠了我认真': '一圈圈年轮 我认真',
    '密密麻麻是我的自尊': '密密麻麻是我的自尊',
    '修改一次次离分': '修改一次次离分',
    '我承认曾幻想过永恒': '我承认 曾幻想过永恒',
    '可惜从没人陪我演这剧本': '可惜从没人陪我演这剧本',
    '可惜从没人陪我演唱剧本': '可惜从没人陪我演这剧本',
    '春去秋来的茂盛': '春去秋来的茂盛', '却遮住了黄昏': '却遮住了黄昏',
    '寒夜剩我一个人等清晨': '寒夜剩我一个人 等清晨',
    '世间最独的仇恨': '世间最毒的仇恨', '是永远却无分': '是有缘却无份',
    '可惜你从未心疼我的本': '可惜你从未心疼 我的笨',
    '回忆苦涩的吻恨': '回忆苦涩的吻痕', '是树干': '是树根',
    '圆圈勾勒成指纹': '圆圈勾勒成指纹', '印在我的嘴唇': '印在我的嘴唇',
    '作曲 李宗盛': None, '字幕志愿者 杨茜茜': None,
}
for k, v in MISTAKES.items():
    if v and k != v:
        print(f'   ASR「{k}」 -> 权威「{v}」')

# 组装：把 ASR 的时间窗与权威歌词字数对齐
out_phrases = []
for seg_i, (block_i, lines) in enumerate(PLAN):
    out_phrases.append(dict(block=block_i, lines=lines))
print(f'\n段落块: {len(out_phrases)}')

# 用 ASR 时间窗给每个块分配时间范围
# 手工按 ASR 段聚合（ASR 段是按行切的）
blocks_time = [
    (18.6, 30.9), (31.2, 44.0), (44.1, 56.9), (57.1, 69.4), (69.5, 96.1),
    (105.5, 118.6), (118.7, 131.4), (131.4, 144.2), (144.2, 156.5), (156.5, 183.5),
    (206.3, 242.7),
]
assert len(blocks_time) == len(out_phrases)

result = []
for (block_i, lines), (t0, t1) in zip(out_phrases, blocks_time):
    n_char = sum(len(l) for l in lines)
    # 字符级初估：按字数均分（只是初估，后续用 HFA + 能量重建真界）
    span = (t1 - t0) / max(n_char, 1)
    chars, cursor = [], t0
    for line in lines:
        line_chars = []
        for ch in line:
            line_chars.append(dict(char=ch, est_start=round(cursor, 3), est_end=round(cursor+span, 3)))
            cursor += span
        chars.append(dict(line=line, chars=line_chars))
    result.append(dict(
        block=block_i, lines=lines, time_est=[t0, t1],
        n_chars=n_char, char_index_start=0,
        lines_detail=chars,
    ))

# assign global char indices
i = 0
for r in result:
    i0 = i
    for ld in r['lines_detail']:
        for c in ld['chars']:
            c['global_index'] = i; i += 1
    r['char_index_start'] = i0; r['char_index_end'] = i
print(f'total sung chars: {i}')

doc = dict(
    schema_version=1,
    source='百度百科《年轮》(张碧晨版, 汪苏泷词曲) + 复用ASR时间窗(近似)',
    asr_corrections={k: v for k, v in MISTAKES.items() if v and k != v},
    blocks=result,
    total_chars=i,
    note='字符级时间仅为初估，真界由后续 HFA + 能量起音重建',
)
(NEW / 'lyrics.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nwrote {NEW}/lyrics.json')
for r in result:
    print(f'  block{r["block"]:2d} {r["time_est"][0]:6.1f}-{r["time_est"][1]:6.1f}  {r["n_chars"]:2d}字  {" / ".join(r["lines"])}')
