"""Validate explicit listening labels without fitting or repairing a song."""
import argparse
import json
from pathlib import Path

from ..openutau.ustx import sha256

AXES = ('firmness','airiness','proximity','loudness','naturalness','timbre')
CHOICES = {k:{'A','B','same','uncertain'} for k in AXES}
CHOICES['timbre']={'same','different','uncertain'}


def _read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def validate_partition(samples):
    """All interventions/duplicates of a context stay in one data split."""
    ids=set();groups={};audio_splits={}
    for s in samples:
        if (s['id'] in ids or s['split'] not in {'development','holdout'}
                or not s['context_id']):
            raise ValueError('Invalid sample identity/split')
        ids.add(s['id']);groups.setdefault(s['context_id'],set()).add(s['split'])
        if s.get('audio',{}).get('sha256'):
            audio_splits.setdefault(s['audio']['sha256'],set()).add(s['split'])
    if any(len(v)!=1 for v in groups.values()):
        raise ValueError('Context descendants leak across partitions')
    if any(len(v)!=1 for v in audio_splits.values()):
        raise ValueError('Identical audio leaks across partitions')
    return dict(samples=len(ids),contexts=len(groups))


def validate_ratings(catalog_path,packet_path,ratings_path,require_complete=False):
    catalog_path=Path(catalog_path).resolve();packet_path=Path(packet_path).resolve()
    catalog=_read(catalog_path);packet=_read(packet_path);ratings=_read(ratings_path)
    if set(packet)!={'schema_version','catalog','pairs','instructions'} or packet['schema_version']!=1:
        raise ValueError('Unsupported listening packet')
    if packet['catalog']!={'path':str(catalog_path),'sha256':sha256(catalog_path)}:
        raise ValueError('Changed sample catalog')
    partition=validate_partition(catalog['samples']);samples={s['id']:s for s in catalog['samples']}
    for sample in samples.values():
        path=Path(sample['audio']['path'])
        if not path.is_absolute() or sha256(path)!=sample['audio']['sha256']:
            raise ValueError('Changed audio sample')
    if (set(ratings)!={'schema_version','packet_sha256','rater_id','ratings'}
            or ratings['schema_version']!=1 or ratings['packet_sha256']!=sha256(packet_path)):
        raise ValueError('Labels do not bind this listening order')
    if not isinstance(ratings['rater_id'],str):raise ValueError('Rater identity must be text')
    pairs={}
    for p in packet['pairs']:
        if (set(p)!={'id','A','B','context_id','split'} or p['id'] in pairs
                or p['A'] not in samples or p['B'] not in samples):
            raise ValueError('Invalid pair identity')
        a,b=samples[p['A']],samples[p['B']]
        if any(s['context_id']!=p['context_id'] or s['split']!=p['split'] for s in [a,b]):
            raise ValueError('Pair context/partition mismatch')
        pairs[p['id']]=p
    found=set();complete=0;pending=0;observed=[]
    for row in ratings['ratings']:
        if set(row)!={'pair_id','answers','comment'} or row['pair_id'] not in pairs or row['pair_id'] in found:
            raise ValueError('Unknown/duplicate listening label')
        found.add(row['pair_id'])
        if set(row['answers'])!=set(AXES) or not isinstance(row['comment'],str):
            raise ValueError('Separate listening axes required')
        for key,answer in row['answers'].items():
            if answer is not None and answer not in CHOICES[key]:raise ValueError('Invalid perceptual answer')
        ready=all(v is not None for v in row['answers'].values())
        if ready:complete+=1
        else:pending+=1
        observed.append(dict(**row,split=pairs[row['pair_id']]['split'],status='rated' if ready else 'pending'))
    if found!=set(pairs):raise ValueError('Missing listening pairs')
    if require_complete and (pending or not isinstance(ratings['rater_id'],str) or not ratings['rater_id'].strip()):
        raise ValueError('Listening labels/rater still pending')
    return dict(schema_version=1,packet_sha256=sha256(packet_path),catalog_sha256=sha256(catalog_path),
                partition=partition,rater_id=ratings['rater_id'],rater_status='provided' if ratings['rater_id'].strip() else 'pending',
                completed_pairs=complete,pending_pairs=pending,
                ratings=observed,perceptual_scale_validated=False,automatic_song_pass=False,
                boundary='Validated label provenance only; no threshold fitting, transitive acceptance or isolated-vowel-to-phrase equivalence')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['catalog','packet','ratings','out']:p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--require-complete',action='store_true');a=p.parse_args(argv)
    result=validate_ratings(a.catalog,a.packet,a.ratings,a.require_complete)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps(dict(completed=result['completed_pairs'],pending=result['pending_pairs'])))
    return 0


if __name__=='__main__':raise SystemExit(main())
