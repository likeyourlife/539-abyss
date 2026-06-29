"""维度4：偏差分析（v2.1 修复版）

核心逻辑变更：诊断发现原版偏差评分方向反了
- 原版：Z-score负值（低于理论频率）→ 不中奖概率高
- 实际：Z-score负值号码反而更容易出现（均值回归）

v2.1 修正：偏差评分方向反转
- Z-score正值（高于理论频率）→ 不中奖概率高 → 高分
- Z-score负值（低于理论频率）→ 不中奖概率低 → 低分

原理：长期超出理论频率的号码是"热号"，未来可能降温（均值回归），
因此不中奖概率反而更高；低于理论频率的"冷号"可能回归出现。
"""

import math
from typing import List, Dict
from ..utils import safe_divide


def compute_deviation_stats(
    draws: List[List[int]],
    number: int,
) -> Dict[str, float]:
    """计算单个号码的偏差统计（统计部分不变）"""
    total_draws = len(draws)
    if total_draws == 0:
        return {"appear_count": 0, "total_draws": 0, "observed_freq": 0.0,
                "expected_freq": 5.0 / 39.0, "z_score": 0.0, "deviation_ratio": 0.0}

    appear_count = sum(1 for d in draws if number in d)
    observed_freq = safe_divide(appear_count, total_draws)
    expected_freq = 5.0 / 39.0

    p = expected_freq
    se = math.sqrt(safe_divide(p * (1 - p), total_draws, default=1.0))
    z_score = safe_divide(observed_freq - expected_freq, se) if se > 0 else 0.0
    deviation_ratio = safe_divide(observed_freq, expected_freq)

    return {
        "appear_count": appear_count,
        "total_draws": total_draws,
        "observed_freq": observed_freq,
        "expected_freq": expected_freq,
        "z_score": z_score,
        "deviation_ratio": deviation_ratio,
    }


def score_deviation(
    draws: List[List[int]],
    number: int,
) -> float:
    """计算号码的不中奖偏差评分（v2.1 方向修正）

    不中奖概率方向（修正后）：
    - Z-score正值大（高于理论频率的热号）→ 不中奖概率高 → 高分
    - Z-score负值大（低于理论频率的冷号）→ 不中奖概率低 → 低分

    原因：均值回归效应 — 超出理论频率的热号未来可能降温，
    低于理论频率的冷号未来可能回暖。
    """
    stats = compute_deviation_stats(draws, number)
    z_score = stats["z_score"]

    # 修正方向：Z-score正值 → 高分（热号排除），负值 → 低分
    score = max(0.0, min(100.0, 50 + z_score * 12))

    return score
