"""权重管理器 - 动态优化评分维度权重

v2.0核心改进：基于回测表现自动微调权重

优化策略：
1. 使用最近30期回测准确率作为优化目标
2. 梯度下降式微调：每期尝试微调权重，看准确率是否提升
3. 权重变化幅度硬限制±5%，防止过拟合
4. 权重总和始终=1（归一化约束）
"""

from typing import Dict, List, Tuple
from copy import deepcopy
from ..config import DEFAULT_WEIGHTS, WEIGHT_OPTIMIZATION_WINDOW, WEIGHT_CHANGE_LIMIT


class WeightManager:
    """权重管理器"""

    def __init__(self, initial_weights: Dict[str, float] = None):
        self.weights = deepcopy(initial_weights or DEFAULT_WEIGHTS)
        self._normalize_weights()
        self.history: List[Dict] = []  # 权重调整历史

    def _normalize_weights(self):
        """确保权重总和=1"""
        total = sum(self.weights.values())
        if total > 0:
            for key in self.weights:
                self.weights[key] = self.weights[key] / total

    def get_weights(self) -> Dict[str, float]:
        """获取当前权重"""
        return deepcopy(self.weights)

    def optimize(
        self,
        accuracy_with_current: float,
        backtest_func,
        draws: List[List[int]],
        window: int = WEIGHT_OPTIMIZATION_WINDOW,
    ) -> Dict[str, float]:
        """基于回测准确率优化权重

        尝试5个方向的微调，选择准确率最高的方向：
        - 每个维度各尝试+0.03和-0.03
        - 遍历所有组合，保留最优

        Args:
            accuracy_with_current: 当前权重下的回测准确率
            backtest_func: 回测函数，接受draws和weights，返回准确率
            draws: 历史数据
            window: 优化窗口期数

        Returns:
            优化后的权重
        """
        best_weights = deepcopy(self.weights)
        best_accuracy = accuracy_with_current

        step = 0.03  # 每次微调步长
        dimensions = list(self.weights.keys())

        # 对每个维度尝试增加和减少
        for dim in dimensions:
            for delta in [step, -step]:
                trial_weights = deepcopy(self.weights)
                trial_weights[dim] += delta

                # 从其他维度均匀扣减，保持总和=1
                other_dims = [d for d in dimensions if d != dim]
                per_other = delta / len(other_dims)
                for other in other_dims:
                    trial_weights[other] -= per_other

                # 检查权重是否在合理范围内
                if any(w < 0.05 for w in trial_weights.values()):
                    continue  # 权重不能低于0.05
                if abs(trial_weights[dim] - self.weights[dim]) > WEIGHT_CHANGE_LIMIT:
                    continue  # 单次变化不超过限制

                # 归一化
                total = sum(trial_weights.values())
                for key in trial_weights:
                    trial_weights[key] /= total

                # 回测验证
                trial_accuracy = backtest_func(draws, trial_weights, window)

                if trial_accuracy > best_accuracy:
                    best_weights = trial_weights
                    best_accuracy = trial_accuracy

        # 记录优化历史
        self.history.append({
            "previous_weights": deepcopy(self.weights),
            "optimized_weights": deepcopy(best_weights),
            "previous_accuracy": accuracy_with_current,
            "optimized_accuracy": best_accuracy,
            "improvement": best_accuracy - accuracy_with_current,
        })

        # 应用最优权重
        if best_accuracy > accuracy_with_current:
            self.weights = best_weights

        return self.get_weights()

    def reset(self):
        """重置为默认权重"""
        self.weights = deepcopy(DEFAULT_WEIGHTS)
        self._normalize_weights()
