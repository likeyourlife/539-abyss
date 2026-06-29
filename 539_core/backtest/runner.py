"""回测运行器 - 验证排除策略的历史有效性

v2.1更新：支持Draw对象和纯号码列表两种输入
"""

from typing import List, Dict, Union
from datetime import date
from ..engine.scorer import NoWinScorer
from ..config import NUMBERS_RANGE, PICK_COUNT, BACKTEST_WARMUP
from ..data.models import Draw, BacktestResult, BacktestSummary
from ..utils import safe_divide, combination_count


def _extract_numbers(draw_item) -> List[int]:
    """从Draw对象或纯号码列表中提取号码"""
    if isinstance(draw_item, Draw):
        return draw_item.numbers
    elif isinstance(draw_item, list):
        return draw_item
    else:
        raise TypeError(f"不支持的数据类型: {type(draw_item)}")


def _to_numbers_list(draws: List) -> List[List[int]]:
    """将Draw对象列表转为纯号码列表（引擎需要）"""
    return [_extract_numbers(d) for d in draws]


def run_backtest(
    draws: List,
    weights: Dict[str, float] = None,
    warmup: int = BACKTEST_WARMUP,
    top_n: int = 10,
) -> BacktestSummary:
    """运行完整回测

    对历史数据进行逐期评分并验证排除准确率：
    1. 前warmup期作为基线数据（不参与验证）
    2. 从warmup期开始，逐期使用之前的数据评分
    3. 检查排除号是否命中实际开奖号

    Args:
        draws: 历史数据（Draw对象列表或号码列表）
        weights: 评分权重
        warmup: 预热期数（前N期不参与验证）
        top_n: 排除TOP多少个号

    Returns:
        BacktestSummary: 回测汇总结果
    """
    scorer = NoWinScorer(weights)
    total_draws = len(draws)

    if total_draws <= warmup:
        return BacktestSummary(
            total_periods=0,
            avg_accuracy=0.0,
            baseline_accuracy=0.0,
        )

    results = []
    test_periods = total_draws - warmup

    for i in range(warmup, total_draws):
        # 将之前的Draw对象转为号码列表供引擎使用
        history_numbers = _to_numbers_list(draws[:i])
        actual_numbers = _extract_numbers(draws[i])  # 本期实际开奖号

        score_result = scorer.score(
            history_numbers,
            target_draw_id=f"backtest_{i}",
            target_date=date.min,  # 回测不需要真实日期
        )

        # 排除号
        excluded = score_result.get_exclusion(top_n)

        # 验证
        false_positives = len(set(excluded) & set(actual_numbers))
        is_perfect = false_positives == 0

        results.append(BacktestResult(
            period_index=i,
            draw_id=f"backtest_{i}",
            draw_date=date.min,
            excluded=excluded,
            actual=actual_numbers,
            false_positives=false_positives,
            is_perfect=is_perfect,
        ))

    # 计算汇总指标
    total_fp = sum(r.false_positives for r in results)
    perfect_count = sum(1 for r in results if r.is_perfect)
    total_excluded_slots = test_periods * top_n

    avg_accuracy = safe_divide(
        total_excluded_slots - total_fp,
        total_excluded_slots,
    )

    baseline_accuracy = 1 - safe_divide(PICK_COUNT, NUMBERS_RANGE)
    improvement_pp = (avg_accuracy - baseline_accuracy) * 100

    return BacktestSummary(
        total_periods=test_periods,
        total_false_positives=total_fp,
        perfect_count=perfect_count,
        avg_accuracy=avg_accuracy,
        baseline_accuracy=baseline_accuracy,
        improvement_pp=improvement_pp,
    )


def quick_backtest(
    draws: List,
    weights: Dict[str, float] = None,
    window: int = 30,
) -> float:
    """快速回测（仅最近window期），用于权重优化

    Args:
        draws: 历史数据（Draw对象或号码列表）
        weights: 评分权重
        window: 回测窗口期数

    Returns:
        最近window期的排除准确率
    """
    total_draws = len(draws)
    warmup = max(BACKTEST_WARMUP, total_draws - window)

    if total_draws <= warmup:
        return 0.0

    summary = run_backtest(draws, weights, warmup=warmup, top_n=10)
    return summary.avg_accuracy
