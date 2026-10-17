"""Lazy ONNX integration for future authorized execution, never auto-run.

Receives already SHA-bound native records/runtime root explicitly. Noise model
copies go only into a caller-selected new research/experiment run directory.
"""
from pathlib import Path
import numpy as np

from freeze_stage_2d import ROOT, sha
from shfc_path_runner import load_sealed_protocol
from agent2utau.evaluation.controlled_probe import noise_adapter


class OnnxPathsBackend:
    def __init__(self, records, *, install_root, out):
        protocol = load_sealed_protocol()
        out = Path(out).resolve()
        if out.exists() or not any(out.is_relative_to(ROOT / p) for p in ['runs/research', 'runs/experiments']):
            raise ValueError('Explicit unused local research/experiment output required')
        self.install_root = Path(install_root).resolve()
        self.expected = protocol['fixed']['runtime_expected_hashes']
        for alias, digest in self.expected.items():
            prefix = 'external-resource/OpenUtau/'
            if not alias.startswith(prefix):
                raise ValueError('Unresolved runtime identity')
            path = (self.install_root / alias[len(prefix):]).resolve()
            if not path.is_relative_to(self.install_root) or sha(path) != digest:
                raise ValueError('Current installed runtime SHA differs')
        cases = {c['condition']['id'] for c in protocol['cases']}
        if set(records) != cases:
            raise ValueError('Backend requires both frozen condition records')
        self.records = records
        first_a, first_v = records[next(iter(records))]
        for a,v in records.values():
            for key in ['acoustic_model','vocoder_model','acoustic_mel_base','vocoder_mel_base','singer_location']:
                if a[key] != first_a[key]:
                    raise ValueError('Condition backend resource differs')
            for key in ['variance_model','variance_speaker_root']:
                if v[key] != first_v[key]:
                    raise ValueError('Condition variance resource differs')
        for name in [first_a['acoustic_model'], first_a['vocoder_model'], first_v['variance_model']]:
            self.require_resource(name)
        # Imports and source-model loads occur only when constructor is called.
        import onnxruntime as ort
        out.mkdir(parents=True)
        var_model, acoustic_model = out/'variance.onnx', out/'acoustic.onnx'
        self.adapter_proofs = [noise_adapter(first_v['variance_model'],var_model,3,24),
            noise_adapter(first_a['acoustic_model'],acoustic_model,1,128)]
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = opts.inter_op_num_threads = 1
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.variance, self.acoustic, self.vocoder = [ort.InferenceSession(str(p),sess_options=opts,
            providers=['CPUExecutionProvider']) for p in [var_model,acoustic_model,first_a['vocoder_model']]]
        self.variance_record = first_v
        self.predictor_calls = self.renderer_calls = 0

    def require_resource(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.install_root):
            raise ValueError('Model/speaker resource outside declared install')
        alias = 'external-resource/OpenUtau/' + path.relative_to(self.install_root).as_posix()
        if alias not in self.expected or sha(path) != self.expected[alias]:
            raise ValueError('Model/speaker resource lacks frozen SHA')

    def check_speaker(self, values, root):
        normal,classic = Path(root)/'Yousa_Normal.emb',Path(root)/'Yousa_Classic.emb'
        for p in (normal,classic):
            self.require_resource(p)
        speaker = .75*np.fromfile(normal,dtype='<f4')+.25*np.fromfile(classic,dtype='<f4')
        if 'spk_embed' not in values or not np.array_equal(values['spk_embed'],np.broadcast_to(speaker,values['spk_embed'].shape)):
            raise ValueError('Actual two-stage speaker mix differs')

    def predict(self, values):
        if self.predictor_calls >= 8:
            raise ValueError('Frozen variance budget exceeded')
        self.check_speaker(values,self.variance_record['variance_speaker_root'])
        names = [r.name for r in self.variance.get_outputs()]
        if set(names) != {'breathiness_pred','voicing_pred','tension_pred'}:
            raise ValueError('Unsupported variance output contract')
        self.predictor_calls += 1
        return dict(zip(names,self.variance.run(names,values)))

    def render(self, inputs, vocoder_f0, condition_id):
        if self.renderer_calls >= 16 or condition_id not in self.records:
            raise ValueError('Frozen rendering budget/condition exceeded')
        a,_ = self.records[condition_id]
        self.check_speaker(inputs,a['singer_location'])
        self.renderer_calls += 1
        mel = self.acoustic.run(['mel'],inputs)[0]
        converted = mel.copy()
        if a['acoustic_mel_base'] not in ('e','10') or a['vocoder_mel_base'] not in ('e','10'):
            raise ValueError('Unknown mel unit')
        if a['acoustic_mel_base'] != a['vocoder_mel_base']:
            converted *= np.log(10) if a['acoustic_mel_base']=='10' else 1/np.log(10)
        wave = self.vocoder.run(None,dict(mel=converted,f0=vocoder_f0))[0].reshape(-1)
        return mel,wave

    def final_bindings_hold(self):
        # Reopen only declared inputs; no cache search or changed-runtime repair.
        for alias,digest in self.expected.items():
            if sha(self.install_root/alias.removeprefix('external-resource/OpenUtau/')) != digest:
                raise ValueError('Runtime changed during explicit backend execution')
        return dict(runtime_bytes_exact=True,variance_calls=self.predictor_calls,raw_acoustic_vocoder_calls=self.renderer_calls)
