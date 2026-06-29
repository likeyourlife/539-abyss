"""数据模型 - 今彩539核心数据结构"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class Draw:
    """一期开奖记录"""
    draw_id: str              # 期号（如 1150000155）
    draw_date: date           # 开奖日期
    numbers: List[int]        # 开奖号码（5个，如 [4, 14, 21, 31, 32]）
    source: str = "i539"      # 数据来源

    def __post_init__(self):
        # 确保号码排序且在有效范围内
        self.numbers = sorted(self.numbers)
        assert len(self.numbers) == 5, f"每期必须5个号码，实际{len(self.numbers)}"
        assert all(1 <= n <= 39 for n in self.numbers), f"号码必须在01-39范围内"


@dataclass
class NumberStats:
    """单个号码的统计数据"""
    number: int                # 号码（1-39）
    total_freq: float = 0.0    # 总出现频率（出现次数/总期数）
    recent_freq: float = 0.0   # 近N期出现频率
    recency_gap: int = 0       # 最近出现距今多少期（0=上期刚出现）
    avg_interval: float = 0.0  # 平均出现间隔
    interval_variance: float = 0.0  # 间隔方差（稳定性指标）
    z_score: float = 0.0       # Z-score偏差
    cluster_score: float = 0.0  # 聚类评分
    # 各维度原始评分（不中奖概率方向）
    freq_score: float = 0.0
    recency_score: float = 0.0
    interval_score: float = 0.0
    deviation_score: float = 0.0
    cluster_raw_score: float = 0.0
    # v2.1新增维度评分
    momentum_score: float = 0.0     # 动量评分
    coverage_score: float = 0.0     # 组合约束评分
    cooccurrence_score: float = 0.0 # 共现评分
    # 综合评分
    composite_score: float = 0.0  # 综合不中奖概率（0-100）


@dataclass
class ScoreResult:
    """评分结果"""
    draw_id: str                          # 目标期号
    target_date: date                     # 目标日期
    number_stats: List[NumberStats]       # 39个号码的完整统计
    weights_used: dict                    # 本次评分使用的权重
    # 排名结果
    exclusion_top2: List[int] = field(default_factory=list)
    exclusion_top5: List[int] = field(default_factory=list)
    exclusion_top10: List[int] = field(default_factory=list)
    recommendation_top5: List[int] = field(default_factory=list)

    def get_exclusion(self, top_n: int) -> List[int]:
        """获取TOP N排除号"""
        sorted_stats = sorted(self.number_stats, key=lambda s: s.composite_score, reverse=True)
        return [s.number for s in sorted_stats[:top_n]]

    def get_recommendation(self, top_n: int) -> List[int]:
        """获取TOP N关注号（不中奖概率最低的号）"""
        sorted_stats = sorted(self.number_stats, key=lambda s: s.composite_score)
        return [s.number for s in sorted_stats[:top_n]]


@dataclass
class BacktestResult:
    """单期回测结果"""
    period_index: int          # 回测期序号
    draw_id: str               # 实际期号
    draw_date: date            # 实际日期
    excluded: List[int]        # 推荐排除号
    actual: List[int]          # 实际开奖号
    false_positives: int = 0   # 误排数（排除号中实际出现了的）
    is_perfect: bool = False   # 完美排除（排除号无一命中）

    def __post_init__(self):
        self.false_positives = len(set(self.excluded) & set(self.actual))
        self.is_perfect = self.false_positives == 0


@dataclass
class BacktestSummary:
    """回测汇总"""
    total_periods: int = 0          # 回测总期数
    total_false_positives: int = 0  # 总误排数
    perfect_count: int = 0          # 完美排除期数
    avg_accuracy: float = 0.0       # 平均排除准确率
    baseline_accuracy: float = 0.0  # 随机基线准确率
    improvement_pp: float = 0.0     # 相对基线提升百分点

    @property
    def accuracy_pct(self) -> float:
        return self.avg_accuracy * 100

    @property
    def baseline_pct(self) -> float:
        return self.baseline_accuracy * 100
