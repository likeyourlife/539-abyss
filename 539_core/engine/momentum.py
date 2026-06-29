"""新增维度6：动量检测（Momentum）

核心逻辑：号码近期出现频率相对于长期频率的变化趋势
- 正动量（近期频率 > 长期频率）→ 号码处于上升趋势 → 不中奖概率低
- 负动量（近期频率 < 长期频率）→ 号码处于下降趋势 → 不中奖概率高
- 零动量 → 无明显趋势

这是真正有信号的方向！因为：
- 近期频率变化捕捉了短期的"热/冷"转换
- 长期频率作为基线参考，消除历史累积的偏差
- 动量指标能识别"正在变热"的号码（排除它们不合算）
  和"正在变冷"的号码（排除它们是正确的）
"""

from typing import List, Dict
from ..utils import safe_divide


def compute_momentum_stats(
    draws: List[List[int]],
    number: int,
    short_window: int = 10,
    long_window: int = 50,
) -> Dict[str, float]:
    """计算号码的动量统计

    Args:
        draws: 历史开奖号码列表
        number: 要分析的号码
        short_window: 短期窗口期数
        long_window: 长期窗口期数

    Returns:
        dict: {
            'short_freq': 近N期出现频率,
            'long_freq': 远N期出现频率,
            'momentum': 动量值（短期频率 - 长期频率）,
            'momentum_ratio': 动量比率（短期/长期）,
        }
    """
    total_draws = len(draws)
    if total_draws < long_window:
        return {"short_freq": 0.0, "long_freq": 0.0,
                "momentum": 0.0, "momentum_ratio": 1.0}

    # 短期频率（最近short_window期）
    recent = draws[-short_window:]
    short_count = sum(1 for d in recent if number in d)
    short_freq = safe_divide(short_count, short_window)

    # 长期频率（最近long_window期）
    long_range = draws[-long_window:]
    long_count = sum(1 for d in long_range if number in d)
    long_freq = safe_divide(long_count, long_window)

    # 动量值
    momentum = short_freq - long_freq

    # 动量比率（短期/长期）
    momentum_ratio = safe_divide(short_freq, long_freq, default=1.0)

    return {
        "short_freq": short_freq,
        "long_freq": long_freq,
        "momentum": momentum,
        "momentum_ratio": momentum_ratio,
    }


def score_momentum(
    draws: List[List[int]],
    number: int,
    short_window: int = 10,
    long_window: int = 50,
) -> float:
    """计算号码的不中奖动量评分

    不中奖概率方向：
    - 负动量（近期频率下降）→ 号码正在变冷 → 不中奖概率高 → 高分
    - 正动量（近期频率上升）→ 号码正在变热 → 不中奖概率低 → 低分

    这个维度的信号应该比纯频率更有效，
    因为它捕捉的是"变化趋势"而非"绝对水平"
    """
    stats = compute_momentum_stats(draws, number, short_window, long_window)
    momentum = stats["momentum"]

    # 不中奖概率方向：负动量 → 高分，正动量 → 低分
    # momentum范围大约 [-0.10, +0.10]
    # 负值（变冷）→ 高分（排除），正值（变热）→ 低分（保留）
    score = max(0.0, min(100.0, 50 - momentum * 300))

    return score
