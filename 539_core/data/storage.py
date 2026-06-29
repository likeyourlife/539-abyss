"""数据存储管理 - SQLite + JSON双写"""

import json
import sqlite3
import os
from datetime import date, datetime
from typing import List, Optional
from .models import Draw
from ..config import DB_FILE, JSON_BACKUP


class DataStorage:
    """数据存储管理器"""

    def __init__(self, db_path: str = None, json_path: str = None):
        # 确定项目根目录（向上找到包含539_core的目录）
        self.project_root = self._find_project_root()
        self.db_path = db_path or os.path.join(self.project_root, DB_FILE)
        self.json_path = json_path or os.path.join(self.project_root, JSON_BACKUP)
        self._init_db()

    def _find_project_root(self) -> str:
        """从当前文件向上找到项目根目录"""
        # 539_core/data/storage.py → 539_core → 项目根
        current = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(os.path.dirname(current))

    def _init_db(self):
        """初始化SQLite数据库"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS draws (
                draw_id   TEXT PRIMARY KEY,
                date      TEXT NOT NULL,
                numbers   TEXT NOT NULL,
                source    TEXT DEFAULT 'i539'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS number_stats (
                number    INTEGER PRIMARY KEY,
                freq      REAL,
                recency   INTEGER,
                avg_interval REAL,
                interval_var  REAL,
                z_score   REAL,
                cluster_score REAL,
                updated_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                period_id   INTEGER,
                draw_id     TEXT,
                excluded    TEXT,
                actual      TEXT,
                accuracy    REAL,
                false_positive INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weight_history (
                date        TEXT,
                freq_w      REAL,
                recency_w   REAL,
                interval_w  REAL,
                deviation_w REAL,
                cluster_w   REAL,
                accuracy    REAL
            )
        """)

        conn.commit()
        conn.close()

    def save_draw(self, draw: Draw):
        """保存一期开奖记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO draws VALUES (?, ?, ?, ?)",
            (draw.draw_id, draw.draw_date.isoformat(),
             json.dumps(draw.numbers), draw.source)
        )
        conn.commit()
        conn.close()

    def save_draws(self, draws: List[Draw]):
        """批量保存开奖记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for draw in draws:
            cursor.execute(
                "INSERT OR REPLACE INTO draws VALUES (?, ?, ?, ?)",
                (draw.draw_id, draw.draw_date.isoformat(),
                 json.dumps(draw.numbers), draw.source)
            )
        conn.commit()
        conn.close()

    def load_draws(self) -> List[Draw]:
        """从SQLite加载所有开奖记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT draw_id, date, numbers, source FROM draws ORDER BY date ASC"
        )
        rows = cursor.fetchall()
        conn.close()

        draws = []
        for row in rows:
            draw = Draw(
                draw_id=row[0],
                draw_date=date.fromisoformat(row[1]),
                numbers=json.loads(row[2]),
                source=row[3],
            )
            draws.append(draw)
        return draws

    def load_draw_numbers(self) -> List[List[int]]:
        """加载所有开奖号码列表（用于评分引擎）"""
        draws = self.load_draws()
        return [d.numbers for d in draws]

    def get_draw_count(self) -> int:
        """获取开奖记录总数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM draws")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_latest_draw(self) -> Optional[Draw]:
        """获取最近一期开奖记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT draw_id, date, numbers, source FROM draws ORDER BY date DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return Draw(
                draw_id=row[0],
                draw_date=date.fromisoformat(row[1]),
                numbers=json.loads(row[2]),
                source=row[3],
            )
        return None

    def export_json(self):
        """导出数据为JSON备份"""
        draws = self.load_draws()
        data = [
            {
                "draw_id": d.draw_id,
                "date": d.draw_date.isoformat(),
                "numbers": d.numbers,
                "source": d.source,
            }
            for d in draws
        ]
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_json(self, json_path: str = None):
        """从JSON文件导入数据"""
        path = json_path or self.json_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"JSON文件不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        draws = []
        for item in data:
            draw = Draw(
                draw_id=item["draw_id"],
                draw_date=date.fromisoformat(item["date"]),
                numbers=item["numbers"],
                source=item.get("source", "import"),
            )
            draws.append(draw)

        self.save_draws(draws)
        return len(draws)
