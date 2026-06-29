# 今彩539 项目记忆

## 项目目标
构建台湾今彩539投注辅助/分析系统，核心功能：
1. **不中奖概率分析**（重点）：识别大概率不会中奖的号码，帮助排除
2. **选号辅助**：在排除冷号后，推荐值得关注的号码
3. **回溯验证**：验证排除策略的有效性

## 软件架构（v2.1 - 混合架构+8维度优化，2026-06-29）

### 架构选择：方案C（Skill入口 + Agent编排）
- 快速路径（默认）：Skill触发 → 直接Python脚本 → ~10秒出结果
- 深度路径（关键词）：strategy/compare/deep → Agent团队并行 → ~2分钟

### 技术栈
- 核心引擎：Python 3.13 + 539_core包
- 数据存储：SQLite + JSON双轨
- 数据抓取：httpx + BeautifulSoup（i539.tw + lottolyzer）
- CLI：argparse（539cli命令）
- Skill：~/.workbuddy/skills/539-analyzer/SKILL.md
- Python路径：/Users/ioorule/.workbuddy/binaries/python/envs/default/bin/python3

### 系统文件
```
今彩539/
├── 539_core/                    # 核心Python包
│   ├── engine/                  # 8维度评分引擎(v2.1) + 权重管理
│   ├── data/                    # 存储(SQLite/JSON) + 抓取 + 模型
│   ├── backtest/                # 回测运行器 + 策略模拟器
│   ├── report/                  # HTML报告生成
│   ├── config.py                # 全局配置
│   ├── cli.py                   # CLI入口
│   └── utils.py                 # 工具函数
├── scripts/
│   ├── run_analysis.py          # Skill快速路径主脚本
│   ├── run_backtest.py          # 回测脚本
│   ├── update_data.py           # 数据更新脚本
│   ├── daily_push.py            # 每日推送脚本（采集→回测→预测→JSON）
│   ├── weekly_backtest.py       # 每周深度回测+引擎自动学习
│   ├── generate_dashboard_data.py # Dashboard数据生成
│   └── config.py                # 路径配置
├── frontend/
│   └── index.html               # Dashboard前端（Chart.js图表）
├── data/
│   ├── 539.db                   # SQLite数据库
│   ├── 539_all_history.json     # JSON备份
│   └── backtest_history.json    # 回测历史记录
├── reports/                     # 报告输出目录
├── docs/
│   └── dev_plan_v2.md           # 开发计划书
└── 539cli.py                    # CLI入口
```

### 专家包路径
~/.workbuddy/plugins/marketplaces/my-experts/plugins/539-abyss/
- 专家名：伍叁玖分析专家，花名Abyss
- Agent型，categoryId=08-FinanceInvestment

### Skill路径
~/.workbuddy/skills/539-analyzer/SKILL.md（用户级，跨项目可用）

### 自动化
- 539每日分析推送：周一至周六14:00（采集→回测→预测→企业微信推送）
- 539周一深度回测：每周一10:00（策略对比→达标检查→自动微调权重）

### GitHub仓库
https://github.com/likeyourlife/539-abyss（private）
- gh CLI：~/bin/gh（已认证 likeyourlife 账号）

## 数据来源
- 主源：i539.tw（近20期，主页table lau-history结构）
- 备源：lottolyzer（全量，img class="ball" alt属性解析）
- 当前数据：1020期（2023-04-26 ~ 2026-06-27，含i539+lottolyzer最新同步）

## 关键发现（v2.1 深度优化后 2026-06-29）
- **诊断发现**：原5维度中3个（frequency/interval/deviation）方向反了！
  - 冷号被标记为"不中奖概率高"，但均值回归使冷号反而更易出现
  - 热号应该被排除（透支概率），而非冷号
- **深度优化**：各维度独立贡献量化
  - momentum: +0.46pp ← 最强信号（动量趋势）
  - recency: +0.26pp ← 第二强（近期遗忘衰减）
  - cluster: +0.18pp ← 第三强（聚类组合）
  - coverage/cooccurrence: ≈0 ← 独立无信号
  - frequency/interval/deviation: ≈-0.07pp ← 微弱负信号
- 修正+新增3维度后：回测准确率87.49%（超过随机基线87.18%，+0.31pp）
- 最优策略：momentum_heavy(87.49%)/coverage_heavy(87.49%)并列
- DEFAULT_WEIGHTS已更新为momentum_heavy配置
- TOP10排除号：[12,18,35,38,08,19,22,02,06,39]
- TOP5关注号：[29,21,14,10,25]

## 用户偏好
- 关注"不中奖概率"而非"中奖概率"
- 需要TOP2/TOP5/TOP10分层排名
- 需要回溯验证排除策略有效性
- 选择方案C（Skill+Agent混合架构）

## 投注规则
- 01-39中选5个号码，每注50元
- 周一至周六晚8:30开奖
- 头奖800万（对5码），贰奖2万（对4码），参奖300（对3码），肆奖50（对2码）
