"""维度2：近期趋势分析

核心逻辑：最近N期未出现的号码 → 不中奖概率越高
v2.0改进：动态窗口（3/5/10期加权），而非固定窗口

评分方向：recency_score = 不中奖概率方向
- 长期未出现的号码 → 高recency_score
- 刚刚出现的号码 → 低recency_score
"""

from typing import List, Dict
from ..utils import safe_divide


def compute_recency_stats(
    draws: List[List[int]],
    number: int,
) -> Dict[str, float]:
    """计算单个号码的近期趋势统计

    Args:
        draws: 历史开奖号码列表（从早到晚排序）
        number: 要分析的号码

    Returns:
        dict: {
            'recency_gap': 最近出现距今多少期（0=上期刚出现）,
            'recent_3_freq': 近3期出现频率,
            'recent_5_freq': 近5期出现频率,
            'recent_10_freq': 近10期出现频率,
            'weighted_recency': 动态窗口加权近期频率,
        }
    """
    total_draws = len(draws)
    if total_draws == 0:
        return {"recency_gap": total_draws, "recent_3_freq": 0.0,
                "recent_5_freq": 0.0, "recent_10_freq": 0.0,
                "weighted_recency": 0.0}

    # 计算recency_gap：从最近一期往回找，该号码最近出现的期数距离
    recency_gap = total_draws  # 默认从未出现过
    for i in range(total_draws - 1, -1, -1):
        if number in draws[i]:
            recency_gap = total_draws - 1 - i
            break

    # 计算各窗口期出现频率
    def window_freq(window_size: int) -> float:
        if total_draws < window_size:
            window_size = total_draws
        recent_draws = draws[-window_size:]
        count = sum(1 for d in recent_draws if number in d)
        return safe_divide(count, window_size)

    recent_3 = window_freq(3)
    recent_5 = window_freq(5)
    recent_10 = window_freq(10)

    # 动态窗口加权：近3期权重最高
    # 权重分配：3期=0.5, 5期=0.3, 10期=0.2
    weighted_recency = recent_3 * 0.5 + recent_5 * 0.3 + recent_10 * 0.2

    return {
        "recency_gap": recency_gap,
        "recent_3_freq": recent_3,
        "recent_5_freq": recent_5,
        "recent_10_freq": recent_10,
        "weighted_recency": weighted_recency,
    }


def score_recency(
    draws: List[List[int]],
    number: int,
) -> float:
    """计算号码的不中奖近期评分

    不中奖概率方向：
    - recency_gap大（长期未出现）→ 可能处于冷态，不中奖概率高
    - 但也要注意"均值回归"：长期冷号可能随时回暖

    评分策略：
    1. 基础评分基于recency_gap：gap越大→score越高
    2. 衰减修正：超过15期的gap开始衰减（均值回归效应）
    3. 近期频率修正：近期频率低 → 加强不中奖概率
    """
    stats = compute_recency_stats(draws, number)
    recency_gap = stats["recency_gap"]
    weighted_recency = stats["weighted_recency"]

    # 基础评分：gap映射到分数
    # gap=0 → score=0（刚出现过）
    # gap=10 → score≈80
    # gap=20 → score≈90（但开始衰减）
    if recency_gap == 0:
        base_score = 0.0
    elif recency_gap <= 15:
        # 线性增长阶段
        base_score = safe_divide(recency_gap, 15) * 80
    else:
        # 衰减阶段（均值回归效应）
        # 超过15期后增长放缓
        base_score = 80 + safe_divide(min(recency_gap - 15, 30), 30) * 10

    # 近期频率修正
    # 理论近期频率 = 5/39 ≈ 0.1282
    # 频率远低于理论 → 加强不中奖概率（加分）
    # 频率远高于理论 → 降低不中奖概率（减分）
    theoretical = 5.0 / 39.0
    freq_deviation = theoretical - weighted_recency
    freq_adjustment = freq_deviation * 50  # 缩放因子

    # 合并评分
    score = max(0.0, min(100.0, base_score + freq_adjustment))

    return score
