"""539 Dashboard 后端API服务 - Flask"""

import json
import sys
import os
import threading
from datetime import datetime, date
from flask import Flask, jsonify, send_from_directory, request

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

app = Flask(__name__, static_folder='frontend')

# 全局状态
analysis_status = {
    "running": False,
    "progress": 0,
    "message": "就绪",
    "last_result": None,
    "last_run": None,
}

def run_analysis_task():
    """后台运行分析引擎"""
    global analysis_status
    
    analysis_status["running"] = True
    analysis_status["progress"] = 10
    analysis_status["message"] = "采集数据..."
    
    try:
        from importlib import import_module
        storage_mod = import_module('539_core.data.storage')
        fetcher_mod = import_module('539_core.data.fetcher')
        scorer_mod = import_module('539_core.engine.scorer')
        backtest_mod = import_module('539_core.backtest.runner')
        
        # 1. 采集数据
        ds = storage_mod.DataStorage()
        recent = fetcher_mod.fetch_i539_recent()
        if recent:
            ds.save_draws(recent)
        for page in range(1, 3):
            page_data = fetcher_mod.fetch_lottolyzer_page(page)
            if page_data:
                ds.save_draws(page_data)
        
        analysis_status["progress"] = 40
        analysis_status["message"] = "评分计算..."
        
        # 2. 评分
        draws = ds.load_draw_numbers()
        scorer = scorer_mod.NoWinScorer()
        result = scorer.score(draws)
        
        analysis_status["progress"] = 70
        analysis_status["message"] = "回测验证..."
        
        # 3. 回测
        summary = backtest_mod.run_backtest(draws, top_n=10)
        baseline = 1 - 5/39
        
        analysis_status["progress"] = 90
        analysis_status["message"] = "生成报告..."
        
        # 4. 构建结果
        latest = ds.get_latest_draw()
        
        # 获取号码评分
        number_scores = []
        for ns in result.number_stats:
            number_scores.append({
                "number": ns.number,
                "composite_score": round(ns.composite_score, 4),
                "is_excluded_top2": ns.number in result.get_exclusion(2),
                "is_excluded_top5": ns.number in result.get_exclusion(5),
                "is_excluded_top10": ns.number in result.get_exclusion(10),
                "is_recommended": ns.number in result.get_recommendation(5),
                "momentum_score": round(ns.momentum_score, 4) if hasattr(ns, 'momentum_score') else 0,
                "recency_score": round(ns.recency_score, 4),
                "cluster_score": round(ns.cluster_raw_score if hasattr(ns, 'cluster_raw_score') else ns.cluster_score, 4),
            })
        number_scores.sort(key=lambda x: x["composite_score"], reverse=True)
        
        output = {
            "generated_at": datetime.now().isoformat(),
            "total_draws": len(draws),
            "latest_draw": {
                "date": str(latest.draw_date) if latest else None,
                "numbers": latest.numbers if latest else None,
            },
            "prediction": {
                "top2": [{"number": n, "label": f"{n:02d}"} for n in result.get_exclusion(2)],
                "top4": [{"number": n, "label": f"{n:02d}"} for n in result.get_exclusion(4)],
                "top5": [{"number": n, "label": f"{n:02d}"} for n in result.get_exclusion(5)],
                "top10": [{"number": n, "label": f"{n:02d}"} for n in result.get_exclusion(10)],
                "recommended": [{"number": n, "label": f"{n:02d}"} for n in result.get_recommendation(5)],
            },
            "number_scores": number_scores,
            "backtest": {
                "accuracy_pct": round(summary.avg_accuracy * 100, 2),
                "baseline_pct": round(baseline * 100, 2),
                "improvement_pp": round(summary.improvement_pp, 2),
                "perfect_count": summary.perfect_count,
                "total_periods": summary.total_periods,
            },
            "weights": {k: round(v, 3) for k, v in result.weights_used.items()},
            "engine_version": "2.1",
        }
        
        # 保存JSON
        json_path = os.path.join(project_root, "reports", f"dashboard_data.json")
        with open(json_path, "w") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        # 也复制到frontend目录
        frontend_path = os.path.join(project_root, "frontend", "dashboard_data.json")
        with open(frontend_path, "w") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        analysis_status["progress"] = 100
        analysis_status["message"] = "分析完成！"
        analysis_status["last_result"] = output
        analysis_status["last_run"] = datetime.now().isoformat()
        
    except Exception as e:
        analysis_status["progress"] = 0
        analysis_status["message"] = f"分析失败: {str(e)}"
        analysis_status["running"] = False
        raise
    
    finally:
        analysis_status["running"] = False


# ===== API 路由 =====

@app.route('/')
def index():
    """主页"""
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """静态文件"""
    return send_from_directory('frontend', path)

@app.route('/api/dashboard')
def get_dashboard():
    """获取Dashboard数据"""
    json_path = os.path.join(project_root, "reports", "dashboard_data.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "暂无数据，请先运行预测引擎"}), 404

@app.route('/api/run-analysis', methods=['POST'])
def run_analysis():
    """运行分析引擎"""
    if analysis_status["running"]:
        return jsonify({
            "status": "running",
            "progress": analysis_status["progress"],
            "message": analysis_status["message"],
        })
    
    # 启动后台线程
    thread = threading.Thread(target=run_analysis_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "started",
        "progress": 0,
        "message": "引擎启动中...",
    })

@app.route('/api/status')
def get_status():
    """获取引擎运行状态"""
    result = {
        "running": analysis_status["running"],
        "progress": analysis_status["progress"],
        "message": analysis_status["message"],
        "last_run": analysis_status["last_run"],
    }
    
    if analysis_status["last_result"]:
        result["last_result"] = {
            "accuracy_pct": analysis_status["last_result"]["backtest"]["accuracy_pct"],
            "improvement_pp": analysis_status["last_result"]["backtest"]["improvement_pp"],
            "top2": analysis_status["last_result"]["prediction"]["top2"],
            "top5": analysis_status["last_result"]["prediction"]["top5"],
            "top10": analysis_status["last_result"]["prediction"]["top10"],
        }
    
    return jsonify(result)

@app.route('/api/update-data', methods=['POST'])
def update_data():
    """仅更新数据（不重新评分）"""
    try:
        from importlib import import_module
        storage_mod = import_module('539_core.data.storage')
        fetcher_mod = import_module('539_core.data.fetcher')
        
        ds = storage_mod.DataStorage()
        recent = fetcher_mod.fetch_i539_recent()
        added_i539 = len(recent) if recent else 0
        if recent:
            ds.save_draws(recent)
        
        added_lotto = 0
        for page in range(1, 3):
            page_data = fetcher_mod.fetch_lottolyzer_page(page)
            if page_data:
                ds.save_draws(page_data)
                added_lotto += len(page_data)
        
        draws = ds.load_draw_numbers()
        latest = ds.get_latest_draw()
        
        return jsonify({
            "status": "success",
            "total_draws": len(draws),
            "added_i539": added_i539,
            "added_lotto": added_lotto,
            "latest_date": str(latest.draw_date) if latest else None,
            "latest_numbers": latest.numbers if latest else None,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/backtest-compare', methods=['POST'])
def backtest_compare():
    """策略对比回测"""
    try:
        from importlib import import_module
        storage_mod = import_module('539_core.data.storage')
        simulator_mod = import_module('539_core.backtest.simulator')
        
        ds = storage_mod.DataStorage()
        draws = ds.load_draw_numbers()
        results = simulator_mod.compare_strategies(draws)
        
        strategies = {}
        for name, summary in results.items():
            strategies[name] = {
                "accuracy_pct": round(summary.avg_accuracy * 100, 2),
                "improvement_pp": round(summary.improvement_pp, 2),
                "perfect_count": summary.perfect_count,
                "total_periods": summary.total_periods,
            }
        
        return jsonify({
            "status": "success",
            "strategies": strategies,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    print("✦ 今彩539 Dashboard API 服务启动")
    print(f"   项目路径: {project_root}")
    print(f"   访问地址: http://localhost:5390")
    print()
    
    # 首次启动自动加载已有数据
    json_path = os.path.join(project_root, "reports", "dashboard_data.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            analysis_status["last_result"] = json.load(f)
        print("   已加载上次分析数据")
    
    app.run(host='0.0.0.0', port=5390, debug=False)
