"""数据更新脚本"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from importlib import import_module
fetcher = import_module('539_core.data.fetcher')
storage = import_module('539_core.data.storage')

def main():
    print("开始抓取最新数据...")

    # 从i539获取近20期
    recent = fetcher.fetch_i539_recent()
    print(f"i539近20期: {len(recent)}期")

    # 从lottolyzer获取第1页（50期）
    page1 = fetcher.fetch_lottolyzer_page(1)
    print(f"lottolyzer第1页: {len(page1)}期")

    # 合并
    all_draws = recent + page1
    seen = set()
    unique = []
    for d in all_draws:
        key = d.draw_date.isoformat()
        if key not in seen:
            seen.add(key)
            unique.append(d)
    unique.sort(key=lambda d: d.draw_date)

    # 保存
    ds = storage.DataStorage()
    existing = ds.get_draw_count()
    ds.save_draws(unique)
    new_count = ds.get_draw_count()

    print(f"更新完成: 原有{existing}期, 当前{new_count}期, 新增{new_count-existing}期")

    # 如果新增数据，自动运行分析
    if new_count > existing:
        print("\n检测到新数据，自动运行分析...")
        os.system(f"/Users/ioorule/.workbuddy/binaries/python/envs/default/bin/python3 {project_root}/scripts/run_analysis.py")

if __name__ == "__main__":
    main()
