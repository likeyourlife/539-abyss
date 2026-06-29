"""回测指标计算"""

from typing import List
from ..data.models import BacktestResult, BacktestSummary
from ..utils import safe_divide


def calculate_metrics(results: List[BacktestResult], top_n: int = 10) -> BacktestSummary:
    """从回测结果列表计算汇总指标

    Args:
        results: 回测结果列表
        top_n: 排除号数量

    Returns:
        BacktestSummary: 汇总指标
    """
    if not results:
        return BacktestSummary()

    test_periods = len(results)
    total_fp = sum(r.false_positives for r in results)
    perfect_count = sum(1 for r in results if r.is_perfect)
    total_excluded_slots = test_periods * top_n

    avg_accuracy = safe_divide(
        total_excluded_slots - total_fp,
        total_excluded_slots,
    )

    baseline_accuracy = 1 - safe_divide(5, 39)

    improvement_pp = (avg_accuracy - baseline_accuracy) * 100

    return BacktestSummary(
        total_periods=test_periods,
        total_false_positives=total_fp,
        perfect_count=perfect_count,
        avg_accuracy=avg_accuracy,
        baseline_accuracy=baseline_accuracy,
        improvement_pp=improvement_pp,
    )


def period_accuracy(result: BacktestResult, top_n: int = 10) -> float:
    """单期排除准确率"""
    excluded_count = len(result.excluded)
    if excluded_count == 0:
        return 1.0
    return safe_divide(
        excluded_count - result.false_positives,
        excluded_count,
    )
