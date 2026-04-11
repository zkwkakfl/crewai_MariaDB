"""field_change_log에서 source_row_id 제거(작업지시번호만으로 식별)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "공정발주내역.sqlite"


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='field_change_log'"
    )
    if not cur.fetchone():
        print("field_change_log 없음")
        conn.close()
        return

    cur.execute("PRAGMA table_info(field_change_log)")
    cols = [r[1] for r in cur.fetchall()]
    if "source_row_id" not in cols:
        print("이미 source_row_id 없음")
        conn.close()
        return

    cur.execute(
        """
        CREATE TABLE field_change_log_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            작업지시번호 TEXT NOT NULL,
            field_name TEXT NOT NULL,
            marker TEXT NOT NULL,
            removed_text TEXT,
            value_before TEXT,
            value_after TEXT,
            source_backup TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        INSERT INTO field_change_log_v2 (
            id, 작업지시번호, field_name, marker,
            removed_text, value_before, value_after, source_backup, recorded_at
        )
        SELECT
            id, 작업지시번호, field_name, marker,
            removed_text, value_before, value_after, source_backup, recorded_at
        FROM field_change_log
        """
    )
    cur.execute("DROP TABLE field_change_log")
    cur.execute("ALTER TABLE field_change_log_v2 RENAME TO field_change_log")
    cur.execute("DROP INDEX IF EXISTS idx_field_change_src")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_field_change_wo "
        "ON field_change_log (작업지시번호, field_name)"
    )

    conn.commit()
    conn.close()
    print("field_change_log: source_row_id 제거 완료")


if __name__ == "__main__":
    main()
