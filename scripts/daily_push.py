"""每日539分析推送脚本 - 采集数据→回测→评分→形成预测→输出JSON"""

import json
import sys
import os
import time
from datetime import datetime, date

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from importlib import import_module

storage_mod = import_module('539_core.data.storage')
fetcher_mod = import_module('539_core.data.fetcher')
scorer_mod = import_module('539_core.engine.scorer')
backtest_mod = import_module('539_core.backtest.runner')

def run_daily_analysis():
    """执行每日分析流程"""
    ds = storage_mod.DataStorage()

    # 1. 采集前日开奖数据
    print("1. 采集数据...")
    recent = fetcher_mod.fetch_i539_recent()
    if recent:
        ds.save_draws(recent)
        print(f"   i539近20期已更新，最新: {recent[-1].draw_date}")
    
    # 也从lottolyzer补充更多数据
    for page in range(1, 3):
        page_data = fetcher_mod.fetch_lottolyzer_page(page)
        if page_data:
            ds.save_draws(page_data)
    print("   lottolyzer数据已同步")

    # 2. 加载全量数据
    draws = ds.load_draw_numbers()
    print(f"2. 数据量: {len(draws)}期")

    # 3. 回测验证
    print("3. 回测验证...")
    summary = backtest_mod.run_backtest(draws, top_n=10)
    baseline = 1 - 5/39
    accuracy_pct = summary.avg_accuracy * 100
    baseline_pct = baseline * 100
    improvement = summary.improvement_pp
    
    print(f"   准确率: {accuracy_pct:.2f}% (基线{baseline_pct:.2f}%, {improvement:+.2f}pp)")
    
    # 如果准确率低于87%，触发权重微调（简易版）
    if accuracy_pct < 87.0:
        print("   ⚠️ 准确率低于87%，建议手动检查权重")
    
    # 4. 评分生成预测
    print("4. 生成预测...")
    scorer = scorer_mod.NoWinScorer()
    result = scorer.score(draws)
    
    top2 = result.get_exclusion(2)
    top5 = result.get_exclusion(5)
    top10 = result.get_exclusion(10)
    recommended = result.get_recommendation(5)
    
    latest = ds.get_latest_draw()
    
    # 5. 输出JSON结果
    output = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "total_draws": len(draws),
        "latest_draw": {
            "date": str(latest.draw_date) if latest else None,
            "numbers": latest.numbers if latest else None,
        },
        "prediction": {
            "top2_exclude": top2,
            "top5_exclude": top5,
            "top10_exclude": top10,
            "top5_recommend": recommended,
        },
        "backtest": {
            "accuracy_pct": round(accuracy_pct, 2),
            "baseline_pct": round(baseline_pct, 2),
            "improvement_pp": round(improvement, 2),
            "perfect_count": summary.perfect_count,
            "total_periods": summary.total_periods,
        },
        "weights": result.weights_used,
        "engine_version": "2.1",
    }
    
    # 保存JSON
    json_path = os.path.join(project_root, "reports", f"daily_{date.today().isoformat()}.json")
    with open(json_path, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"5. 结果已保存: {json_path}")

    # 6. 更新GitHub Pages Dashboard数据
    print("6. 更新GitHub Pages...")
    gen_script = os.path.join(project_root, "scripts", "generate_dashboard_data.py")
    push_script = os.path.join(project_root, "scripts", "push_to_pages.py")
    try:
        os.system(f"/Users/ioorule/.workbuddy/binaries/python/envs/default/bin/python3 {gen_script}")
        os.system(f"/Users/ioorule/.workbuddy/binaries/python/envs/default/bin/python3 {push_script}")
    except Exception as e:
        print(f"   GitHub Pages更新失败: {e}")

    return output

if __name__ == "__main__":
    result = run_daily_analysis()
    print("\n" + "="*50)
    print(f"今彩539 每日分析推送 ({date.today()})")
    print("="*50)
    print(f"最新开奖: {result['latest_draw']['date']} → {result['latest_draw']['numbers']}")
    print()
    print(f"  TOP2 排除: {[f'{n:02d}' for n in result['prediction']['top2_exclude']]}")
    print(f"  TOP5 排除: {[f'{n:02d}' for n in result['prediction']['top5_exclude']]}")
    print(f"  TOP10 排除: {[f'{n:02d}' for n in result['prediction']['top10_exclude']]}")
    print(f"  TOP5 关注: {[f'{n:02d}' for n in result['prediction']['top5_recommend']]}")
    print()
    print(f"  回测准确率: {result['backtest']['accuracy_pct']}% ({result['backtest']['improvement_pp']:+.2f}pp)")
    print("="*50)
