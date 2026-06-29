"""批量抓取数据并导入SQLite"""

import sys
sys.path.insert(0, '.')

from importlib import import_module
fetcher = import_module('539_core.data.fetcher')
storage = import_module('539_core.data.storage')

# 1. 从lottolyzer抓取多页数据（20页 = 1000期）
print("=== 开始批量抓取lottolyzer数据 ===")
all_draws = fetcher.fetch_lottolyzer_all(max_pages=20)
print(f"lottolyzer总共: {len(all_draws)}期")

# 2. 从i539补充最新20期
print("\n=== 补充i539近20期 ===")
recent = fetcher.fetch_i539_recent()
print(f"i539近20期: {len(recent)}期")

# 3. 合并去重
combined = all_draws + recent
seen = set()
unique = []
for d in combined:
    key = d.draw_date.isoformat()
    if key not in seen:
        seen.add(key)
        unique.append(d)
unique.sort(key=lambda d: d.draw_date)

print(f"\n合并去重: {len(unique)}期")
if unique:
    print(f"最早: {unique[0].draw_date} {unique[0].numbers}")
    print(f"最近: {unique[-1].draw_date} {unique[-1].numbers}")

# 4. 导入SQLite
print("\n=== 导入SQLite ===")
ds = storage.DataStorage()
ds.save_draws(unique)
count = ds.get_draw_count()
print(f"SQLite已存: {count}期")

# 5. 导出JSON备份
ds.export_json()
print(f"JSON备份已导出")

# 6. 验证
draws = ds.load_draw_numbers()
print(f"\n验证: 读取到{len(draws)}期数据")
if draws:
    print(f"  第1期: {draws[0]}")
    print(f"  最后一期: {draws[-1]}")
