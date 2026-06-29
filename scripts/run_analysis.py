"""Skill快速路径 - 主分析脚本"""

import argparse
import json
import sys
import os

# 确保项目路径在搜索范围
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from importlib import import_module
storage_mod = import_module('539_core.data.storage')
scorer_mod = import_module('539_core.engine.scorer')
backtest_mod = import_module('539_core.backtest.runner')

def main():
    parser = argparse.ArgumentParser(description="今彩539 不中奖概率分析")
    parser.add_argument("--top", type=int, default=10, help="排除TOP N")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    args = parser.parse_args()

    # 加载历史数据
    ds = storage_mod.DataStorage()
    draws = ds.load_draw_numbers()

    if not draws:
        print("没有历史数据，请先运行 update_data.py")
        return

    # 评分
    scorer = scorer_mod.NoWinScorer()
    result = scorer.score(draws)

    # 回测概览（使用全量回测而非quick 30期）
    summary = backtest_mod.run_backtest(draws, top_n=10)
    baseline = 1 - 5/39

    # 输出
    latest = ds.get_latest_draw()

    print(f"\n{'='*50}")
    print(f"今彩539 不中奖概率分析报告")
    print(f"{'='*50}")
    print(f"数据量: {len(draws)}期")
    if latest:
        print(f"最新开奖: {latest.draw_date} → {latest.numbers}")
    print(f"评分权重: {result.weights_used}")
    print()

    excluded = result.get_exclusion(args.top)
    print(f"  TOP{args.top} 排除号: {[f'{n:02d}' for n in excluded]}")

    if args.top >= 10:
        top2 = result.get_exclusion(2)
        top5 = result.get_exclusion(5)
        top10 = result.get_exclusion(10)
        print(f"\n  TOP2 排除号: {[f'{n:02d}' for n in top2]}")
        print(f"  TOP5 排除号: {[f'{n:02d}' for n in top5]}")
        print(f"  TOP10 排除号: {[f'{n:02d}' for n in top10]}")

    recommended = result.get_recommendation(5)
    print(f"\n  TOP5 关注号: {[f'{n:02d}' for n in recommended]}")

    print(f"\n  回测准确率: {summary.accuracy_pct:.2f}%")
    print(f"  随机基线:   {baseline*100:.2f}%")
    print(f"  提升幅度:   {summary.improvement_pp:+.1f}pp")
    print(f"  完美排除期: {summary.perfect_count}/{summary.total_periods}")
    print(f"{'='*50}")
    print("\n⚠️ 提示: 彩票本质随机，分析结果仅供参考，请理性投注")

    if args.json:
        output = {
            "total_draws": len(draws),
            "latest_draw": str(latest.draw_date) if latest else None,
            "exclusion": {
                f"top{n}": result.get_exclusion(n) for n in [2, 5, 10]
            },
            "recommendation": result.get_recommendation(5),
            "weights": result.weights_used,
            "backtest_accuracy": summary.avg_accuracy,
            "baseline": baseline,
        }
        with open(os.path.join(project_root, "reports", "latest_analysis.json"), "w") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nJSON结果已保存至 reports/latest_analysis.json")

if __name__ == "__main__":
    main()
