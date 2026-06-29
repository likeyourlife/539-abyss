"""回测验证脚本"""

import argparse
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from importlib import import_module
storage_mod = import_module('539_core.data.storage')
backtest_mod = import_module('539_core.backtest.runner')
simulator_mod = import_module('539_core.backtest.simulator')

def main():
    parser = argparse.ArgumentParser(description="今彩539 回测验证")
    parser.add_argument("--top", type=int, default=10, help="排除TOP N")
    parser.add_argument("--strategy", type=str, default=None, help="指定策略名")
    parser.add_argument("--compare", action="store_true", help="多策略对比")
    args = parser.parse_args()

    ds = storage_mod.DataStorage()
    draws = ds.load_draw_numbers()

    if not draws:
        print("没有历史数据")
        return

    if args.compare:
        # 多策略对比
        results = simulator_mod.compare_strategies(draws, top_n=args.top)
        best_name, best_summary = simulator_mod.find_best_strategy(draws, top_n=args.top)

        print(f"\n{'='*60}")
        print(f"多策略回测对比")
        print(f"{'='*60}")
        print(f"{'策略':<15} {'准确率':>10} {'基线':>10} {'提升pp':>10} {'完美排除':>10}")
        print("-" * 60)

        for name, summary in sorted(results.items(), key=lambda x: x[1].avg_accuracy, reverse=True):
            print(f"{name:<15} {summary.accuracy_pct:>9.2f}% {summary.baseline_pct:>9.2f}% "
                  f"{summary.improvement_pp:>9.1f}pp {summary.perfect_count:>8}/{summary.total_periods}")

        print(f"\n最优策略: {best_name} (准确率 {best_summary.accuracy_pct:.2f}%)")
        print(f"{'='*60}")
    else:
        # 单策略回测
        weights = None
        strategy_name = "default"
        if args.strategy:
            weights = simulator_mod.STRATEGIES.get(args.strategy)
            strategy_name = args.strategy

        summary = backtest_mod.run_backtest(draws, weights, top_n=args.top)

        print(f"\n{'='*50}")
        print(f"回测验证报告")
        print(f"{'='*50}")
        print(f"策略: {strategy_name}")
        print(f"回测期数: {summary.total_periods}")
        print(f"排除TOP: {args.top}")
        print()
        print(f"  排除准确率:  {summary.accuracy_pct:.2f}%")
        print(f"  随机基线:    {summary.baseline_pct:.2f}%")
        print(f"  提升幅度:    {summary.improvement_pp:.1f}pp")
        print(f"  完美排除期:  {summary.perfect_count}/{summary.total_periods}")
        print(f"  总误排数:    {summary.total_false_positives}")
        print(f"{'='*50}")

if __name__ == "__main__":
    main()
