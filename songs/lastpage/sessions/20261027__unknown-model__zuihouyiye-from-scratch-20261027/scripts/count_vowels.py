import json

phones = json.loads(open('runs/production/zuihouyiye-from-scratch-20261027/design/baseline_phones.json', encoding='utf-8').read())
print("Total parts in baseline_phones:", len(phones['parts']))
for pi, p in enumerate(phones['parts']):
    vowels = [ph for phr in p['phrases'] for ph in phr['phones'] if not ph['phoneme'].startswith('zh/') and ph['phoneme'] not in ('AP', 'SP')]
    all_vowels = [ph for phr in p['phrases'] for ph in phr['phones'] if any(v in ph['phoneme'] for v in ('a','e','i','o','u','v')) and ph['phoneme'] not in ('AP', 'SP')]
    print(f"Part {pi:02d}: notes={len(p['notes'])} vowels={len(all_vowels)} phones={len(p['phrases'][0]['phones'])}")
