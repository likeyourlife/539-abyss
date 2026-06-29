"""工具函数"""

import math
from typing import List


def zscore_normalize(values: List[float]) -> List[float]:
    """Z-score标准化：将原始分数转换为标准正态分布"""
    if not values:
        return []
    mean = sum(values) / len(values)
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
    if std == 0:
        return [0.0] * len(values)
    return [(v - mean) / std for v in values]


def minmax_normalize(values: List[float]) -> List[float]:
    """Min-Max标准化：将值映射到0-1范围"""
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [0.5] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def combination_count(n: int, k: int) -> int:
    """计算C(n,k)组合数"""
    if k > n or k < 0:
        return 0
    if k == 0 or k == n:
        return 1
    result = 1
    for i in range(1, k + 1):
        result = result * (n - i + 1) // i
    return result


def number_padded(n: int) -> str:
    """号码格式化为两位字符串"""
    return f"{n:02d}"


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """安全除法，避免除零"""
    if b == 0:
        return default
    return a / b
