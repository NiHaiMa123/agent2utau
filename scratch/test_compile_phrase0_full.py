import sys
sys.path.insert(0, 'src')
import json
import numpy as np
from pathlib import Path
from agent2utau.workflow import design_math

dm = design_math()
from test_skill_pitch import nodes, p_start_s, p_end_s

# Components for phrase 0
components = [
    {
        'id': 'p01_u02_arch',
        'family': 'finite_return',
        'support_s': [14.830, 15.050],
        'peak_s': 14.940,
        'peak_c': 18.0
    },
    {
        'id': 'p01_u05_arch',
        'family': 'finite_return',
        'support_s': [16.050, 16.300],
        'peak_s': 16.180,
        'peak_c': 16.0
    },
    {
        'id': 'p01_u07_vib',
        'family': 'oscillation',
        'support_s': [17.000, 17.400],
        'attack_end_s': 17.060,
        'release_start_s': 17.340,
        'depth_nodes': [
            [17.000, 8.0],
            [17.150, 24.0],
            [17.400, 10.0]
        ],
        'rate_nodes': [
            [17.000, 5.4],
            [17.400, 5.6]
        ],
        'phase_rad': 0.0
    }
]

decisions = [
    {
        'support_s': [p_start_s, 14.830],
        'condition': 'First phrase start and pick up',
        'choice': 'natural_two_stage_step',
        'alternative': 'square_jump',
        'reason': 'Conforms to two-stage terrace upward interval connection recipe',
        'uncertainty': 'minimal',
        'component_ids': []
    },
    {
        'support_s': [14.830, 15.050],
        'condition': 'Note 2 (停) sustain body',
        'choice': 'expressive_micro_arch',
        'alternative': 'flat_plateau',
        'reason': 'Lyrical emphasis on 停',
        'uncertainty': 'minimal',
        'component_ids': ['p01_u02_arch']
    },
    {
        'support_s': [15.050, 16.050],
        'condition': 'Mid phrase connections (下脚步)',
        'choice': 'smooth_s_curves',
        'alternative': 'instant_midi_step',
        'reason': 'Smooth glides between syllables',
        'uncertainty': 'minimal',
        'component_ids': []
    },
    {
        'support_s': [16.050, 16.300],
        'condition': 'Note 5 (步) sustain body',
        'choice': 'expressive_micro_arch',
        'alternative': 'flat_plateau',
        'reason': 'Subtle expressive swell',
        'uncertainty': 'minimal',
        'component_ids': ['p01_u05_arch']
    },
    {
        'support_s': [16.300, 17.000],
        'condition': 'Major downward drop (却) and rise (无)',
        'choice': 'downward_undershoot_and_terrace_rise',
        'alternative': 'cliff_jump',
        'reason': 'Musical portamento and terrace rise',
        'uncertainty': 'minimal',
        'component_ids': []
    },
    {
        'support_s': [17.000, 17.400],
        'condition': 'Note 7 (住) long sustained vowel',
        'choice': 'natural_vibrato',
        'alternative': 'stiff_plateau',
        'reason': 'Phrase cadence vibrato expansion',
        'uncertainty': 'minimal',
        'component_ids': ['p01_u07_vib']
    },
    {
        'support_s': [17.400, p_end_s],
        'condition': 'Phrase tail release',
        'choice': 'release_hold',
        'alternative': 'sudden_cutoff',
        'reason': 'Clean decay into breath boundary',
        'uncertainty': 'minimal',
        'component_ids': []
    }
]

expectations = [
    {
        'support_s': [p_start_s, p_end_s],
        'range_c': [700.0, 950.0],
        'purpose': 'Check overall phrase melodic range'
    },
    {
        'support_s': [14.830, 15.050],
        'range_c': [10.0, 30.0],
        'purpose': 'Check micro arch on 停'
    },
    {
        'support_s': [17.000, 17.400],
        'range_c': [30.0, 60.0],
        'purpose': 'Check vibrato depth on 住'
    }
]

plan = {
    'schema': 1,
    'origin': 'agent_designed',
    'support_s': [p_start_s, p_end_s],
    'center_nodes': nodes,
    'components': components,
    'decisions': decisions,
    'expectations': expectations
}

res = dm.compile_plan(plan)
print('Shape checks pass:', res['shape_checks_pass'])
for c in res['local_checks']:
    print(' ', c['purpose'], 'observed:', c['observed_range_c'], 'pass:', c['pass'])
