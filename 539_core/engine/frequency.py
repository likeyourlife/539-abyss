"""维度1：频率分析（v2.1 修复版）

核心逻辑变更：低频号码反而更容易出现（均值回归效应）
诊断发现：原版评分方向反了——"历史低频"标记为不中奖概率高，
但实际数据证明这些号反而更容易出现

v2.1 修正：频率评分方向反转
- 高频号码（热号）→ 不中奖概率高 → 高分（排除热号！）
- 低频号码（冷号）→ 不中奖概率低 → 低分（冷号可能回归出现）

原理：在随机系统中，长期高频号码"透支"了概率，
未来可能降温；长期低频号码"积攒"了概率，均值回归效应使其更可能出现。
"""

from typing import List, Dict
from ..utils import safe_divide


def compute_frequency_stats(
    draws: List[List[int]],
    number: int,
    decay_factor: float = 0.98,
) -> Dict[str, float]:
    """计算单个号码的频率统计（统计部分不变）"""
    total_draws = len(draws)
    if total_draws == 0:
        return {"total_freq": 0.0, "weighted_freq": 0.0,
                "appear_count": 0, "total_draws": 0}

    appear_count = 0
    weighted_appear = 0.0
    total_weight = 0.0

    for idx, draw_numbers in enumerate(draws):
        weight = decay_factor ** (total_draws - 1 - idx)
        total_weight += weight
        if number in draw_numbers:
            appear_count += 1
            weighted_appear += weight

    total_freq = safe_divide(appear_count, total_draws)
    weighted_freq = safe_divide(weighted_appear, total_weight)

    return {
        "total_freq": total_freq,
        "weighted_freq": weighted_freq,
        "appear_count": appear_count,
        "total_draws": total_draws,
    }


def score_frequency(
    draws: List[List[int]],
    number: int,
    decay_factor: float = 0.98,
) -> float:
    """计算号码的不中奖频率评分（v2.1 方向修正）

    不中奖概率方向（修正后）：
    - 高频号码 → 不中奖概率高 → 高分（排除）
    - 低频号码 → 不中奖概率低 → 低分（冷号回归，可能出现）

    原因：均值回归效应 — 长期高频的号码未来可能降温，
    长期低频的号码未来可能回暖（积攒概率）
    """
    stats = compute_frequency_stats(draws, number, decay_factor)
    weighted_freq = stats["weighted_freq"]

    theoretical_freq = 5.0 / 39.0  # ≈ 0.1282

    # 偏离度（修正方向）：高频 → 正偏离 → 高分
    deviation = weighted_freq - theoretical_freq

    # 正偏离（高频）→ 高分，负偏离（低频）→ 低分
    score = max(0.0, min(100.0, 50 + deviation * 500))

    return score
