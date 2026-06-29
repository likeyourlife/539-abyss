"""策略模拟器 v2.1 - 8维度多策略对比回测

深度优化后（2026-06-29）的关键发现：
- momentum独立贡献最强(+0.46pp)
- recency第二(+0.26pp)，cluster第三(+0.18pp)
- coverage/cooccurrence独立贡献≈0，组合时有微弱帮助
- frequency/interval/deviation修正后仍弱(≈-0.07pp)
- 最优策略：momentum_heavy / coverage_heavy 并列87.49%
"""

from typing import List, Dict, Tuple, Union
from ..engine.scorer import NoWinScorer
from ..backtest.runner import run_backtest
from ..data.models import BacktestSummary
from ..config import DEFAULT_WEIGHTS


# 预置策略配置（v2.1: 8维度，基于深度优化）
STRATEGIES = {
    # 最优配置（momentum优先，87.49%）
    "momentum_heavy": DEFAULT_WEIGHTS,

    # coverage优先（并列最优87.49%）
    "coverage_heavy": {
        "frequency": 0.05, "recency": 0.15, "interval": 0.05,
        "deviation": 0.05, "cluster": 0.20, "momentum": 0.15,
        "coverage": 0.30, "cooccurrence": 0.05,
    },

    # 近期+动量组合（87.36%）
    "recency_momentum": {
        "frequency": 0.05, "recency": 0.30, "interval": 0.05,
        "deviation": 0.05, "cluster": 0.10, "momentum": 0.25,
        "coverage": 0.15, "cooccurrence": 0.05,
    },

    # 共现+动量组合（87.41%）
    "social_momentum": {
        "frequency": 0.05, "recency": 0.10, "interval": 0.05,
        "deviation": 0.05, "cluster": 0.10, "momentum": 0.30,
        "coverage": 0.10, "cooccurrence": 0.25,
    },

    # 均衡配置（87.40%）
    "balanced_8": {
        "frequency": 0.125, "recency": 0.125, "interval": 0.125,
        "deviation": 0.125, "cluster": 0.125, "momentum": 0.125,
        "coverage": 0.125, "cooccurrence": 0.125,
    },

    # 旧版默认（87.47%，略低于最优）
    "v2_default": {
        "frequency": 0.10, "recency": 0.20, "interval": 0.10,
        "deviation": 0.10, "cluster": 0.15, "momentum": 0.20,
        "coverage": 0.10, "cooccurrence": 0.05,
    },

    # 信号优先（只用3个有信号的维度，87.16%）
    "signal_only": {
        "frequency": 0.0, "recency": 0.30, "interval": 0.0,
        "deviation": 0.0, "cluster": 0.20, "momentum": 0.30,
        "coverage": 0.15, "cooccurrence": 0.05,
    },
}


def compare_strategies(
    draws: List,
    strategy_names: List[str] = None,
    top_n: int = 10,
) -> Dict[str, BacktestSummary]:
    """对比多种策略的回测表现

    Args:
        draws: 历史数据（Draw对象列表或号码列表）
        strategy_names: 要对比的策略名（默认全部）
        top_n: 排除TOP多少个号

    Returns:
        Dict[str, BacktestSummary]: 各策略回测结果
    """
    if strategy_names is None:
        strategy_names = list(STRATEGIES.keys())

    results = {}
    for name in strategy_names:
        weights = STRATEGIES.get(name, DEFAULT_WEIGHTS)
        summary = run_backtest(draws, weights, top_n=top_n)
        results[name] = summary

    return results


def find_best_strategy(
    draws: List,
    top_n: int = 10,
) -> Tuple[str, BacktestSummary]:
    """找出回测表现最好的策略

    Args:
        draws: 历史数据（Draw对象列表或号码列表）
        top_n: 排除TOP多少个号

    Returns:
        (策略名, 回测结果)
    """
    results = compare_strategies(draws, top_n=top_n)
    best_name = max(results, key=lambda k: results[k].avg_accuracy)
    return best_name, results[best_name]
