import sys
sys.path.insert(0, 'src')
import json
import numpy as np
from pathlib import Path
from agent2utau.workflow import design_math

dm = design_math()

# Load test_skill_pitch nodes
from test_skill_pitch import nodes, p_start_s, p_end_s

plan = {
    'schema': 1,
    'origin': 'agent_designed',
    'support_s': [p_start_s, p_end_s],
    'center_nodes': nodes,
    'components': [],
    'decisions': [
        {
            'support_s': [p_start_s, p_end_s],
            'condition': 'First phrase melodic line with natural skill transitions',
            'choice': 'natural_transitions',
            'alternative': 'counterfactual_square_step',
            'reason': 'Conforms to upward and downward interval connections in skill references',
            'uncertainty': 'minimal',
            'component_ids': []
        }
    ],
    'expectations': [
        {
            'support_s': [p_start_s, p_end_s],
            'range_c': [700.0, 950.0],
            'purpose': 'Check overall phrase melodic range'
        }
    ]
}

res = dm.compile_plan(plan)
print('Shape checks pass:', res['shape_checks_pass'])
print('Times count:', len(res['times_s']))
print('Cents min/max:', min(res['cents']), max(res['cents']))
