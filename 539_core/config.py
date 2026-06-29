"""全局配置 - 今彩539系统参数"""

# 彩票规则
NUMBERS_RANGE = 39       # 号码范围 01-39
PICK_COUNT = 5           # 每期选5个号码
TOTAL_COMBINATIONS = 575757  # C(39,5) 总组合数

# 评分维度权重（v2.1: 8维度，基于深度优化搜索结果）
# 搜索发现：momentum/recency/cluster是唯一3个有正向信号的维度
# momentum独立贡献+0.46pp，是最强维度
# 最优策略：momentum_heavy/coverage_heavy并列87.49%（+0.31pp超基线）
DEFAULT_WEIGHTS = {
    "frequency": 0.05,    # 修正后弱维度（独立贡献-0.06pp）
    "recency": 0.15,      # 第二强维度（独立贡献+0.26pp）
    "interval": 0.05,     # 修正后弱维度（独立贡献-0.09pp）
    "deviation": 0.05,    # 修正后弱维度（独立贡献-0.08pp）
    "cluster": 0.10,      # 第三强维度（独立贡献+0.18pp）
    "momentum": 0.40,     # 最强维度（独立贡献+0.46pp）
    "coverage": 0.15,     # 组合约束（独立贡献≈0，组合时有微弱帮助）
    "cooccurrence": 0.05, # 共现分析（独立贡献≈0，组合时有微弱帮助）
}

# 动态优化参数
WEIGHT_OPTIMIZATION_WINDOW = 30   # 滚动优化窗口期数
WEIGHT_CHANGE_LIMIT = 0.05        # 单次权重变化最大幅度

# 评分标准化方法
SCORING_METHOD = "zscore"  # zscore | minmax

# 数据源配置
DATA_SOURCES = {
    "primary": {
        "name": "i539",
        "url": "https://i539.tw/history",
        "format": "html",
    },
    "fallback": {
        "name": "lottolyzer",
        "url": "https://cn.lottolyzer.com/539/history",
        "format": "html",
    },
}

# 回测参数
BACKTEST_WARMUP = 100  # 回测前100期作为统计基线，不参与评分验证

# 存储路径（相对于项目根目录）
DATA_DIR = "data"
DB_FILE = "data/539.db"
JSON_BACKUP = "data/539_all_history.json"
REPORTS_DIR = "reports"

# TOP排名层数
TOP_LEVELS = [2, 5, 10]
