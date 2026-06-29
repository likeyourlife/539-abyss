"""新增维度7：组合约束分析（Combinatorial Coverage）

核心逻辑：开奖号码不是独立选择的——每期5个号码覆盖不同区间。
历史数据显示，每期的5个号码倾向于分散在不同区间：
  - 区间1 [01-13]: 平均1.7个号码
  - 区间2 [14-26]: 平均1.7个号码
  - 区间3 [27-39]: 平均1.6个号码

如果一个区间在近期开奖中被"低估"（号码少于期望），
该区间的号码在下一期更可能出现（组合回归）。

评分方向：
- 号码所属区间近期被低估 → 号码更可能出现 → 不中奖概率低 → 低分
- 号码所属区间近期被高估 → 号码不太出现 → 不中奖概率高 → 高分
"""

from typing import List, Dict
from ..utils import safe_divide
from collections import defaultdict


def compute_coverage_stats(
    draws: List[List[int]],
    number: int,
    window: int = 15,
) -> Dict[str, float]:
    """计算号码的组合覆盖统计

    分析近期各区间号码出现密度，判断该号码所在区间的覆盖状态。

    Args:
        draws: 历史开奖号码列表
        number: 要分析的号码
        window: 分析窗口期数

    Returns:
        dict: {
            'zone': 区间编号(1/2/3),
            'zone_expected': 区间理论期望密度,
            'zone_observed': 区间近期实际密度,
            'zone_coverage_ratio': 区间覆盖比率(observed/expected),
            'coverage_deviation': 覆盖偏差(observed - expected),
        }
    """
    total_draws = len(draws)
    if total_draws < window:
        return {"zone": 0, "zone_expected": 0.0, "zone_observed": 0.0,
                "zone_coverage_ratio": 1.0, "coverage_deviation": 0.0}

    # 确定号码所在区间
    if 1 <= number <= 13:
        zone = 1
    elif 14 <= number <= 26:
        zone = 2
    else:
        zone = 3

    # 区间范围映射
    zone_ranges = {1: (1, 13), 2: (14, 26), 3: (27, 39)}

    # 近期各区间号码密度
    recent = draws[-window:]

    zone_counts = defaultdict(int)
    for d in recent:
        for n in d:
            for z, (lo, hi) in zone_ranges.items():
                if lo <= n <= hi:
                    zone_counts[z] += 1

    # 理论期望：每期5个号码 × 区间号码数/39
    zone_size = zone_ranges[zone][1] - zone_ranges[zone][0] + 1
    zone_expected_per_draw = safe_divide(zone_size, 39) * 5
    zone_expected = zone_expected_per_draw * window

    zone_observed = zone_counts[zone]

    coverage_ratio = safe_divide(zone_observed, zone_expected, default=1.0)
    coverage_deviation = safe_divide(zone_observed - zone_expected, window)

    return {
        "zone": zone,
        "zone_expected": zone_expected_per_draw,
        "zone_observed": safe_divide(zone_observed, window),
        "zone_coverage_ratio": coverage_ratio,
        "coverage_deviation": coverage_deviation,
    }


def score_coverage(
    draws: List[List[int]],
    number: int,
    window: int = 15,
) -> float:
    """计算号码的不中奖组合覆盖评分

    不中奖概率方向：
    - 号码所在区间近期被高估(coverage_ratio>1) → 该区间号码已经太多
      → 下一期该区间号码更少 → 不中奖概率高 → 高分
    - 号码所在区间近期被低估(coverage_ratio<1) → 该区间号码不够
      → 下一期该区间号码可能补回 → 不中奖概率低 → 低分
    """
    stats = compute_coverage_stats(draws, number, window)
    ratio = stats["zone_coverage_ratio"]

    # 不中奖方向：高估(>1) → 高分，低估(<1) → 低分
    deviation = ratio - 1.0  # 正值=高估, 负值=低估
    score = max(0.0, min(100.0, 50 + deviation * 80))

    return score
