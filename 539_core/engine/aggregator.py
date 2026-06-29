"""多维度聚合器 v2.1 - 8维度评分合并（3修正+2保留+3新增）

维度列表（v2.1）：
修正方向：frequency, interval, deviation（反转评分）
保留有效：recency, cluster（无需修改）
新增维度：momentum(动量), coverage(组合约束), cooccurrence(共现)
"""

from typing import List, Dict
from ..utils import zscore_normalize, minmax_normalize
from ..config import SCORING_METHOD
from .frequency import score_frequency, compute_frequency_stats
from .recency import score_recency, compute_recency_stats
from .interval import score_interval, compute_interval_stats
from .deviation import score_deviation, compute_deviation_stats
from .cluster import score_cluster, compute_cluster_stats
from .momentum import score_momentum, compute_momentum_stats
from .coverage import score_coverage, compute_coverage_stats
from .cooccurrence import score_cooccurrence, compute_cooccurrence_stats


def compute_all_dimensions(
    draws: List[List[int]],
    number: int,
) -> Dict[str, float]:
    """计算单个号码所有8维度的原始评分"""
    freq_stats = compute_frequency_stats(draws, number)
    rec_stats = compute_recency_stats(draws, number)
    int_stats = compute_interval_stats(draws, number)
    dev_stats = compute_deviation_stats(draws, number)
    clu_stats = compute_cluster_stats(draws, number)
    mom_stats = compute_momentum_stats(draws, number)
    cov_stats = compute_coverage_stats(draws, number)
    cooc_stats = compute_cooccurrence_stats(draws, number)

    return {
        "freq_score": score_frequency(draws, number),
        "recency_score": score_recency(draws, number),
        "interval_score": score_interval(draws, number),
        "deviation_score": score_deviation(draws, number),
        "cluster_score": score_cluster(draws, number),
        "momentum_score": score_momentum(draws, number),
        "coverage_score": score_coverage(draws, number),
        "cooccurrence_score": score_cooccurrence(draws, number),
        # 统计详情
        "freq_stats": freq_stats,
        "rec_stats": rec_stats,
        "int_stats": int_stats,
        "dev_stats": dev_stats,
        "clu_stats": clu_stats,
        "mom_stats": mom_stats,
        "cov_stats": cov_stats,
        "cooc_stats": cooc_stats,
    }


def aggregate_scores(
    dimension_scores: List[Dict[str, float]],
    weights: Dict[str, float],
    method: str = SCORING_METHOD,
) -> List[float]:
    """将8维度评分聚合为综合分数

    Args:
        dimension_scores: 39个号码的各维度评分列表
        weights: 各维度权重（8个维度）
        method: 标准化方法

    Returns:
        39个综合评分列表（0-100范围）
    """
    dim_keys = [
        "freq_score", "recency_score", "interval_score",
        "deviation_score", "cluster_score", "momentum_score",
        "coverage_score", "cooccurrence_score",
    ]
    weight_keys = [
        "frequency", "recency", "interval",
        "deviation", "cluster", "momentum",
        "coverage", "cooccurrence",
    ]

    # 收集各维度的原始评分
    raw_scores = {}
    for dk in dim_keys:
        raw_scores[dk] = [d[dk] for d in dimension_scores]

    # 标准化各维度评分
    normed_scores = {}
    for dk in dim_keys:
        raws = raw_scores[dk]
        if method == "zscore":
            normed_scores[dk] = zscore_normalize(raws)
        else:
            normed_scores[dk] = minmax_normalize(raws)

    # 加权聚合
    composite_scores = []
    for i in range(len(dimension_scores)):
        composite = 0.0
        for dk, wk in zip(dim_keys, weight_keys):
            w = weights.get(wk, 0.0)
            composite += normed_scores[dk][i] * w
        composite_scores.append(composite)

    # 映射回0-100范围
    if composite_scores:
        min_c = min(composite_scores)
        max_c = max(composite_scores)
        if max_c > min_c:
            composite_scores = [
                (c - min_c) / (max_c - min_c) * 100
                for c in composite_scores
            ]
        else:
            composite_scores = [50.0] * len(composite_scores)

    return composite_scores
