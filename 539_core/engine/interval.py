"""维度3：间隔分析（v2.1 修复版）

核心逻辑变更：诊断发现原版间隔评分方向反了
- 原版：间隔大 → 不中奖概率高（排除）
- 实际：间隔大 → 均值回归 → 反而更容易出现

v2.1 修正：间隔评分方向反转
- 间隔小（频繁出现）→ 不中奖概率高 → 高分（排除热号）
- 间隔大（久未出现）→ 不中奖概率低 → 低分（回归概率积攒）

同时改进：加入"间隔一致性"因子
- 间隔越不稳定（方差大）→ 号码表现不规则 → 不中奖概率更高
"""

from typing import List, Dict
from ..utils import safe_divide


def compute_interval_stats(
    draws: List[List[int]],
    number: int,
) -> Dict[str, float]:
    """计算单个号码的间隔统计（统计部分不变）"""
    total_draws = len(draws)
    appear_indices = [i for i, d in enumerate(draws) if number in d]

    if len(appear_indices) < 2:
        avg_interval = safe_divide(total_draws, max(len(appear_indices), 1))
        return {
            "avg_interval": avg_interval,
            "interval_variance": 0.0,
            "interval_std": 0.0,
            "intervals": [],
            "last_interval": total_draws if not appear_indices else total_draws - 1 - appear_indices[-1],
        }

    intervals = []
    for j in range(1, len(appear_indices)):
        intervals.append(appear_indices[j] - appear_indices[j - 1])

    last_interval = total_draws - 1 - appear_indices[-1]
    if last_interval > 0:
        intervals.append(last_interval)

    avg_interval = safe_divide(sum(intervals), len(intervals))
    if len(intervals) > 1:
        variance = sum((iv - avg_interval) ** 2 for iv in intervals) / len(intervals)
        std = variance ** 0.5
    else:
        variance = 0.0
        std = 0.0

    return {
        "avg_interval": avg_interval,
        "interval_variance": variance,
        "interval_std": std,
        "intervals": intervals,
        "last_interval": last_interval if last_interval > 0 else intervals[-1] if intervals else total_draws,
    }


def score_interval(
    draws: List[List[int]],
    number: int,
) -> float:
    """计算号码的不中奖间隔评分（v2.1 方向修正）

    不中奖概率方向（修正后）：
    - 间隔小（频繁出现）→ 不中奖概率高 → 高分（排除热号）
    - 间隔大（久未出现）→ 不中奖概率低 → 低分（回归概率积攒）

    新增因子：间隔方差
    - 方差大 → 号码出现不规则 → 不中奖概率更高（加分）
    - 方差小 → 号码出现规律 → 概率可预测 → 不影响
    """
    stats = compute_interval_stats(draws, number)
    avg_interval = stats["avg_interval"]
    interval_std = stats["interval_std"]

    theoretical_interval = 39.0 / 5.0  # ≈ 7.8

    # 基础评分（修正方向）：间隔低于理论值 → 高分
    interval_deviation = theoretical_interval - avg_interval
    # 间隔小 → deviation正 → 高分
    base_score = max(0.0, min(100.0, 50 + interval_deviation * 3))

    # 间隔方差修正：方差越大 → 号码更不规则 → 不中奖概率更高
    # 这里不反转，因为方差大确实意味着不可预测
    theoretical_std = (39.0 / 5.0) ** 0.5  # ≈ 2.8
    variance_factor = safe_divide(interval_std, theoretical_std)
    # variance_factor > 1 → 比理论更不稳定 → 加分（不中奖概率高）
    variance_adjustment = max(0, variance_factor - 1) * 10

    score = max(0.0, min(100.0, base_score + variance_adjustment))

    return score
