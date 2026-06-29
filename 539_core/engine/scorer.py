"""评分引擎主入口 v2.1 - 8维度不中奖概率评分系统

深度优化后（2026-06-29）的关键发现：
- 3个维度有真正正向信号：momentum(+0.46pp) > recency(+0.26pp) > cluster(+0.18pp)
- 5个维度信号微弱或无：coverage/cooccurrence≈0, freq/int/dev≈-0.07pp
- 最优策略：momentum_heavy (87.49%, +0.31pp超基线87.18%)
- 默认权重已更新为momentum_heavy配置

使用方式：
    scorer = NoWinScorer()
    result = scorer.score(draws, weights={...})
    print(result.exclusion_top10)  # TOP10排除号
"""

from typing import List, Dict, Optional
from datetime import date

from .weights import WeightManager
from .aggregator import compute_all_dimensions, aggregate_scores
from ..config import DEFAULT_WEIGHTS, NUMBERS_RANGE, TOP_LEVELS
from ..data.models import NumberStats, ScoreResult


class NoWinScorer:
    """不中奖概率评分引擎 v2.1"""

    def __init__(self, weights: Dict[str, float] = None):
        self.weight_manager = WeightManager(weights)

    def score(
        self,
        draws: List[List[int]],
        target_draw_id: str = "next",
        target_date: date = None,
        weights: Dict[str, float] = None,
    ) -> ScoreResult:
        """对39个号码进行8维度不中奖概率评分"""
        used_weights = weights or self.weight_manager.get_weights()

        # 为39个号码计算8维度评分
        dimension_scores = []
        for number in range(1, NUMBERS_RANGE + 1):
            dims = compute_all_dimensions(draws, number)
            dimension_scores.append(dims)

        # 聚合为综合评分
        composite_scores = aggregate_scores(dimension_scores, used_weights)

        # 构建NumberStats
        number_stats = []
        for i, number in enumerate(range(1, NUMBERS_RANGE + 1)):
            dims = dimension_scores[i]
            stats = NumberStats(
                number=number,
                total_freq=dims["freq_stats"]["total_freq"],
                recent_freq=dims["rec_stats"]["weighted_recency"],
                recency_gap=dims["rec_stats"]["recency_gap"],
                avg_interval=dims["int_stats"]["avg_interval"],
                interval_variance=dims["int_stats"]["interval_variance"],
                z_score=dims["dev_stats"]["z_score"],
                cluster_score=dims["clu_stats"]["cluster_score"],
                freq_score=dims["freq_score"],
                recency_score=dims["recency_score"],
                interval_score=dims["interval_score"],
                deviation_score=dims["deviation_score"],
                cluster_raw_score=dims["cluster_score"],
                momentum_score=dims["momentum_score"],
                coverage_score=dims["coverage_score"],
                cooccurrence_score=dims["cooccurrence_score"],
                composite_score=composite_scores[i],
            )
            number_stats.append(stats)

        # 排名
        sorted_stats = sorted(number_stats, key=lambda s: s.composite_score, reverse=True)

        exclusion_top2 = [s.number for s in sorted_stats[:2]]
        exclusion_top5 = [s.number for s in sorted_stats[:5]]
        exclusion_top10 = [s.number for s in sorted_stats[:10]]

        sorted_asc = sorted(number_stats, key=lambda s: s.composite_score)
        recommendation_top5 = [s.number for s in sorted_asc[:5]]

        return ScoreResult(
            draw_id=target_draw_id,
            target_date=target_date or date.today(),
            number_stats=number_stats,
            weights_used=used_weights,
            exclusion_top2=exclusion_top2,
            exclusion_top5=exclusion_top5,
            exclusion_top10=exclusion_top10,
            recommendation_top5=recommendation_top5,
        )

    def score_with_optimization(
        self,
        draws: List[List[int]],
        backtest_func,
        target_draw_id: str = "next",
        target_date: date = None,
    ) -> ScoreResult:
        """评分并自动优化权重"""
        result = self.score(draws, target_draw_id, target_date)

        from ..backtest.runner import quick_backtest
        current_accuracy = quick_backtest(draws, self.weight_manager.get_weights())

        optimized_weights = self.weight_manager.optimize(
            current_accuracy, backtest_func, draws
        )

        if optimized_weights != self.weight_manager.get_weights():
            result = self.score(draws, target_draw_id, target_date, optimized_weights)

        return result
