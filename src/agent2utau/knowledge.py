"""Explicit, SHA-bound knowledge retrieval and Agent decision receipts.

Reads public knowledge records only. It neither chooses doses nor executes media.
"""
import csv
import json
from pathlib import Path
from .resources.config import REPO_ROOT
from .openutau.ustx import sha256

KNOW=REPO_ROOT/'docs/knowledge/acoustic-manifestations-20261009'
CATALOGUE=KNOW/'active-knowledge-sources.json'

def _read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def _public(name):
    p=(REPO_ROOT/name).resolve()
    if not (p.is_relative_to(REPO_ROOT/'docs/knowledge') or p.is_relative_to(REPO_ROOT/'docs/reports')) or not p.is_file():
        raise ValueError(f'Knowledge source must be an existing public document: {name}')
    return p

def _ref(p):return dict(path=Path(p).relative_to(REPO_ROOT).as_posix(),sha256=sha256(p))

def _collect(config,entities,parameters,responses,absence_reason=''):
    table=_public(config['table1']);param=_public(config['parameters']);bindings=[_ref(table),_ref(param)]
    t=_read(table)
    with param.open(encoding='utf-8-sig',newline='') as f:pr=list(csv.DictReader(f))
    by_id={r['id']:dict(kind='entity',record=r) for r in t['entities']}
    by_id.update({r['id']:dict(kind='parameter',record=r) for r in pr})
    for name in config['response_indices']:
        path=_public(name);bindings.append(_ref(path))
        for r in _read(path)['rows']:
            by_id[r['id']]=dict(kind='response',record=r)
    for name in config.get('response_packets',[]):
        path=_public(name);bindings.append(_ref(path));r=_read(path)
        item=r.get('table2_supplement',r);ident=item['record_id']
        by_id[ident]=dict(kind='response',record=dict(id=ident,source=_ref(path),source_record=item))
    selected=[]
    for kind,ids in [('entity',entities),('parameter',parameters),('response',responses)]:
        for ident in ids:
            if ident not in by_id or by_id[ident]['kind']!=kind:raise ValueError(f'Unknown {kind} ID: {ident}')
            item=by_id[ident];selected.append(dict(id=ident,**item))
            if kind=='response':
                r=item['record']
                for b in [r['source'],*r.get('feedback_sources',[])]:
                    p=_public(b['path'])
                    if sha256(p)!=b['sha256']:raise ValueError(f'Changed response source: {b["path"]}')
                    bindings.append(b)
    if not entities or not parameters:raise ValueError('Select at least one table1 entity and parameter')
    if not responses and not absence_reason.strip():raise ValueError('No matching response: explicitly record evidence absence')
    if len({r['id'] for r in selected})!=len(selected):raise ValueError('Duplicate knowledge ID')
    return selected,list({r['path']:r for r in bindings}.values())

def collect_context(entities,parameters,responses,absence_reason='',catalogue_path=CATALOGUE):
    path=Path(catalogue_path);config=_read(path)
    rows,bindings=_collect(config,entities,parameters,responses,absence_reason)
    return dict(schema_version=1,registry_snapshot=dict(path=str(path),sha256=sha256(path),config=config),
        request=dict(entities=entities,parameters=parameters,responses=responses,absence_reason=absence_reason),
        records=rows,sources=bindings,automatic_parameter_selection=False,
        records_are_conditional_evidence=True,general_rule_validated=False)

def validate_context(packet,decisions):
    if packet.get('schema_version')!=1:raise ValueError('Unknown knowledge context schema')
    for b in packet['sources']:
        if sha256(_public(b['path']))!=b['sha256']:raise ValueError(f'Changed knowledge source: {b["path"]}')
    q=packet['request'];rows,bindings=_collect(packet['registry_snapshot']['config'],**q)
    if rows!=packet['records'] or bindings!=packet['sources']:raise ValueError('Knowledge records or bindings do not match source documents')
    ids=[r['id'] for r in rows]
    if len(decisions)!=len(ids) or {d.get('id') for d in decisions}!=set(ids):raise ValueError('Decide once for every retrieved knowledge ID')
    for d in decisions:
        if d.get('decision') not in ['use','reject','extrapolate','keep_unknown']:raise ValueError('Unknown knowledge decision')
        for k in ['reason','condition_match','limitations']:
            if not isinstance(d.get(k),str) or not d[k].strip():raise ValueError(f'Missing decision {k}')
        if d.get('general_rule_claim',False):raise ValueError('This receipt cannot declare a general rule validated')
    return dict(status='passed',record_ids=ids,decisions=decisions,sources=bindings,
        validation='source identity and explicit decision coverage; not evidence of musical correctness',
        automatic_parameter_selection=False,general_rule_validated=False)

def check_plan_knowledge(plan,plan_path):
    spec=plan.get('knowledge_context')
    if not isinstance(spec,dict) or set(spec)!={'path','sha256','decisions'}:raise ValueError('Plan requires SHA-bound knowledge_context and decisions')
    path=Path(spec['path']);path=(Path(plan_path).parent/path).resolve() if not path.is_absolute() else path.resolve()
    if sha256(path)!=spec['sha256']:raise ValueError('Changed knowledge context packet')
    packet=_read(path);receipt=validate_context(packet,spec['decisions']);receipt['packet_sha256']=spec['sha256']
    return packet,receipt
