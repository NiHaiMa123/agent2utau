import sys, difflib
sys.stdout.reconfigure(encoding='utf-8')

a = open('runs/production/nianlun-v3-20261029/compiled/project.ustx', encoding='utf-8').read().splitlines()
b = open('runs/production/nianlun-v3-20261029/compiled/project_voiced.ustx', encoding='utf-8').read().splitlines()
print(f'lines: good={len(a)} bad={len(b)}')
d = list(difflib.unified_diff(a, b, 'project', 'voiced', n=1, lineterm=''))
print(f'diff lines: {len(d)}')
for line in d[:80]:
    print(line[:220])
