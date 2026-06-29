"""CLI入口 - 539cli命令行工具"""

import argparse
import json
import sys
from datetime import date

from .engine.scorer import NoWinScorer
from .data.storage import DataStorage
from .data.fetcher import fetch_latest
from .backtest.runner import run_backtest, quick_backtest
from .backtest.simulator import compare_strategies, find_best_strategy
from .config import DEFAULT_WEIGHTS, TOP_LEVELS


def cmd_analyze(args):
    """分析命令：评分 + 排名"""
    storage = DataStorage()
    draws = storage.load_draw_numbers()

    if not draws:
        print("❌ 没有历史数据，请先运行 `539cli update`")
        return

    scorer = NoWinScorer()
    latest_draw = storage.get_latest_draw()
    next_draw_id = f"next_after_{latest_draw.draw_id if latest_draw else 'unknown'}"

    result = scorer.score(draws, target_draw_id=next_draw_id)

    print(f"\n{'='*50}")
    print(f"今彩539 不中奖概率分析报告")
    print(f"{'='*50}")
    print(f"数据量: {len(draws)}期")
    if latest_draw:
        print(f"最新开奖: {latest_draw.draw_date} → {latest_draw.numbers}")
    print(f"评分权重: {result.weights_used}")
    print()

    for top_n in TOP_LEVELS:
        excluded = result.get_exclusion(top_n)
        print(f"  TOP{top_n} 排除号: {[f'{n:02d}' for n in excluded]}")

    print()
    recommended = result.get_recommendation(5)
    print(f"  TOP5 关注号: {[f'{n:02d}' for n in recommended]}")

    # 回测概览（全量回测）
    draws_obj = storage.load_draws()  # 用Draw对象列表（runner已支持）
    summary = run_backtest(draws_obj, top_n=10)
    baseline = 1 - 5/39
    print(f"\n  回测准确率: {summary.accuracy_pct:.2f}%")
    print(f"  随机基线:   {baseline*100:.2f}%")
    print(f"  提升幅度:   {summary.improvement_pp:.1f}pp")
    print(f"  完美排除期: {summary.perfect_count}/{summary.total_periods}")
    print(f"{'='*50}")

    # 输出JSON（如需要）
    if args.json:
        output = {
            "exclusion": {
                f"top{n}": result.get_exclusion(n) for n in TOP_LEVELS
            },
            "recommendation": result.get_recommendation(5),
            "weights": result.weights_used,
            "backtest_accuracy": accuracy,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_backtest(args):
    """回测命令"""
    storage = DataStorage()
    draws = storage.load_draw_numbers()

    if not draws:
        print("❌ 没有历史数据")
        return

    weights = DEFAULT_WEIGHTS
    if args.strategy:
        from .backtest.simulator import STRATEGIES
        weights = STRATEGIES.get(args.strategy, DEFAULT_WEIGHTS)

    top_n = args.top or 10
    summary = run_backtest(draws, weights, top_n=top_n)

    print(f"\n{'='*50}")
    print(f"回测验证报告")
    print(f"{'='*50}")
    print(f"策略: {args.strategy or 'default'}")
    print(f"权重: {weights}")
    print(f"回测期数: {summary.total_periods}")
    print(f"排除TOP: {top_n}")
    print()
    print(f"  排除准确率:  {summary.accuracy_pct:.2f}%")
    print(f"  随机基线:    {summary.baseline_pct:.2f}%")
    print(f"  提升幅度:    {summary.improvement_pp:.1f}pp")
    print(f"  完美排除期:  {summary.perfect_count}/{summary.total_periods}")
    print(f"  总误排数:    {summary.total_false_positives}")
    print(f"{'='*50}")


def cmd_strategy(args):
    """策略对比命令"""
    storage = DataStorage()
    draws = storage.load_draw_numbers()

    if not draws:
        print("❌ 没有历史数据")
        return

    top_n = args.top or 10
    results = compare_strategies(draws, top_n=top_n)

    print(f"\n{'='*60}")
    print(f"多策略回测对比")
    print(f"{'='*60}")
    print(f"{'策略':<15} {'准确率':>10} {'基线':>10} {'提升pp':>10} {'完美排除':>10}")
    print("-" * 60)

    for name, summary in sorted(results.items(), key=lambda x: x[1].avg_accuracy, reverse=True):
        print(f"{name:<15} {summary.accuracy_pct:>9.2f}% {summary.baseline_pct:>9.2f}% "
              f"{summary.improvement_pp:>9.1f}pp {summary.perfect_count:>8}/{summary.total_periods}")

    best_name, best_summary = find_best_strategy(draws, top_n=top_n)
    print(f"\n  🏆 最优策略: {best_name} (准确率 {best_summary.accuracy_pct:.2f}%)")
    print(f"{'='*60}")


def cmd_update(args):
    """更新数据命令"""
    print("正在从i539.tw抓取最新数据...")
    new_draws = fetch_latest()

    if not new_draws:
        print("❌ 数据抓取失败，请检查网络或数据源")
        return

    storage = DataStorage()
    existing_count = storage.get_draw_count()

    # 只追加新数据
    added = 0
    for draw in new_draws:
        try:
            storage.save_draw(draw)
            added += 1
        except Exception:
            pass

    new_count = storage.get_draw_count()
    print(f"✅ 数据更新完成: 原有{existing_count}期, 新增{new_count-existing_count}期, 共{new_count}期")

    # 自动分析
    if args.auto_analyze:
        cmd_analyze(args)


def main():
    """CLI主入口"""
    parser = argparse.ArgumentParser(
        prog="539cli",
        description="今彩539 不中奖概率分析工具 v2.0",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # analyze 子命令
    p_analyze = subparsers.add_parser("analyze", help="评分分析")
    p_analyze.add_argument("--top", type=int, default=10, help="排除TOP N")
    p_analyze.add_argument("--json", action="store_true", help="输出JSON格式")

    # backtest 子命令
    p_backtest = subparsers.add_parser("backtest", help="回测验证")
    p_backtest.add_argument("--top", type=int, default=10, help="排除TOP N")
    p_backtest.add_argument("--strategy", type=str, help="使用指定策略")

    # strategy 子命令
    p_strategy = subparsers.add_parser("strategy", help="策略对比")
    p_strategy.add_argument("--top", type=int, default=10, help="排除TOP N")

    # update 子命令
    p_update = subparsers.add_parser("update", help="更新数据")
    p_update.add_argument("--auto-analyze", action="store_true", help="更新后自动分析")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "strategy":
        cmd_strategy(args)
    elif args.command == "update":
        cmd_update(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
