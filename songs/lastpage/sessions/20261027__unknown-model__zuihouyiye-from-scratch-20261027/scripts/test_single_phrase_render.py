import copy
from pathlib import Path
import yaml
import soundfile as sf

# Load compiled v5
ustx_path = Path("runs/production/zuihouyiye-from-scratch-20261027/compiled_v5/project.ustx")
doc = yaml.safe_load(ustx_path.read_text(encoding="utf-8"))

# Create test project with just Part 29
test_doc = copy.deepcopy(doc)
p29 = copy.deepcopy(doc['voice_parts'][29])
test_doc['voice_parts'] = [p29]

out_test_ustx = Path("scratch/test_p29_baseline.ustx")
out_test_ustx.write_text(yaml.safe_dump(test_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

print("Created scratch/test_p29_baseline.ustx")
