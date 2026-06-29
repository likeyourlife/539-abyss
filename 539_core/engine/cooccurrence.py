"""新增维度8：共现分析（Co-occurrence）

核心逻辑：开奖号码不是独立出现的——某些号码经常一起出现。
如果号码A和B经常共现，那么当A很可能出现时，B也更可能出现。

策略：
- 找到最近期出现的高频号码（热号）
- 分析哪些号码与这些热号有高共现率
- 高共现号码 → 更可能一起出现 → 不中奖概率低 → 低分
- 低共现号码 → 不容易和热号搭伴 → 不中奖概率高 → 高分

这本质上是"号码社交网络"——号码间的关联性。
"""

from typing import List, Dict, Tuple
from ..utils import safe_divide
from collections import defaultdict


def compute_cooccurrence_stats(
    draws: List[List[int]],
    number: int,
    window: int = 30,
) -> Dict[str, float]:
    """计算号码的共现统计

    分析该号码与近期高频号码的共现程度。

    Args:
        draws: 历史开奖号码列表
        number: 要分析的号码
        window: 分析窗口期数

    Returns:
        dict: {
            'recent_hot_numbers': 近期高频号码列表,
            'avg_cooccurrence': 与近期热号的平均共现率,
            'max_cooccurrence': 与某个热号的最大共现率,
            'cooccurrence_score': 综合共现评分(0-1),
        }
    """
    total_draws = len(draws)
    if total_draws < window:
        return {"recent_hot_numbers": [], "avg_cooccurrence": 0.0,
                "max_cooccurrence": 0.0, "cooccurrence_score": 0.5}

    recent = draws[-window:]

    # 1. 找出近期高频号码（出现次数最多的5-8个号）
    number_counts = defaultdict(int)
    for d in recent:
        for n in d:
            number_counts[n] += 1

    # 取频率最高的前8个号码作为"热号锚点"
    sorted_by_freq = sorted(number_counts.items(), key=lambda x: x[1], reverse=True)
    hot_numbers = [n for n, c in sorted_by_freq[:8]]

    # 2. 计算该号码与每个热号的共现率
    # 共现率 = 两号码同时出现在同一期的次数 / 热号出现的总次数
    cooccurrence_rates = []

    for hot_num in hot_numbers:
        if hot_num == number:
            continue

        # 热号出现的期数
        hot_appear_periods = [d for d in recent if hot_num in d]

        if not hot_appear_periods:
            continue

        # 两号码同时出现的期数
        co_appear = sum(1 for d in hot_appear_periods if number in d)
        rate = safe_divide(co_appear, len(hot_appear_periods))
        cooccurrence_rates.append(rate)

    # 3. 综合评分
    avg_cooc = safe_divide(sum(cooccurrence_rates), len(cooccurrence_rates)) if cooccurrence_rates else 0.0
    max_cooc = max(cooccurrence_rates) if cooccurrence_rates else 0.0

    # 理论共现率（随机情况下）：如果热号出现，该号同时出现的概率 = 5/39
    # 但因为5个号中1个已经是热号，剩余4个位置选该号的概率 = 4/(39-1) = 4/38
    theoretical_cooc = safe_divide(4, 38)

    # 共现评分：实际共现率 vs 理论值
    cooc_score = safe_divide(avg_cooc, theoretical_cooc, default=1.0)

    return {
        "recent_hot_numbers": hot_numbers,
        "avg_cooccurrence": avg_cooc,
        "max_cooccurrence": max_cooc,
        "cooccurrence_score": min(cooc_score, 2.0),  # 上限2倍
    }


def score_cooccurrence(
    draws: List[List[int]],
    number: int,
    window: int = 30,
) -> float:
    """计算号码的不中奖共现评分

    不中奖概率方向：
    - 高共现率 → 号码容易和热号搭伴 → 不中奖概率低 → 低分
    - 低共现率 → 号号不容易和热号搭伴 → 不中奖概率高 → 高分
    """
    stats = compute_cooccurrence_stats(draws, number, window)
    cooc_score = stats["cooccurrence_score"]

    # 不中奖方向：低共现 → 高分
    # cooc_score范围大约 [0.5, 2.0]
    # 1.0是理论基准
    deviation = 1.0 - cooc_score  # 正值=低于理论(低共现)，负值=高于理论
    score = max(0.0, min(100.0, 50 + deviation * 50))

    return score
