"""维度5：聚类分析

核心逻辑：号码在特定属性维度上的聚类程度影响出现概率
v2.0改进：加入奇偶、大小、区间三维度分布

聚类维度：
1. 奇偶分布：开奖号码通常奇偶比约2:3或3:2，极端分布少见
2. 大小分布：号码01-19为小，20-39为大，通常2:3或3:2
3. 区间分布：[01-13], [14-26], [27-39]三区间，通常2:2:1或类似

评分方向：cluster_score = 不中奖概率方向
- 号码属性维度与"常见聚类模式"不匹配 → 不中奖概率高
- 号码属性维度与"常见聚类模式"匹配 → 不中奖概率低
"""

from typing import List, Dict, Tuple
from collections import Counter
from ..utils import safe_divide


def compute_cluster_stats(
    draws: List[List[int]],
    number: int,
) -> Dict[str, float]:
    """计算单个号码的聚类统计

    分析近期开奖号码在奇偶、大小、区间三个维度上的分布模式，
    判断该号码的属性在这些模式中的适配度。

    Args:
        draws: 历史开奖号码列表
        number: 要分析的号码

    Returns:
        dict: {
            'odd_even_fit': 奇偶适配度（0-1）,
            'big_small_fit': 大小适配度（0-1）,
            'zone_fit': 区间适配度（0-1）,
            'cluster_score': 综合适配度（0-1）,
        }
    """
    if len(draws) < 10:
        # 数据太少，无法统计聚类模式
        return {
            "odd_even_fit": 0.5,
            "big_small_fit": 0.5,
            "zone_fit": 0.5,
            "cluster_score": 0.5,
        }

    # 统计近10期的分布模式
    recent_draws = draws[-10:]

    # 1. 奇偶分布模式
    odd_counts = []
    for d in recent_draws:
        odd_count = sum(1 for n in d if n % 2 == 1)
        odd_counts.append(odd_count)
    avg_odd = safe_divide(sum(odd_counts), len(odd_counts))

    # 2. 大小分布模式（01-19小，20-39大）
    big_counts = []
    for d in recent_draws:
        big_count = sum(1 for n in d if n >= 20)
        big_counts.append(big_count)
    avg_big = safe_divide(sum(big_counts), len(big_counts))

    # 3. 区间分布模式
    zone1_counts = []  # 01-13
    zone2_counts = []  # 14-26
    zone3_counts = []  # 27-39
    for d in recent_draws:
        zone1_counts.append(sum(1 for n in d if 1 <= n <= 13))
        zone2_counts.append(sum(1 for n in d if 14 <= n <= 26))
        zone3_counts.append(sum(1 for n in d if 27 <= n <= 39))
    avg_zone1 = safe_divide(sum(zone1_counts), len(zone1_counts))
    avg_zone2 = safe_divide(sum(zone2_counts), len(zone2_counts))
    avg_zone3 = safe_divide(sum(zone3_counts), len(zone3_counts))

    # 判断该号码的属性在当前模式中的适配度
    # 适配度高 → 该号码属性"需要"被选 → 不中奖概率低
    # 适配度低 → 该号码属性"不需要" → 不中奖概率高

    is_odd = number % 2 == 1
    is_big = number >= 20
    if 1 <= number <= 13:
        zone = 1
    elif 14 <= number <= 26:
        zone = 2
    else:
        zone = 3

    # 奇偶适配度：该号码属于的类别（奇/偶）在近期平均占比
    # 如果是奇数 → 奇数在近期平均出现多少 → 这就是适配度
    if is_odd:
        odd_even_fit = safe_divide(avg_odd, 5)  # 归一化到0-1
    else:
        odd_even_fit = safe_divide(5 - avg_odd, 5)

    # 大小适配度
    if is_big:
        big_small_fit = safe_divide(avg_big, 5)
    else:
        big_small_fit = safe_divide(5 - avg_big, 5)

    # 区间适配度
    zone_avg_map = {1: avg_zone1, 2: avg_zone2, 3: avg_zone3}
    zone_fit = safe_divide(zone_avg_map[zone], 5)

    # 综合适配度
    cluster_score = odd_even_fit * 0.3 + big_small_fit * 0.3 + zone_fit * 0.4

    return {
        "odd_even_fit": odd_even_fit,
        "big_small_fit": big_small_fit,
        "zone_fit": zone_fit,
        "cluster_score": cluster_score,
    }


def score_cluster(
    draws: List[List[int]],
    number: int,
) -> float:
    """计算号码的不中奖聚类评分

    不中奖概率方向：
    cluster_score（适配度）低 → 该号码属性不被"需要" → 不中奖概率高 → 高分
    cluster_score（适配度）高 → 该号码属性被"需要" → 不中奖概率低 → 低分

    映射：score = (1 - cluster_score) * 100
    """
    stats = compute_cluster_stats(draws, number)
    fit = stats["cluster_score"]

    # 不中奖方向：适配度低 → 高分
    score = (1 - fit) * 100

    return max(0.0, min(100.0, score))
