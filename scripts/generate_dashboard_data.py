"""539 Dashboard API - 提供前端展示所需的所有数据"""

import json
import sys
import os
from datetime import datetime, date, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from importlib import import_module

storage_mod = import_module('539_core.data.storage')
scorer_mod = import_module('539_core.engine.scorer')
backtest_mod = import_module('539_core.backtest.runner')
simulator_mod = import_module('539_core.backtest.simulator')


def get_dashboard_data():
    """获取Dashboard所需的所有数据"""
    ds = storage_mod.DataStorage()
    draws = ds.load_draw_numbers()
    latest = ds.get_latest_draw()
    
    # 1. 当日预测分析结果
    scorer = scorer_mod.NoWinScorer()
    result = scorer.score(draws)
    
    top2 = result.get_exclusion(2)
    top4 = result.get_exclusion(4)
    top5 = result.get_exclusion(5)
    top10 = result.get_exclusion(10)
    recommended = result.get_recommendation(5)
    
    # 获取每个号码的具体评分（概率数据）
    number_scores = []
    for ns in result.number_stats:
        number_scores.append({
            "number": ns.number,
            "composite_score": round(ns.composite_score, 4),
            "is_excluded_top2": ns.number in top2,
            "is_excluded_top5": ns.number in top5,
            "is_excluded_top10": ns.number in top10,
            "is_recommended": ns.number in recommended,
            "momentum_score": round(ns.momentum_score, 4) if hasattr(ns, 'momentum_score') else 0,
            "recency_score": round(ns.recency_score, 4),
            "cluster_score": round(ns.cluster_raw_score if hasattr(ns, 'cluster_raw_score') else ns.cluster_score, 4),
        })
    number_scores.sort(key=lambda x: x["composite_score"], reverse=True)
    
    # 2. 回测准确率数据
    summary = backtest_mod.run_backtest(draws, top_n=10)
    baseline = 1 - 5/39
    
    # 3. 回测历史（月度准确率）
    history_path = os.path.join(project_root, "data", "backtest_history.json")
    backtest_history = []
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            backtest_history = json.load(f)
    
    # 4. 计算每日准确率（近一个月）
    daily_accuracy = []
    # 取最近30期做逐期回测
    warmup = len(draws) - 30
    if warmup < 100:
        warmup = 100
    
    for i in range(warmup, len(draws)):
        history = draws[:i]
        actual = draws[i]
        result_i = scorer_mod.NoWinScorer().score(history)
        excluded = result_i.get_exclusion(10)
        fp = len(set(excluded) & set(actual))
        accuracy = (10 - fp) / 10
        daily_accuracy.append({
            "period": i,
            "accuracy_pct": round(accuracy * 100, 2),
            "excluded": excluded,
            "actual": actual,
        })
    
    # 5. 月度准确率（近12个月）
    monthly_accuracy = []
    draws_with_dates = ds.load_draws()  # Draw对象（有日期）
    
    for month_offset in range(12):
        target_month = date.today() - timedelta(days=30 * (month_offset + 1))
        target_month_start = date(target_month.year, target_month.month, 1)
        target_month_end = date(target_month.year, target_month.month + 1 if target_month.month < 12 else 1, 1) if target_month.month < 12 else date(target_month.year + 1, 1, 1)
        
        month_draws = [d for d in draws_with_dates if target_month_start <= d.draw_date < target_month_end]
        if len(month_draws) < 10:
            continue
        
        # 对这个月的每期做回测
        total_accuracy = 0
        count = 0
        for d in month_draws:
            idx = draws_with_dates.index(d)
            if idx < 100:
                continue
            history_nums = [dd.numbers for dd in draws_with_dates[:idx]]
            actual = d.numbers
            result_m = scorer_mod.NoWinScorer().score(history_nums)
            excluded_m = result_m.get_exclusion(10)
            fp_m = len(set(excluded_m) & set(actual))
            total_accuracy += (10 - fp_m) / 10
            count += 1
        
        if count > 0:
            monthly_accuracy.append({
                "month": target_month_start.strftime("%Y-%m"),
                "accuracy_pct": round(total_accuracy / count * 100, 2),
                "draws_count": count,
                "baseline_pct": round(baseline * 100, 2),
            })
    
    monthly_accuracy.reverse()
    
    # 组装Dashboard数据
    dashboard = {
        "generated_at": datetime.now().isoformat(),
        "total_draws": len(draws),
        "latest_draw": {
            "date": str(latest.draw_date) if latest else None,
            "numbers": latest.numbers if latest else None,
        },
        "prediction": {
            "top2": [{"number": n, "label": f"{n:02d}"} for n in top2],
            "top4": [{"number": n, "label": f"{n:02d}"} for n in top4],
            "top5": [{"number": n, "label": f"{n:02d}"} for n in top5],
            "top10": [{"number": n, "label": f"{n:02d}"} for n in top10],
            "recommended": [{"number": n, "label": f"{n:02d}"} for n in recommended],
        },
        "number_scores": number_scores,
        "backtest": {
            "accuracy_pct": round(summary.avg_accuracy * 100, 2),
            "baseline_pct": round(baseline * 100, 2),
            "improvement_pp": round(summary.improvement_pp, 2),
            "perfect_count": summary.perfect_count,
            "total_periods": summary.total_periods,
        },
        "daily_accuracy": daily_accuracy,
        "monthly_accuracy": monthly_accuracy,
        "backtest_history": backtest_history,
        "weights": {k: round(v, 3) for k, v in result.weights_used.items()},
        "engine_version": "2.1",
    }
    
    # 保存
    output_path = os.path.join(project_root, "reports", "dashboard_data.json")
    with open(output_path, "w") as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)
    
    print(f"Dashboard数据已保存: {output_path}")
    return dashboard


if __name__ == "__main__":
    data = get_dashboard_data()
    print(f"总数据量: {data['total_draws']}期")
    print(f"月度准确率: {len(data['monthly_accuracy'])}个月")
    print(f"每日准确率: {len(data['daily_accuracy'])}天")
