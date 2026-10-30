"""阶段5f：修正 — 原生短语超出 part 设计支撑时，用边界值外推（不外推斜率）。

根因：AP 呼吸音符让原生 RenderPhrase 起点早于 part 的 sung 起点（如 18.23 vs 18.73），
      df.evaluate 在主支撑外做 Hermite 外推 → 数值爆炸（33984c）。
修正：
  1) 采样时把时间 clamp 到设计支撑内（外推用边界值，这是 AP 段的正确做法：保持载频）
  2) 重采样后核验所有节点在合理音高范围（4000–9000c）
"""
import sys, json, io, importlib.util
import numpy as np, yaml
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutx import ustx as _u  # noqa
