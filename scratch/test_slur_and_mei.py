import copy
import json
from pathlib import Path
from agent2utau.openutau.ustx import load_ustx, save_ustx
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

cfg = load_config()
score_path = Path("runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx")
doc = load_ustx(score_path)

test_doc = copy.deepcopy(doc)

# 1. In Part 28 and 34, fix '没' to '没[m ei]'
for pi in [28, 34]:
    for n in test_doc['voice_parts'][pi]['notes']:
        if n.get('lyric') == '没':
            n['lyric'] = '没[m ei]'
            print(f"Part {pi}: changed '没' to '没[m ei]'")

# 2. In Part 18, 24, 25, 31, 37, change bogus middle-of-phrase APs to '+'
# Part 18: note 8 was AP(64) between '一' and '次'
test_doc['voice_parts'][18]['notes'][8]['lyric'] = '+'
test_doc['voice_parts'][18]['notes'][8]['tone'] = test_doc['voice_parts'][18]['notes'][7]['tone']  # tone 63

# Part 24: note 10 was AP(59) between '零' and '的'
test_doc['voice_parts'][24]['notes'][10]['lyric'] = '+'
test_doc['voice_parts'][24]['notes'][10]['tone'] = test_doc['voice_parts'][24]['notes'][9]['tone']  # tone 59

# Part 25: note 4 was AP(64), note 8 was AP(64)
test_doc['voice_parts'][25]['notes'][4]['lyric'] = '+'
test_doc['voice_parts'][25]['notes'][4]['tone'] = test_doc['voice_parts'][25]['notes'][3]['tone']  # tone 68
test_doc['voice_parts'][25]['notes'][8]['lyric'] = '+'
test_doc['voice_parts'][25]['notes'][8]['tone'] = test_doc['voice_parts'][25]['notes'][7]['tone']  # tone 68

# Part 31: note 5 was AP(59) between '我' and '把'
test_doc['voice_parts'][31]['notes'][5]['lyric'] = '+'
test_doc['voice_parts'][31]['notes'][5]['tone'] = test_doc['voice_parts'][31]['notes'][4]['tone']  # tone 64

# Part 37: note 5 was AP(59) between '我' and '把'
test_doc['voice_parts'][37]['notes'][5]['lyric'] = '+'
test_doc['voice_parts'][37]['notes'][5]['tone'] = test_doc['voice_parts'][37]['notes'][4]['tone']  # tone 64

test_ustx = Path("scratch/test_modified_score.ustx")
save_ustx(test_doc, test_ustx)

# Run export-phonemes on test_modified_score.ustx
out_phones = Path("scratch/test_modified_phones.json")
rep = run_bridge(cfg, ['export-phonemes', '--project', str(test_ustx.resolve()), '--out', str(out_phones.resolve())])
print("export-phonemes result:", rep.get('ok'), rep.get('errors'))

# Inspect phonemes of Part 18, 24, 25, 28, 31, 34, 37
ph_data = json.loads(out_phones.read_text(encoding='utf-8'))
for pi in [18, 24, 25, 28, 31, 34, 37]:
    p = ph_data['parts'][pi]
    symbols = [x['phoneme'] for x in p['phrases'][0]['phones']]
    print(f"Part {pi} phonemes:", symbols)
