"""重新生成接触表：每页 12 个单元（3x4），共 30 页，覆盖 349 个单元。

每格保留原图的坐标轴与音符标签，足以判断：
  是否有垂直悬崖、是否深 V、音符落点是否清楚、字腹是否有起伏。
"""
import sys, json, io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
ATLAS = NEW/'compiled'/'execution-review'/'atlas'
OUT = NEW/'evaluation'/'contact_sheets'
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob('sheet_*.png'):
    f.unlink()

sheet = json.load(io.open(NEW/'evaluation'/'visual_review_sheet.json', encoding='utf-8'))
units = [u for page in sheet['pages'] for u in page]
print(f'units {len(units)}')

PER_PAGE = 12
COLS, ROWS = 3, 4
CELL_W, CELL_H = 700, 500
PAD = 6

try:
    font = ImageFont.truetype("arial.ttf", 16)
except Exception:
    font = ImageFont.load_default()

pages = [units[i:i+PER_PAGE] for i in range(0, len(units), PER_PAGE)]
print(f'pages {len(pages)}')

for pi, page in enumerate(pages):
    W = COLS*CELL_W + (COLS+1)*PAD
    H = ROWS*CELL_H + (ROWS+1)*PAD
    canvas = Image.new('RGB', (W, H), 'white')
    draw = ImageDraw.Draw(canvas)
    for ci, u in enumerate(page):
        p = ATLAS/u['atlas']
        if not p.is_file():
            continue
        im = Image.open(p).convert('RGB')
        im.thumbnail((CELL_W-4, CELL_H-22))
        col, row = ci % COLS, ci // COLS
        x0 = PAD + col*(CELL_W+PAD)
        y0 = PAD + row*(CELL_H+PAD)
        canvas.paste(im, (x0+2, y0+20))
        tag = f"{ci+1}.{u['id']} {u['lyric']} t{u['tone']}"
        draw.text((x0+2, y0+2), tag, fill=(0,0,0), font=font)
    canvas.save(OUT/f'sheet_{pi+1:02d}.png', optimize=True)

print(f'written {len(list(OUT.glob("sheet_*.png")))} sheets')
idx = dict(schema_version=1, per_page=PER_PAGE, total_units=len(units),
           pages=[dict(page=i+1, units=[u['id'] for u in pg]) for i,pg in enumerate(pages)])
(OUT/'index.json').write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote index.json')
