"""Forward musical intent and read-only discrimination diagnostics.

These checks can falsify a claimed motion. They cannot certify source truth,
musical taste, voice quality, human listening, or the honesty of an attestation.
No production curve is generated here.
"""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..openutau.ustx import TempoMap, load_ustx
from .execution_review import bound, check_action, exact, inside, interval, read, ref, validate_inventory, write


def text_fields(row, fields):
    if any(not isinstance(row[k], str) or not row[k].strip() for k in fields):
        raise ValueError('Musical intent needs nonempty contextual text')


def validate_brief(path, inventory):
    brief = read(path); inv = validate_inventory(inventory)
    exact(brief, {'schema_version', 'inventory', 'phrases', 'phonation'}, 'musical intent')
    if brief['schema_version'] != 1 or bound(brief['inventory'], Path(path).parent) != Path(inventory).resolve():
        raise ValueError('Musical intent targets another inventory/version')
    units = {u['id']: u for u in inv['units']}; sources = {s['id']: s for s in inv['sources']}
    covered = []; phrase_ids = set(); gesture_ids = set()
    for phrase in brief['phrases']:
        exact(phrase, {'id', 'unit_ids', 'support_s', 'observations', 'intention', 'gestures'}, 'intent phrase')
        text_fields(phrase, ['id', 'intention']); span = interval(phrase['support_s'])
        if phrase['id'] in phrase_ids or not phrase['unit_ids'] or not set(phrase['unit_ids']) <= units.keys():
            raise ValueError('Duplicate phrase or unknown intent unit')
        phrase_ids.add(phrase['id']); covered.extend(phrase['unit_ids'])
        if any(not inside(units[u]['support_s'], span) for u in phrase['unit_ids']):
            raise ValueError('Intent phrase must include complete unit supports')
        observations = set()
        for obs in phrase['observations']:
            exact(obs, {'id', 'source_id', 'source_window_s', 'description', 'reliability'}, 'source observation')
            text_fields(obs, ['id', 'description'])
            if obs['id'] in observations or obs['source_id'] not in sources or sources[obs['source_id']]['role'] != 'source_observation':
                raise ValueError('Observation needs a distinct bound current source observation')
            interval(obs['source_window_s'])
            if obs['reliability'] not in {'observed', 'uncertain', 'unknown'}:
                raise ValueError('Unknown source reliability')
            observations.add(obs['id'])
        gesture_units = set(); unit_spans=defaultdict(list)
        for g in phrase['gestures']:
            exact(g, {'id', 'unit_ids', 'role', 'support_s', 'observation_ids', 'interpretation', 'alternative', 'rejected_because', 'contrast', 'checks'}, 'musical gesture')
            text_fields(g, ['id', 'interpretation', 'alternative', 'rejected_because'])
            if g['id'] in gesture_ids or not g['unit_ids'] or not set(g['unit_ids']) <= set(phrase['unit_ids']):
                raise ValueError('Duplicate gesture or wrong unit identity')
            gesture_ids.add(g['id']); gesture_units.update(g['unit_ids'])
            if g['role'] not in {'arrival', 'body', 'connection', 'release', 'hold', 'unknown'} or not inside(interval(g['support_s']), span):
                raise ValueError('Unsupported gesture role/support')
            for uid in g['unit_ids']:
                a=max(g['support_s'][0],units[uid]['support_s'][0]);b=min(g['support_s'][1],units[uid]['support_s'][1])
                if b<=a:raise ValueError('Gesture does not intersect its declared unit')
                unit_spans[uid].append([a,b])
            if not g['observation_ids'] or not set(g['observation_ids']) <= observations:
                raise ValueError('Gesture needs local source observations, not only file names')
            contrast = g['contrast']; exact(contrast, {'mode', 'shallow_limit_c', 'connection_s', 'reason'}, 'diagnostic contrast')
            text_fields(contrast, ['reason'])
            if contrast['mode'] not in {'must_differ', 'may_match'} or not np.isfinite([contrast['shallow_limit_c'], contrast['connection_s']]).all() or contrast['shallow_limit_c'] <= 0 or contrast['connection_s'] <= 0:
                raise ValueError('Finite positive diagnostic contrast settings required')
            if g['role'] == 'hold' and contrast['mode'] != 'may_match':
                raise ValueError('A purposeful hold may match the diagnostic alternative')
            if not g['checks']:
                raise ValueError('Gesture needs pre-plan observable criteria')
            for c in g['checks']:
                exact(c, {'kind', 'support_s', 'parameters'}, 'intent criterion')
                if c['kind'] not in {'hold', 'range', 'direction', 'landmarks', 'cycles'} or not inside(interval(c['support_s']), g['support_s']):
                    raise ValueError('Intent check must stay in its frozen gesture')
        if gesture_units != set(phrase['unit_ids']):
            raise ValueError('Missing unit musical judgment')
        from .local_views import _covers
        if any(not _covers(unit_spans[u],units[u]['support_s']) for u in phrase['unit_ids']):
            raise ValueError('Musical gestures must cover full units, not a selected tiny window')
    if len(covered) != len(set(covered)) or set(covered) != units.keys():
        raise ValueError('Musical phrases must partition all actual units')
    voice = brief['phonation']; exact(voice, {'baseline', 'target', 'status', 'contexts'}, 'phonation calibration')
    text_fields(voice, ['baseline', 'target'])
    if voice['status'] not in {'unvalidated', 'listening_evidence'}:
        raise ValueError('Unsupported phonation calibration state')
    if voice['status'] == 'listening_evidence' and not voice['contexts']:
        raise ValueError('Calibrated voice needs bound audio/feedback contexts')
    for c in voice['contexts']:
        exact(c, {'unit_ids', 'role', 'audio', 'feedback'}, 'calibration context'); text_fields(c, ['role'])
        if not c['unit_ids'] or not set(c['unit_ids']) <= units.keys():
            raise ValueError('Unknown calibration context units')
        bound(c['audio'], Path(path).parent); bound(c['feedback'], Path(path).parent)
    return brief


def freeze_intent(brief, inventory, plan, out):
    """Record that this tool saw a complete brief while the plan was absent.

    This is a local provenance receipt, not a signed proof of Agent reasoning.
    """
    plan = Path(plan).resolve()
    if Path(out).resolve() in {plan,Path(brief).resolve(),Path(inventory).resolve()}:
        raise ValueError('Intent receipt must have a distinct output path')
    if plan.exists():
        raise ValueError('Freeze musical intent before creating the numeric function plan')
    validate_brief(brief, inventory)
    result = dict(schema_version=1, brief=ref(brief), inventory=ref(inventory), plan_path=str(plan),
                  plan_existed_at_freeze=False, frozen_at=datetime.now(timezone.utc).isoformat(),
                  boundary='Tool-observed order only; not a signed origin or musical-quality proof')
    write(out, result); return result


def validate_lock(lock, inventory, plan):
    obj = read(lock)
    exact(obj, {'schema_version', 'brief', 'inventory', 'plan_path', 'plan_existed_at_freeze', 'frozen_at', 'boundary'}, 'intent lock')
    if obj['schema_version'] != 1 or obj['plan_existed_at_freeze'] is not False or Path(obj['plan_path']).resolve() != Path(plan).resolve() or bound(obj['inventory'], Path(lock).parent) != Path(inventory).resolve():
        raise ValueError('Wrong or retrospective musical intent lock')
    if datetime.fromisoformat(obj['frozen_at']).tzinfo is None:
        raise ValueError('Intent lock requires an explicit time zone')
    brief = bound(obj['brief'], Path(lock).parent)
    return validate_brief(brief, inventory), brief


def structural_audit(plan):
    """Describe repeated geometry without comparing IDs or justification prose."""
    groups = defaultdict(list); zero = count = 0
    if plan is None:
        return dict(status='unknown', groups=[], zero_slope_nodes=0, center_nodes=0)
    for ph in read(plan).get('phrases', []):
        d = ph['design']; nodes = np.asarray(d['center_nodes'], float)
        zero += int(np.count_nonzero(nodes[:, 2] == 0)); count += len(nodes)
        for c in d.get('components', []):
            a, b = c['support_s']; family = c['family']
            if family == 'finite_return':
                # Time-normalized topology, independent of component ID/dose.
                signature = (family, round((c['peak_s']-a)/(b-a)*10), int(np.sign(c['peak_c'])))
            elif family=='oscillation':
                signature = (family, round((c['attack_end_s']-a)/(b-a)*10), round((c['release_start_s']-a)/(b-a)*10))
            else:signature=(family,'unsupported')
            groups[signature].append(dict(part_index=ph['part_index'], position=ph['position'], component_id=c['id'], support_s=c['support_s']))
    repeated = [dict(signature=list(k), occurrences=v) for k, v in groups.items() if len(v)>1]
    findings = []
    if count and zero == count: findings.append('all_center_node_slopes_zero')
    if repeated: findings.append('recurring_time_normalized_structure')
    return dict(status='context_review_required' if findings else 'described', findings=findings,
                groups=repeated, zero_slope_nodes=zero, center_nodes=count,
                boundary='A repeated form or zero slope can be legitimate; this is no variation quota or automatic musical failure')


def score_counterfactual(doc, part_index, times, connection_s):
    """Written centers + uniform short connection, diagnostic only."""
    tm = TempoMap.from_doc(doc); notes = doc['voice_parts'][part_index]['notes']; pos = doc['voice_parts'][part_index]['position']
    starts = np.asarray([tm.tick_to_ms(pos+n['position'])/1000 for n in notes]); tones = np.asarray([n['tone']*100 for n in notes], float)
    if not len(notes): raise ValueError('No score notes for diagnostic')
    indices = np.clip(np.searchsorted(starts, times, side='right')-1, 0, len(notes)-1); center = tones[indices].copy()
    for i in range(1, len(notes)):
        half = min(connection_s/2, (starts[i]-starts[i-1])/2)
        if half<=0: continue
        mask = (times>=starts[i]-half)&(times<=starts[i]+half); u = (times[mask]-starts[i]+half)/(2*half)
        center[mask] = tones[i-1]+(tones[i]-tones[i-1])*(1-np.cos(np.pi*u))/2
    return center


def evaluate_intent(project, inventory, pitch, facts_path, plan, lock=None, critique=None):
    structural = structural_audit(plan)
    result = dict(status='unverified', intent_execution='unknown', discrimination='unknown',
                  agent_judgment='not_supplied', phonation='unvalidated', listening='unknown',
                  musical_quality='unverified', structural=structural, gestures=[], bindings={},
                  boundary='Pre-plan criteria and ablations can falsify a claim, never certify musical taste or voice quality')
    if lock is None:
        result['reason'] = 'Missing forward musical intent; old keep/evidence records are viewing attestations only'
        return result
    brief, path = validate_lock(lock, inventory, plan)
    result['bindings'] = dict(intent_lock=ref(lock), musical_intent=ref(path))
    result['phonation'] = brief['phonation']['status']
    if not pitch:
        result['reason'] = 'No actual native pitch'; return result
    inv = validate_inventory(inventory); units = {u['id']: u for u in inv['units']}; doc = load_ustx(project)
    lines = read(pitch)['phrases']; failures = []; unknown = []; nondiscriminating = []
    for phrase in brief['phrases']:
        for g in phrase['gestures']:
            part_indices = {units[u]['part_index'] for u in g['unit_ids']}
            samples = []
            for pi in part_indices:
                part = doc['voice_parts'][pi]; position = part['position']
                indices={units[u]['phrase_index'] for u in g['unit_ids'] if units[u]['part_index']==pi}
                part_lines=[l for l in lines if l['part_position']==position and l['track_no']==part['track_no']]
                for line in (l for i,l in enumerate(part_lines) if i in indices):
                    t = np.asarray(line['times_ms'], float)/1000; y = np.asarray(line['final_cents'], float)
                    center = score_counterfactual(doc, pi, t, g['contrast']['connection_s'])
                    # Preserve the actual micro-shape, remove large movement.
                    # A shallow actual body remains unchanged: no arbitrary sine
                    # phase can manufacture a discrimination success.
                    shallow = center+np.clip(y-center, -g['contrast']['shallow_limit_c'], g['contrast']['shallow_limit_c'])
                    mask = (t>=g['support_s'][0]-1e-9)&(t<=g['support_s'][1]+1e-9)
                    samples.extend(zip(t[mask], y[mask], shallow[mask]))
            samples = sorted(samples); t = [s[0] for s in samples]
            if len(t)!=len(set(t)):
                raise ValueError('Ambiguous overlapping phrase clocks in musical gesture')
            actual = dict(support_s=g['support_s'], times_s=t, raw_cents=[s[1] for s in samples])
            ablation = dict(actual, raw_cents=[s[2] for s in samples])
            checks = [check_action(dict(c, stage_id=g['id']), actual) for c in g['checks']]
            contrasts = [check_action(dict(c, stage_id=g['id']), ablation) for c in g['checks']]
            realized = all(c['status']=='pass' for c in checks)
            distinguish = any(a['status']=='pass' and b['status']=='fail' for a,b in zip(checks,contrasts))
            if any(c['status']=='fail' for c in checks):failures.append(g['id'])
            if any(c['status']=='unknown' for c in checks+contrasts) or g['role']=='unknown':unknown.append(g['id'])
            if realized and g['contrast']['mode']=='must_differ' and not distinguish:nondiscriminating.append(g['id'])
            result['gestures'].append(dict(id=g['id'],phrase_id=phrase['id'],role=g['role'],actual=checks,shallow_ablation=contrasts,distinguishes_shallow=distinguish,contrast_mode=g['contrast']['mode']))
    result['intent_execution'] = 'fail' if failures else 'unknown' if unknown else 'pass'
    result['discrimination'] = 'fail' if nondiscriminating else 'unknown' if unknown else 'pass'
    result['failed_gestures'] = failures;result['nondiscriminating_gestures'] = nondiscriminating
    if critique:
        cr = read(critique); exact(cr, {'schema_version','lock','project','pitch','facts','records','structural_responses'}, 'musical critique')
        if cr['schema_version']!=1:raise ValueError('Unsupported musical critique')
        for k,target in [('lock',lock),('project',project),('pitch',pitch),('facts',facts_path)]:
            actual=bound(cr[k],Path(critique).parent)
            if ref(actual)['sha256']!=ref(target)['sha256'] or (k!='facts' and actual!=Path(target).resolve()):
                raise ValueError('Stale musical critique '+k)
        seen=set();judgments=[]
        for row in cr['records']:
            exact(row,{'phrase_id','judgment','observed_consequences','evidence'},'phrase critique');text_fields(row,['observed_consequences'])
            if row['phrase_id'] in seen or row['phrase_id'] not in {p['id'] for p in brief['phrases']} or row['judgment'] not in {'retain','revise','unknown'} or not row['evidence']:
                raise ValueError('Missing/wrong actual phrase critique')
            for e in row['evidence']:bound(e,Path(critique).parent)
            seen.add(row['phrase_id']);judgments.append(row['judgment'])
        responses=set()
        for row in cr['structural_responses']:
            exact(row,{'code','context','evidence'},'structural response');text_fields(row,['context'])
            if row['code'] not in structural.get('findings',[]) or row['code'] in responses or not row['evidence']:raise ValueError('Wrong structural response')
            for e in row['evidence']:bound(e,Path(critique).parent)
            responses.add(row['code'])
        complete=seen=={p['id'] for p in brief['phrases']} and responses==set(structural.get('findings',[]))
        result['agent_judgment']='revise' if 'revise' in judgments else 'agent_attested' if complete and 'unknown' not in judgments else 'needs_review'
        result['bindings']['musical_critique']=ref(critique)
    result['status']='rejected' if failures or nondiscriminating or result['agent_judgment']=='revise' else 'agent_attested' if result['agent_judgment']=='agent_attested' and not unknown else 'needs_review'
    return result
