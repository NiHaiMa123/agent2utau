"""Read-only, seeded single-channel DiffSinger response experiment.

Consumes cache-verified native exports. It does not choose musical controls,
edit projects, search parameters, or assess perceived voice quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from ..expression.variance_expectation import CHANNELS, gaussian_frame_noise


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tensors(items):
    names = [q['name'] for q in items]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate native tensor names')
    return {q['name']: np.asarray(q['values'], dtype=q['dtype']).reshape(q['shape'])
            for q in items}


def require_isolation(a, b, va, vb, channel, support_s):
    if channel not in CHANNELS:
        raise ValueError('Unsupported intervention channel')
    for r, v in ((a, va), (b, vb)):
        if not r['native_acoustic_cache_verified'] or not v['native_variance_cache_verified']:
            raise ValueError('Unverified native cache')
    if va != vb:
        raise ValueError('Changed variance conditioning or native prediction')
    for key in ('position_ms', 'frame_ms', 'head_frames', 'tail_frames',
                'sample_rate', 'singer_location', 'acoustic_model', 'vocoder_model',
                'acoustic_mel_base', 'vocoder_mel_base', 'phones', 'vocoder_f0',
                'native_variance_predictions'):
        if a[key] != b[key]:
            raise ValueError(f'Changed native condition: {key}')
    aa, bb = tensors(a['tensors']), tensors(b['tensors'])
    if aa.keys() != bb.keys():
        raise ValueError('Changed input names')
    changed = [k for k in aa if not np.array_equal(aa[k], bb[k])]
    if changed != [channel]:
        raise ValueError(f'Expected only {channel}, got {changed}')
    t = (a['position_ms'] + (np.arange(aa[channel].size) - a['head_frames'])
         * a['frame_ms']) / 1000
    selected = np.flatnonzero(aa[channel].ravel() != bb[channel].ravel())
    if not len(selected) or np.any((t[selected] < support_s[0]) | (t[selected] > support_s[1])):
        raise ValueError('Actual intervention escapes declared finite support')
    for k in CHANNELS:
        da = np.asarray(a['expression_deltas'][k], np.float32)
        db = np.asarray(b['expression_deltas'][k], np.float32)
        if k != channel and not np.array_equal(da, db):
            raise ValueError(f'Changed nonselected control: {k}')
        if k == channel and np.any(db[selected] != 0):
            raise ValueError('B must cancel the selected manual offset')
        for r, inputs in ((a, aa), (b, bb)):
            pred = np.asarray(r['native_variance_predictions'][k], np.float32)[None, :]
            delta = np.asarray(r['expression_deltas'][k], np.float32)[None, :]
            limits = (-10, 10) if k == 'tension' else (-96, 0)
            if not np.array_equal(np.clip(pred + delta, *limits), inputs[k]):
                raise ValueError(f'Native float32 arithmetic mismatch: {k}')
    return dict(changed_native_inputs=changed, changed_frames=len(selected),
                actual_changed_support_s=t[selected[[0, -1]]].tolist(),
                native_variance_conditions_exact=True, native_arithmetic_exact=True)


def noise_adapter(source, destination, channels, bins):
    import onnx
    m = onnx.load(str(source))
    initializers = [x.SerializeToString() for x in m.graph.initializer]
    nodes = [n for n in m.graph.node if n.op_type.startswith('Random')]
    if len(nodes) != 1 or nodes[0].op_type != 'RandomNormalLike':
        raise ValueError('Unsupported random model layout')
    n = nodes[0]
    n.op_type = 'Identity'
    del n.input[:]
    n.input.append('probe_noise')
    del n.attribute[:]
    m.graph.input.append(onnx.helper.make_tensor_value_info(
        'probe_noise', onnx.TensorProto.FLOAT, [1, channels, bins, 'n_frames']))
    onnx.checker.check_model(m)
    if initializers != [x.SerializeToString() for x in m.graph.initializer]:
        raise ValueError('Adapter changed weights')
    onnx.save(m, str(destination))
    return dict(source=str(source), source_sha256=sha(source),
                adapter_sha256=sha(destination), initializer_weights_exact=True)


def require_shift_isolation(a, b, va, vb, support_s, peak_cents):
    """One upstream SHFC intervention; derived variance channels may change.

    This does not equate acoustic conditioning F0 with measured output F0.
    The unshifted vocoder F0 is required to remain byte-for-byte identical.
    """
    for r, v in ((a, va), (b, vb)):
        if not r['native_acoustic_cache_verified'] or not v['native_variance_cache_verified']:
            raise ValueError('Unverified native cache')
        if not r['vocoder_pitch_controllable']:
            raise ValueError('Vocoder cannot isolate conditioning pitch')
    for key in ('position_ms','frame_ms','head_frames','tail_frames','sample_rate',
                'singer_location','acoustic_model','vocoder_model',
                'acoustic_mel_base','vocoder_mel_base','phones','vocoder_f0'):
        if a[key] != b[key]:
            raise ValueError(f'Changed native condition: {key}')
    for key in ('frame_ms','head_frames','tail_frames','variance_model',
                'variance_speaker_root','native_linguistic_cache','linguistic_tensors'):
        if va[key] != vb[key]:
            raise ValueError(f'Changed variance condition: {key}')
    aa, bb, av, bv = [tensors(r['tensors']) for r in (a,b,va,vb)]
    if aa.keys() != bb.keys() or av.keys() != bv.keys():
        raise ValueError('Changed input names')
    changed = [k for k in aa if not np.array_equal(aa[k],bb[k])]
    variance_changed = [k for k in av if not np.array_equal(av[k],bv[k])]
    if 'f0' not in changed or set(changed) - {'f0',*CHANNELS} or variance_changed != ['pitch']:
        raise ValueError('Undeclared SHFC dependency changed')
    ca, cb = [np.asarray(r['tone_shift_cents'],np.float32) for r in (a,b)]
    sa, sb = [np.asarray(r['tone_shift_semitones'],np.float32) for r in (va,vb)]
    frames = aa['f0'].size
    if any(x.shape != (frames,) or not np.isfinite(x).all() for x in (ca,cb,sa,sb)):
        raise ValueError('Bad sampled shift geometry')
    if np.any(ca != 0) or np.any(sa != 0) or not np.isfinite(peak_cents) or peak_cents == 0:
        raise ValueError('A must have zero SHFC and B a declared nonzero peak')
    if np.any(cb < min(0,peak_cents)) or np.any(cb > max(0,peak_cents)) or not np.any(cb == peak_cents):
        raise ValueError('Shift differs from declared peak/direction')
    clock = (a['position_ms']+(np.arange(frames)-a['head_frames'])*a['frame_ms'])/1000
    ix = np.flatnonzero(cb != 0)
    if not len(ix) or np.any((clock[ix]<support_s[0]) | (clock[ix]>support_s[1])):
        raise ValueError('Actual shift escapes declared finite support')
    # Separate native samplers convert to float32 at different points. Bound
    # that conversion error; do not allow a musical pitch tolerance here.
    if np.max(np.abs(sb.astype(np.float64)*100-cb)) > .00005:
        raise ValueError('Variance/acoustic shift paths disagree')
    if not np.array_equal(bv['pitch'],av['pitch']+sb[None,:]):
        raise ValueError('Variance pitch did not receive declared SHFC')
    unshifted = np.asarray(a['vocoder_f0'],np.float32)[None,:]
    factor = np.asarray([math.pow(2,float(c)/1200) for c in cb],np.float32)[None,:]
    if not np.array_equal(aa['f0'],unshifted) or not np.array_equal(bb['f0'],unshifted*factor):
        raise ValueError('Acoustic F0 did not receive native SHFC transform')
    for k in CHANNELS:
        if a['expression_deltas'][k] != b['expression_deltas'][k]:
            raise ValueError(f'Changed manual control: {k}')
        for r,inputs in ((a,aa),(b,bb)):
            pred = np.asarray(r['native_variance_predictions'][k],np.float32)[None,:]
            delta = np.asarray(r['expression_deltas'][k],np.float32)[None,:]
            limits = (-10,10) if k=='tension' else (-96,0)
            if not np.array_equal(np.clip(pred+delta,*limits),inputs[k]):
                raise ValueError(f'Native arithmetic mismatch: {k}')
    return dict(upstream_intervention='SHFC',peak_shift_cents=peak_cents,
        changed_native_inputs=changed,changed_variance_inputs=variance_changed,
        changed_frames=len(ix),actual_changed_support_s=clock[ix[[0,-1]]].tolist(),
        manual_controls_exact=True,linguistic_conditions_exact=True,
        vocoder_F0_exact=True,native_arithmetic_exact=True)


def spectral_response(mel_a, mel_b, clock_s, interval_s):
    """Native log-mel proxies, removing per-frame overall level separately."""
    if mel_a.shape != mel_b.shape or mel_a.shape[-2] != len(clock_s):
        raise ValueError('Changed mel shape or clock')
    mask = (clock_s >= interval_s[0]) & (clock_s <= interval_s[1])
    if not mask.any():
        raise ValueError('No analysis frames')
    delta = np.asarray(mel_b - mel_a, np.float64)[0, mask, :]
    shape = delta - delta.mean(axis=-1, keepdims=True)
    return dict(frames=int(mask.sum()), log_mel_rms=float(np.sqrt(np.mean(delta**2))),
                level_removed_log_mel_rms=float(np.sqrt(np.mean(shape**2))),
                mean_log_mel_change=float(delta.mean()),
                formant_truth=False, perceived_improvement=False)


def run(args):
    import onnxruntime as ort
    import soundfile as sf
    out = Path(args.out)
    if out.exists():
        raise FileExistsError('Preserve prior experiment output')
    out.mkdir(parents=True)
    paths = [Path(p) for p in (args.a, args.b, args.variance_a, args.variance_b)]
    a, b, va, vb = [json.loads(p.read_text(encoding='utf8')) for p in paths]
    mode = getattr(args,'mode','manual_cancel')
    isolation = (require_shift_isolation(a,b,va,vb,args.support,args.shift_peak_cents)
                 if mode=='shfc' else require_isolation(a,b,va,vb,args.channel,args.support))
    if a['frame_ms'] != va['frame_ms'] or a['head_frames'] != va['head_frames']:
        raise ValueError('Resampled variance layout requires a separate verified adapter')
    models = out / 'models'
    models.mkdir()
    adapters = [noise_adapter(va['variance_model'], models/'variance.onnx', 3, 24),
                noise_adapter(a['acoustic_model'], models/'acoustic.onnx', 1, 128)]
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = opts.inter_op_num_threads = 1
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    sessions = [ort.InferenceSession(str(p), sess_options=opts,
                providers=['CPUExecutionProvider']) for p in
                (models/'variance.onnx', models/'acoustic.onnx', a['vocoder_model'])]
    names = [q.name for q in sessions[0].get_outputs()]
    bound = set(paths) | {Path(a['acoustic_model']), Path(va['variance_model']), Path(a['vocoder_model'])}
    for root in (Path(a['singer_location']), Path(va['variance_speaker_root'])):
        bound.update(root.glob('*.yaml'))
        bound.update(root.glob('*.json'))
        bound.update(root.glob('*.emb'))
    for r, v in ((a, va), (b, vb)):
        bound.update(Path(x) for x in (r['native_acoustic_cache'], v['native_variance_cache'], v['native_linguistic_cache']))
    binding = {str(p): sha(p) for p in sorted(bound)}
    results = {}
    frames = tensors(a['tensors'])['f0'].size
    clock = (a['position_ms'] + (np.arange(frames)-a['head_frames'])*a['frame_ms'])/1000
    for label, rec, vr in (('A', a, va), ('A_repeat', a, va), ('B', b, vb)):
        inputs, v = tensors(rec['tensors']), tensors(vr['tensors'])
        for ts, root in ((inputs, Path(rec['singer_location'])), (v, Path(vr['variance_speaker_root']))):
            expected = (.75*np.fromfile(root/'Yousa_Normal.emb', dtype='<f4')
                        + .25*np.fromfile(root/'Yousa_Classic.emb', dtype='<f4'))
            if not np.array_equal(ts['spk_embed'], np.broadcast_to(expected, ts['spk_embed'].shape)):
                raise ValueError('Actual speaker mix differs from frozen Normal75/Classic25')
        v['probe_noise'] = gaussian_frame_noise(11, 3, 24, frames)
        pred = dict(zip(names, sessions[0].run(names, v)))
        for k in CHANNELS:
            if pred[k+'_pred'].shape != inputs[k].shape:
                raise ValueError('Prediction shape changed')
            limits = (-10, 10) if k == 'tension' else (-96, 0)
            inputs[k] = np.clip(pred[k+'_pred'] + np.asarray(rec['expression_deltas'][k], np.float32)[None, :], *limits)
        inputs['probe_noise'] = gaussian_frame_noise(101, 1, 128, frames)
        mel = sessions[1].run(['mel'], inputs)[0]
        vocoder_mel = mel.copy()
        if rec['acoustic_mel_base'] != rec['vocoder_mel_base']:
            vocoder_mel *= np.log(10) if rec['acoustic_mel_base'] == '10' else 1/np.log(10)
        wave = sessions[2].run(None, dict(mel=vocoder_mel, f0=np.asarray(rec['vocoder_f0'], np.float32)[None, :]))[0].reshape(-1)
        if not np.isfinite(wave).all():
            raise ValueError('Nonfinite synthesized waveform')
        np.save(out/f'{label}.npy', wave)
        sf.write(out/f'{label}_raw.wav', wave, rec['sample_rate'], subtype='FLOAT')
        np.savez_compressed(out/f'{label}_inputs.npz', **inputs)
        np.savez_compressed(out/f'{label}_prediction.npz', **pred)
        np.save(out/f'{label}_mel.npy', mel)
        results[label] = dict(wave=wave, mel=mel, inputs=inputs, pred=pred)
        print(f'{label}: fresh variance 11 / acoustic 101 / vocoder complete', flush=True)
    def changed_dict(x, y):
        return [k for k in x if not np.array_equal(x[k], y[k])]
    repeat = results['A_repeat']
    baseline = results['A']
    altered = results['B']
    repeated_inputs = changed_dict(baseline['inputs'], repeat['inputs'])
    repeated_prediction = changed_dict(baseline['pred'], repeat['pred'])
    final_changed = changed_dict(baseline['inputs'], altered['inputs'])
    allowed = {'f0',*CHANNELS} if mode=='shfc' else {args.channel}
    if repeated_inputs or repeated_prediction or set(final_changed)-allowed:
        raise ValueError('Fresh synthesis input isolation failed')
    if mode=='manual_cancel' and final_changed != [args.channel]:
        raise ValueError('Expected only selected manual channel')
    prediction_changed=changed_dict(baseline['pred'], altered['pred'])
    if mode=='manual_cancel' and prediction_changed:
        raise ValueError('Fresh variance prediction changed')
    if mode=='shfc' and 'f0' not in final_changed:
        raise ValueError('Fresh acoustic F0 did not change')
    if any(sha(p) != h for p, h in binding.items()):
        raise ValueError('Frozen dependency changed during experiment')
    report = dict(schema='controlled-native-response-2', mode=mode,isolation=isolation,
        bindings=binding, adapters=adapters, ort_version=ort.__version__, numpy_version=np.__version__,
        seeds={'variance':11,'acoustic':101}, speaker_mix={'Normal':75,'Classic':25},
        wave_start_s=float(clock[0]), sample_rate=a['sample_rate'],
        fresh_final_changed_inputs=final_changed,
        fresh_variance_prediction_exact=not prediction_changed,
        fresh_prediction_changes={k:float(np.max(np.abs(baseline['pred'][k]-altered['pred'][k]))) for k in names},
        repeat_wave_max_abs=float(np.max(np.abs(baseline['wave']-repeat['wave']))),
        repeat=spectral_response(baseline['mel'],repeat['mel'],clock,args.analysis),
        response=spectral_response(baseline['mel'],altered['mel'],clock,args.analysis),
        analysis_s=args.analysis, naturalness_accepted=False, listening_pending=True)
    (out/'response.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('a','b','variance-a','variance-b','out'):
        p.add_argument('--'+name, required=True)
    p.add_argument('--mode',choices=['manual_cancel','shfc'],default='manual_cancel')
    p.add_argument('--channel', choices=CHANNELS)
    p.add_argument('--shift-peak-cents',type=float)
    p.add_argument('--support', type=float, nargs=2, required=True)
    p.add_argument('--analysis', type=float, nargs=2, required=True)
    args=p.parse_args()
    if args.mode=='manual_cancel' and args.channel is None:
        p.error('--channel is required for manual_cancel')
    if args.mode=='shfc' and args.shift_peak_cents is None:
        p.error('--shift-peak-cents is required for shfc')
    run(args)
