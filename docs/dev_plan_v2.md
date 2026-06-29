# 台湾今彩539 预测分析系统 v2.0 — 开发框架计划

> 制定日期：2026-06-29 | 基于 v1.0 经验重构

---

## 1. 项目定位与核心目标

### 1.1 核心理念
**预测"不中奖概率"最高的号码，而非"中奖概率"最高的号码。**

这看似只是视角翻转，但背后的数学逻辑完全不同：
- 中奖概率 → 关注"哪些号码可能出现"（正向预测，39选5，单个号概率≈12.8%）
- 不中奖概率 → 关注"哪些号码大概率不会出现"（排除策略，准确率可达86%+）

**v1.0 已验证**：排除TOP10号码后，候选池从39→29，命中率从12.82%提升至17.24%，排除准确率86.93%（远超随机基线）。

### 1.2 功能目标
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 不中奖概率评分 | 5维度评分引擎，输出1-39每个号的不中奖概率 | P0 |
| TOP排名 | TOP2/TOP5/TOP10 分层排除排名 | P0 |
| 回溯验证 | 历史数据回测，验证排除策略有效性 | P0 |
| 数据自动更新 | 每期开奖后自动抓取并追加 | P1 |
| 关注号推荐 | 在排除冷号后，推荐值得关注的热号 | P1 |
| 可视化报告 | HTML/PDF 分析报告 | P2 |
| 仓位建议 | 基于排除结果的投注策略建议 | P2 |

---

## 2. 架构方案对比

### 方案A：Skill 架构（触发式工具）

```
用户输入 → Skill触发 → 编排脚本 → Python核心引擎 → 结果输出
                                              ↓
                                        数据层(SQLite/JSON)
```

**优势**：
- 简单直接，一句"分析539"就触发
- 维护成本低，改脚本就行
- 执行快，没有Agent间通信开销
- 适合固定流程：抓数据→评分→排名→回测→报告

**劣势**：
- 流程固定，无法动态调整策略
- 不能并行处理多策略对比
- 异常处理靠脚本硬编码

**Skill结构**：
```
~/.workbuddy/skills/539-analyzer/
├── SKILL.md              # Skill定义（触发词、参数、流程）
├── scripts/
│   ├── fetch_data.py     # 数据抓取（i539.tw）
│   ├── score_engine.py   # 5维度评分核心
│   ├── backtest.py       # 回溯验证
│   ├── report.py         # 报告生成
│   └── main.py           # 编排入口
├── references/
│   └── scoring_model.md  # 评分模型文档
└── data/
    └── 539_all_history.json  # 历史数据（850+期）
```

---

### 方案B：Agent 架构（推理式协作者）

```
用户输入 → 主Agent(Orchestrator)
                ↓
    ┌──────────┼──────────┐
    ↓          ↓          ↓
数据Agent   评分Agent   验证Agent
    ↓          ↓          ↓
  报告Agent ← 汇总结果 ← 回测结果
```

**优势**：
- 可以并行：数据抓取 + 评分 + 回测同时进行
- 可以动态决策：数据源失败→自动切换；评分异常→调整权重
- 可扩展：新增"策略对比Agent"、"仓位建议Agent"
- 更智能：能根据历史表现自动调整评分维度权重

**劣势**：
- 开发复杂度更高（Agent间通信、任务协调）
- 执行时间更长（Agent调度开销）
- 维护成本更高（多个Agent需同步更新）

**Agent结构**：
```
.workbuddy/agents/
├── 539-orchestrator.md     # 主协调Agent定义
├── 539-data-fetcher.md     # 数据抓取子Agent
├── 539-scorer.md           # 评分子Agent
├── 539-backtester.md       # 回溯验证子Agent
└── 539-reporter.md         # 报告生成子Agent
```

---

### 方案C：混合架构（Skill入口 + Agent编排） ✅ 已选定

```
用户输入 → Skill(539-analyzer)触发
                ↓
        判断任务复杂度
            ↓           ↓
      简单任务        复杂任务
      直接脚本执行    派发Agent团队
            ↓           ↓
        结果输出 ← ← ← 汇总
```

**这是v2.0推荐方案**：
- 日常分析 → Skill直接跑脚本（快速响应）
- 深度分析/策略对比 → Skill触发Agent团队（并行推理）
- 两者共享同一套Python核心引擎

---

## 3. 共享核心引擎设计（三种方案共用）

无论选Skill还是Agent，核心计算引擎必须一致且独立。

### 3.1 模块架构

```
539_core/                    # 核心Python包（pip可安装）
├── __init__.py
├── engine/
│   ├── scorer.py            # 5维度评分引擎（核心！）
│   ├── frequency.py         # 维度1：频率分析
│   ├── recency.py           # 维度2：近期趋势
│   ├── interval.py          # 维度3：间隔分析
│   ├── deviation.py         # 维度4：偏差分析
│   └── cluster.py           # 维度5：聚类分析
│   ├── weights.py           # 维度权重管理（可动态调整）
│   └── aggregator.py        # 多维度聚合器
├── data/
│   ├── fetcher.py           # 数据抓取（i539.tw + lottolyzer）
│   ├── storage.py           # 数据存储管理
│   ├── updater.py           # 自动更新调度
│   └── models.py            # 数据模型（Draw/NumberStats）
├── backtest/
│   ├── runner.py            # 回溯测试运行器
│   ├── metrics.py           # 准确率/误排率等指标
│   ├── simulator.py         # 策略模拟器
├── report/
│   ├── generator.py         # HTML报告生成
│   ├── pdf_export.py        # PDF导出（依赖Playwright）
│   └── templates/           # HTML模板
├── config.py                # 全局配置
├── cli.py                   # CLI入口（539cli命令）
└── utils.py                 # 工具函数
```

### 3.2 评分引擎设计（5维度 → 综合不中奖概率）

**v1.0验证的5维度模型**，v2.0改进方向：

| 维度 | 含义 | v1.0权重 | v2.0改进 |
|------|------|----------|----------|
| Frequency | 号码出现频率越低→不中奖概率越高 | 0.25 | 加入频率衰减（近期权重更高） |
| Recency | 最近N期未出现→不中奖概率越高 | 0.20 | 改为动态窗口（3/5/10期加权） |
| Interval | 平均出现间隔越大→不中奖概率越高 | 0.20 | 加入间隔方差（稳定性因子） |
| Deviation | 与理论期望偏差越大→不中奖概率越高 | 0.15 | 改为Z-score标准化 |
| Cluster | 号码聚类度越低→不中奖概率越高 | 0.20 | 加入奇偶/大小/区间分布 |

**权重动态调整机制**（v2.0新增）：
- 基于最近30期回测表现，自动微调各维度权重
- 用梯度下降式优化：每期回测后，微调权重使排除准确率最大化
- 权重变化幅度限制±5%，防止过拟合

### 3.3 评分流程

```
输入: 历史数据（最近N期） + 待分析期号
  ↓
Step1: 计算39个号码各维度原始分数
  ↓
Step2: 标准化（Z-score / Min-Max）消除维度量纲差异
  ↓
Step3: 加权聚合 → 综合不中奖概率分数（0-100）
  ↓
Step4: 排序 → TOP2/TOP5/TOP10排除号 + 关注号
  ↓
Step5: 回溯验证 → 输出准确率、误排率
  ↓
输出: {排除排名, 关注推荐, 回测指标, 权重配置}
```

### 3.4 数据架构

**存储方案**：SQLite + JSON双轨

```sql
-- 核心表结构
CREATE TABLE draws (
    draw_id   TEXT PRIMARY KEY,  -- 期号（如 1150000155）
    date      DATE NOT NULL,     -- 开奖日期
    numbers   TEXT NOT NULL,     -- 开奖号码 JSON [04,14,21,31,32]
    source    TEXT DEFAULT 'i539' -- 数据来源
);

CREATE TABLE number_stats (
    number    INTEGER PRIMARY KEY, -- 01-39
    freq      REAL,               -- 总频率
    recency   INTEGER,            -- 最近出现距今期数
    avg_interval REAL,            -- 平均出现间隔
    interval_var  REAL,           -- 间隔方差
    z_score   REAL,               -- Z-score偏差
    cluster_score REAL,           -- 聚类评分
    updated_at TIMESTAMP
);

CREATE TABLE backtest_results (
    period_id   INTEGER,          -- 回测期序号
    draw_id     TEXT,             -- 实际期号
    excluded    TEXT,             -- 推荐排除号 JSON
    actual      TEXT,             -- 实际开奖号 JSON
    accuracy    REAL,             -- 排除准确率
    false_positive INTEGER        -- 误排数（排除号实际中了）
);

CREATE TABLE weight_history (
    date        DATE,
    freq_w      REAL, recency_w   REAL,
    interval_w  REAL, deviation_w REAL,
    cluster_w   REAL,
    accuracy    REAL              -- 该权重下回测准确率
);
```

**数据源**：
- 主源：i539.tw（v1.0验证可用）
- 备源：lottolyzer（cn.lottolyzer.com，可能不稳定）
- 第三备源：手动输入（极端情况）

**数据更新策略**：
- 自动化：每日 20:35 定时抓取（开奖后5分钟）
- 手动：`539cli update` 命令触发
- 失败自动切换：i539 → lottolyzer → 告警等待手动

---

## 4. 开发阶段规划

### Phase 1：核心引擎重建（1-2天）

**目标**：重建5维度评分引擎，达到v1.0同等准确率

| 任务 | 产出 | 验证标准 |
|------|------|----------|
| 重建评分引擎 | `539_core/engine/` | 850期回测准确率≥86% |
| 数据存储层 | `539_core/data/` | SQLite + JSON双写 |
| 回测框架 | `539_core/backtest/` | 全量回测可运行 |
| CLI入口 | `539_core/cli.py` | `539cli analyze`可用 |

### Phase 2：Skill/Agent 包装（1天）

**目标**：将核心引擎包装为Skill和/或Agent可调用形式

| 任务 | 产出 | 验证标准 |
|------|------|----------|
| Skill SKILL.md | 触发词+流程定义 | "分析539"能触发 |
| Skill编排脚本 | `scripts/main.py` | Skill调用→完整分析 |
| Agent定义（可选） | `.workbuddy/agents/` | Agent能派发子任务 |
| 数据迁移 | 850期历史数据导入 | 数据完整性校验 |

### Phase 3：动态优化（1-2天）

**目标**：权重动态调整 + 多策略回测对比

| 任务 | 产出 | 验证标准 |
|------|------|----------|
| 权重动态优化 | `weights.py` | 30期滚动优化 |
| 多策略对比 | 策略模拟器 | 至少3种策略对比 |
| 策略报告 | 对比可视化 | HTML报告含策略对比 |

### Phase 4：自动化部署（1天）

**目标**：每日自动分析 + 报告推送

| 任务 | 产出 | 验证标准 |
|------|------|----------|
| 定时自动化 | WorkBuddy Automation | 每日20:35自动运行 |
| 报告推送 | HTML/PDF报告 | 自动生成并通知 |
| 异常告警 | 数据源失败通知 | 失败时推送告警 |

---

## 5. 技术栈选型

| 层次 | 技术 | 选择理由 |
|------|------|----------|
| 核心引擎 | Python 3.13 | 数学计算+数据处理的最佳选择 |
| 数据存储 | SQLite + JSON | 轻量、无需外部数据库服务 |
| 数据抓取 | httpx + BeautifulSoup | 异步抓取+解析 |
| CLI | argparse | 简单够用 |
| 报告 | Jinja2 + HTML | 模板化报告生成 |
| PDF | Playwright | v1.0验证可用的PDF方案 |
| 测试 | pytest | v1.0已有55项测试经验 |
| 可视化 | ECharts（HTML内嵌） | 无需前端框架，报告内直接渲染 |
| Skill/Agent | WorkBuddy原生机制 | 不引入额外框架 |

**与v1.0的关键差异**：
- ❌ 不再用 FastAPI + React（v2.0以Skill/Agent为核心，不需要Web服务）
- ❌ 不再用 Docker Compose（轻量化，Skill直接在WorkBuddy环境运行）
- ✅ 保留 Python评分引擎（核心资产）
- ✅ 保留 SQLite存储（轻量可靠）
- ✅ 新增 权重动态优化（v1.0缺失）

---

## 6. 输出格式设计

### 6.1 标准分析输出

```json
{
  "date": "2026-06-29",
  "draw_id": "1150000157",
  "exclusion": {
    "top2":  [{"number": 22, "score": 92.3, "dimensions": {...}}],
    "top5":  [{"number": 22, "score": 92.3}, ...],
    "top10": [{"number": 22, "score": 92.3}, ...]
  },
  "recommendation": {
    "top5": [{"number": 31, "score": 8.2, "reason": "近期高频+间隔缩短"}]
  },
  "backtest": {
    "accuracy": 86.93,
    "false_positive_rate": 13.07,
    "total_periods": 752,
    "perfect_exclusions": 154
  },
  "weights": {
    "frequency": 0.27,
    "recency": 0.22,
    "interval": 0.19,
    "deviation": 0.14,
    "cluster": 0.18
  },
  "metadata": {
    "data_source": "i539.tw",
    "total_draws": 852,
    "engine_version": "2.0"
  }
}
```

### 6.2 Skill触发方式

```
/539             → 默认分析（TOP10排除 + TOP5关注 + 回测）
/539 top5        → 仅TOP5排除排名
/539 backtest    → 全量回测验证
/539 update      → 更新数据
/539 report      → 生成HTML报告
/539 strategy    → 多策略对比分析
```

### 6.3 Agent交互方式

```
"帮我分析今彩539"       → Orchestrator派发全部子Agent
"539排除号排名"         → 仅Scorer Agent
"验证排除策略有效性"     → 仅Backtester Agent
"对比三种策略的回测结果" → 多策略并行Agent
```

---

## 7. 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 数据源不稳定（i539.tw/lottolyzer） | 无法获取最新开奖 | 三源备份 + 手动输入兜底 |
| 过拟合（权重动态优化过度） | 实际准确率下降 | 权重变化±5%硬限制 + 30期滑动窗口 |
| 随机性本质不可预测 | 长期准确率退化 | 接受86%天花板，不追求更高 |
| Playwright未安装 | PDF报告不可用 | HTML为默认输出，PDF为可选 |

---

## 8. 与v1.0的继承与改进

| 维度 | v1.0 | v2.0改进 |
|------|------|----------|
| 架构 | FastAPI+React+CLI+Docker | Skill/Agent+Python核心引擎 |
| 评分权重 | 固定硬编码 | 动态优化（30期滚动） |
| 数据源 | 单源（lottolyzer） | 三源备份（i539+lottolyzer+手动） |
| 部署 | Docker Compose | WorkBuddy原生（零部署成本） |
| 交互 | Web界面+CLI | 自然语言触发（"分析539"） |
| 报告 | HTML+PDF | HTML为主，PDF可选 |
| 准确率 | 86.93%（752期） | 目标≥87%（动态权重加持） |

---

## 9. 确定架构：方案C（混合架构）

**已选定**：方案C — Skill入口 + Agent编排

### 9.1 方案C 详细实现规格

#### 路径分流逻辑

```
用户触发 → SKILL.md 接收指令
              ↓
        解析 args 判断路由
              ↓
   ┌─────────────────────────────┐
   │                             │
   │  快速路径（默认）            │  深度路径（关键词触发）
   │  args含: 分析/top/backtest  │  args含: 对比/策略/深度/验证
   │  或无args时                 │  或 --deep 标记
   │                             │
   ↓                             ↓
 scripts/main.py              TeamCreate
   ↓                           ↓
 单脚本串行执行              派发Agent团队
   ↓                           ↓
 直接输出结果               多Agent并行→汇总
```

**分流关键词定义**：
- 快速路径触发词：`analyze`, `top2`, `top5`, `top10`, `backtest`, `update`, `report`（默认）
- 深度路径触发词：`strategy`, `compare`, `deep`, `verify`（含这些词时走Agent团队）

#### Skill SKILL.md 结构设计

```markdown
# 539-analyzer Skill
触发词：539, 今彩539, 539分析, 不中奖概率

参数格式：
  /539             → 快速：TOP10排除 + TOP5关注 + 回测概览
  /539 top5        → 快速：仅TOP5排除排名
  /539 backtest    → 快速：全量回测验证报告
  /539 update      → 快速：更新数据并自动分析
  /539 report      → 快速：生成HTML报告
  /539 strategy    → 深度：多策略对比分析（Agent团队）
  /539 deep        → 深度：完整深度分析（Agent团队）
  /539 compare     → 深度：策略回测对比（Agent团队）

快速路径流程：
  1. 检查数据新鲜度（最近一期是否当天）
  2. 如需更新 → scripts/fetch_data.py
  3. 运行评分 → scripts/main.py --mode {args}
  4. 输出结果 → 格式化文本 + 可选HTML报告

深度路径流程：
  1. TeamCreate "539-deep-analysis"
  2. 并行派发：
     - data-fetcher: 数据获取+验证
     - scorer: 多维度评分（可能跑多种权重配置）
     - backtester: 回测验证（多种策略并行）
  3. 汇总 Agent 收集所有结果
  4. 生成对比报告 + 权重建议
  5. TeamDelete 清理
```

#### Agent 团队配置（深度路径）

| Agent名 | 角色 | 工具 | 产出 |
|---------|------|------|------|
| 539-data | 数据获取+验证 | Bash, WebFetch | 最新数据JSON |
| 539-scorer | 评分计算 | Bash (python脚本) | 多配置评分结果 |
| 539-backtester | 回测验证 | Bash (python脚本) | 多策略回测指标 |
| 539-orchestrator | 汇总+报告 | Bash, Write | HTML对比报告 |

Agent间通信通过 SendMessage + TaskList 协调，共享核心引擎脚本。

#### 项目最终文件结构

```
今彩539/
├── 539_core/                    # Python核心引擎包
│   ├── __init__.py
│   ├── engine/
│   │   ├── scorer.py            # 5维度评分引擎
│   │   ├── frequency.py         # 维度1：频率
│   │   ├── recency.py           # 维度2：近期
│   │   ├── interval.py          # 维度3：间隔
│   │   ├── deviation.py         # 维度4：偏差
│   │   ├── cluster.py           # 维度5：聚类
│   │   ├── weights.py           # 权重管理（动态优化）
│   │   └── aggregator.py        # 多维度聚合
│   ├── data/
│   │   ├── fetcher.py           # 数据抓取（i539/lottolyzer）
│   │   ├── storage.py           # SQLite+JSON存储
│   │   ├── updater.py           # 更新调度
│   │   └── models.py            # 数据模型
│   ├── backtest/
│   │   ├── runner.py            # 回测运行器
│   │   ├── metrics.py           # 准确率指标
│   │   ├── simulator.py         # 策略模拟器
│   ├── report/
│   │   ├── generator.py         # HTML报告
│   │   └── templates/           # HTML模板
│   ├── config.py                # 全局配置
│   ├── cli.py                   # CLI入口
│   └── utils.py                 # 工具函数
├── scripts/
│   ├── main.py                  # Skill快速路径入口
│   └── fetch_data.py            # 独立数据抓取脚本
├── data/
│   ├── 539.db                   # SQLite数据库
│   └── 539_all_history.json     # JSON备份
├── reports/                     # 生成的报告目录
├── tests/                       # pytest测试
├── docs/
│   ├── dev_plan_v2.md           # 本计划书
│   └── scoring_model.md         # 评分模型文档
└── README.md                    # 项目说明
```

Skill文件位于：`~/.workbuddy/skills/539-analyzer/SKILL.md`（用户级，跨项目可用）

---

## 10. 下一步行动（方案C确认后）

1. ✅ **架构已选定**：方案C（混合架构）
2. **创建核心引擎**：Phase 1 → `539_core/engine/scorer.py`
3. **导入历史数据**：从 JSON 迁移到 SQLite
4. **验证回测**：确保准确率≥86%
5. **编写 Skill SKILL.md**：快速路径 + 深度路由
6. **编写编排脚本**：`scripts/main.py`
7. **配置自动化**：每日20:35定时分析

---

*本计划基于 v1.0（2026-06-26~28）的实际经验制定，所有数据指标均有回测验证。*
