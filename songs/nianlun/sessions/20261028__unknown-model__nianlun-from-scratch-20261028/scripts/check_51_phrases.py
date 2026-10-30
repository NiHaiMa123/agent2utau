import json
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
game = json.loads((obs_dir / "game.json").read_text(encoding="utf-8"))
voiced = [n for n in game["notes"] if n["voiced"]]

phrases_52 = [
    # Verse 1 (8)
    ("p00", "圆圈勾勒成指纹", "yuan quan gou le cheng zhi wen", 18.0, 21.8),
    ("p01", "印在我的嘴唇", "yin zai wo de zui chun", 21.8, 25.0),
    ("p02", "回忆苦涩的吻痕", "hui yi ku se de wen hen", 25.0, 28.2),
    ("p03", "是树根", "shi shu gen", 28.2, 31.2),
    ("p04", "春去秋来的茂盛", "chun qu qiu lai de mao sheng", 31.2, 34.8),
    ("p05", "却遮住了黄昏", "que zhe zhu le huang hun", 34.8, 38.0),
    ("p06", "寒夜剩我一个人", "han ye sheng wo yi ge ren", 38.0, 41.0),
    ("p07", "等清晨", "deng qing chen", 41.0, 44.0),
    # Pre-Chorus 1 (8)
    ("p08", "世间最毒的仇恨", "shi jian zui du de chou hen", 44.0, 47.6),
    ("p09", "是永远却无分", "shi yong yuan que wu fen", 47.6, 50.8),
    ("p10", "可惜你从未心疼", "ke xi ni cong wei xin teng", 50.8, 54.0),
    ("p11", "我的恨", "wo de hen", 54.0, 56.8),
    ("p12", "荒草丛生的青春", "huang cao cong sheng de qing chun", 56.8, 60.5),
    ("p13", "倒也过的安稳", "dao ye guo de an wen", 60.5, 63.8),
    ("p14", "代替你陪着我的", "dai ti ni pei zhe wo de", 63.8, 67.0),
    ("p15", "是年轮", "shi nian lun", 67.0, 70.0),
    # Chorus 1 (6)
    ("p16", "数着一圈圈年轮", "shu zhe yi quan quan nian lun", 70.0, 73.2),
    ("p17", "我认真将心事都封存", "wo ren zhen jiang xin shi dou feng cun", 73.2, 78.0),
    ("p18", "密密麻麻是我的自尊", "mi mi ma ma shi wo de zi zun", 78.0, 82.8),
    ("p19", "修改一次次离分", "xiu gai yi ci ci li fen", 82.8, 86.0),
    ("p20", "我承认曾幻想过永恒", "wo cheng ren ceng huan xiang guo yong heng", 86.0, 91.0),
    ("p21", "可惜从没人陪我演这剧本", "ke xi cong mei ren pei wo yan zhe ju ben", 91.0, 97.5),
    # Verse 2 (8)
    ("p22", "圆圈勾勒成指纹", "yuan quan gou le cheng zhi wen", 106.0, 109.2),
    ("p23", "印在我的嘴唇", "yin zai wo de zui chun", 109.2, 112.4),
    ("p24", "回忆苦涩的吻痕", "hui yi ku se de wen hen", 112.4, 115.6),
    ("p25", "是树根", "shi shu gen", 115.6, 118.4),
    ("p26", "春去秋来的茂盛", "chun qu qiu lai de mao sheng", 118.4, 122.0),
    ("p27", "却遮住了黄昏", "que zhe zhu le huang hun", 122.0, 125.0),
    ("p28", "寒夜剩我一个人", "han ye sheng wo yi ge ren", 125.0, 128.4),
    ("p29", "等清晨", "deng qing chen", 128.4, 131.2),
    # Pre-Chorus 2 (8)
    ("p30", "世间最毒的仇恨", "shi jian zui du de chou hen", 131.2, 135.0),
    ("p31", "是永远却无分", "shi yong yuan que wu fen", 135.0, 138.2),
    ("p32", "可惜你从未心疼", "ke xi ni cong wei xin teng", 138.2, 141.4),
    ("p33", "我的恨", "wo de hen", 141.4, 144.2),
    ("p34", "荒草丛生的青春", "huang cao cong sheng de qing chun", 144.2, 147.8),
    ("p35", "倒也过的安稳", "dao ye guo de an wen", 147.8, 151.0),
    ("p36", "代替你陪着我的", "dai ti ni pei zhe wo de", 151.0, 154.4),
    ("p37", "是年轮", "shi nian lun", 154.4, 157.4),
    # Chorus 2 (6)
    ("p38", "数着一圈圈年轮", "shu zhe yi quan quan nian lun", 157.4, 160.6),
    ("p39", "我认真将心事都封存", "wo ren zhen jiang xin shi dou feng cun", 160.6, 165.4),
    ("p40", "密密麻麻是我的自尊", "mi mi ma ma shi wo de zi zun", 165.4, 170.2),
    ("p41", "修改一次次离分", "xiu gai yi ci ci li fen", 170.2, 173.4),
    ("p42", "我承认曾幻想过永恒", "wo cheng ren ceng huan xiang guo yong heng", 173.4, 178.4),
    ("p43", "可惜从没人陪我演这剧本", "ke xi cong mei ren pei wo yan zhe ju ben", 178.4, 185.0),
    # Chorus 3 (6)
    ("p44", "一圈圈年轮", "yi quan quan nian lun", 206.5, 210.2),
    ("p45", "我认真将心事都封存", "wo ren zhen jiang xin shi dou feng cun", 210.2, 215.0),
    ("p46", "密密麻麻是我的自尊", "mi mi ma ma shi wo de zi zun", 215.0, 220.0),
    ("p47", "修改一次次离分", "xiu gai yi ci ci li fen", 220.0, 223.0),
    ("p48", "我承认曾幻想过永恒", "wo cheng ren ceng huan xiang guo yong heng", 223.0, 228.0),
    ("p49", "可惜从没人陪我演这剧本", "ke xi cong mei ren pei wo yan zhe ju ben", 228.0, 234.5),
    # Outro (1)
    ("p50", "可惜从没人陪我演这剧本", "ke xi cong mei ren pei wo yan zhe ju ben", 234.5, 243.0),
]

print(f"Total phrases: {len(phrases_52)}")
for pid, text, py, t0, t1 in phrases_52:
    notes_in = [n for n in voiced if t0 <= n["start"] < t1]
    n_chars = len(text)
    n_py = len(py.split())
    assert n_chars == n_py, f"Mismatch in {pid}: {text} ({n_chars}) vs {py} ({n_py})"
    print(f"{pid}: {text:14s} ({n_chars:2d} chars, {len(notes_in):2d} notes) [{t0:5.1f}-{t1:5.1f}s]")
