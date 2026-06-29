"""每周深度回测+引擎自动学习优化脚本"""

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
simulator_mod = import_module('539_core.backtest.simulator')
config_mod = import_module('539_core.config')

def run_weekly_backtest():
    """执行每周深度回测+引擎优化"""
    ds = storage_mod.DataStorage()

    # 1. 更新数据
    print("1. 更新数据...")
    recent = fetcher_mod.fetch_i539_recent()
    if recent:
        ds.save_draws(recent)
    for page in range(1, 5):
        page_data = fetcher_mod.fetch_lottolyzer_page(page)
        if page_data:
            ds.save_draws(page_data)
    
    draws = ds.load_draw_numbers()
    print(f"   数据量: {len(draws)}期")

    # 2. 策略对比回测
    print("2. 策略对比回测...")
    results = simulator_mod.compare_strategies(draws)
    
    # 找最优策略
    best_name = None
    best_accuracy = 0.0
    best_weights = None
    
    for name, summary in results.items():
        if summary.avg_accuracy > best_accuracy:
            best_accuracy = summary.avg_accuracy
            best_name = name
            best_weights = simulator_mod.STRATEGIES[name]
    
    baseline = 1 - 5/39
    baseline_pct = baseline * 100
    
    print(f"   最优策略: {best_name} ({best_accuracy*100:.2f}%)")
    print(f"   基线: {baseline_pct:.2f}%")
    
    # 3. 检查准确率是否达标
    TARGET_ACCURACY = 87.49
    
    if best_accuracy * 100 >= TARGET_ACCURACY:
        print(f"3. ✅ 准确率达标 ({best_accuracy*100:.2f}% >= {TARGET_ACCURACY}%)")
    else:
        print(f"3. ⚠️ 准确率低于目标 ({best_accuracy*100:.2f}% < {TARGET_ACCURACY}%)")
        print("   触发引擎权重微调...")
        
        # 自动微调：尝试当前最优策略的权重作为新默认
        # 写入config.py
        config_path = os.path.join(project_root, "539_core", "config.py")
        with open(config_path, "r") as f:
            config_content = f.read()
        
        # 找到DEFAULT_WEIGHTS并替换
        import re
        weights_str = "DEFAULT_WEIGHTS = {\n"
        for k, v in best_weights.items():
            weights_str += f'    "{k}": {v:.3f},\n'
        weights_str += "}\n"
        
        new_config = re.sub(
            r'DEFAULT_WEIGHTS = \{[^}]+\}',
            weights_str,
            config_content,
        )
        
        with open(config_path, "r") as f:
            old_weights_match = re.search(r'DEFAULT_WEIGHTS = \{[^}]+\}', f.read())
        
        with open(config_path, "w") as f:
            f.write(new_config)
        
        print(f"   已更新DEFAULT_WEIGHTS为{best_name}策略")
        print(f"   新权重: {best_weights}")

    # 4. 记录回测历史
    history_path = os.path.join(project_root, "data", "backtest_history.json")
    
    # 加载或初始化历史
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            history = json.load(f)
    else:
        history = []
    
    # 记录本次结果
    record = {
        "date": date.today().isoformat(),
        "total_draws": len(draws),
        "best_strategy": best_name,
        "best_accuracy_pct": round(best_accuracy * 100, 2),
        "baseline_pct": round(baseline_pct, 2),
        "improvement_pp": round((best_accuracy - baseline) * 100, 2),
        "all_strategies": {
            name: {
                "accuracy_pct": round(summary.avg_accuracy * 100, 2),
                "improvement_pp": round(summary.improvement_pp, 2),
                "perfect_count": summary.perfect_count,
                "total_periods": summary.total_periods,
            }
            for name, summary in results.items()
        },
        "weights_used": {k: round(v, 3) for k, v in best_weights.items()},
        "target_accuracy": TARGET_ACCURACY,
        "status": "PASS" if best_accuracy * 100 >= TARGET_ACCURACY else "NEEDS_TUNING",
    }
    
    history.append(record)
    
    with open(history_path, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"4. 回测历史已保存: {history_path}")
    
    return record

if __name__ == "__main__":
    record = run_weekly_backtest()
    
    print("\n" + "="*50)
    print(f"今彩539 每周深度回测 ({date.today()})")
    print("="*50)
    print(f"数据量: {record['total_draws']}期")
    print(f"最优策略: {record['best_strategy']} ({record['best_accuracy_pct']}%)")
    print(f"基线: {record['baseline_pct']}%")
    print(f"提升: {record['improvement_pp']:+.2f}pp")
    print(f"状态: {record['status']}")
    print("="*50)
    
    for name, data in record['all_strategies'].items():
        delta = data['accuracy_pct'] - record['baseline_pct']
        sign = '+' if delta > 0 else ''
        print(f"  {name:20s}: {data['accuracy_pct']:.2f}% ({sign}{delta:.2f}pp)")
