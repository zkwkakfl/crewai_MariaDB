"""
field_change_log: consolidated_data_id 대신 작업지시번호를 기준 키로 쓰도록 재구성.

- 기존 행은 consolidated_data와 조인해 `작업지시번호`를 채운 뒤,
  테이블을 `작업지시번호` 중심 스키마로 교체한다.
- 동일 작업지시가 여러 행일 수 있어 `source_row_id`(구 consolidated_data.id)는
  조회·구분용으로만 유지한다.
"""

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
        print("field_change_log 없음 — 건너뜀")
        conn.close()
        return

    cur.execute("PRAGMA table_info(field_change_log)")
    cols = {row[1] for row in cur.fetchall()}
    if "작업지시번호" in cols and "consolidated_data_id" not in cols:
        print("이미 작업지시번호 기준 스키마입니다.")
        conn.close()
        return

    cur.execute(
        """
        CREATE TABLE field_change_log_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            작업지시번호 TEXT NOT NULL,
            source_row_id INTEGER NOT NULL,
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

    # consolidated_data_id → 작업지시번호 조인
    cur.execute(
        """
        INSERT INTO field_change_log_new (
            id, 작업지시번호, source_row_id, field_name, marker,
            removed_text, value_before, value_after, source_backup, recorded_at
        )
        SELECT
            l.id,
            COALESCE(
                NULLIF(TRIM(c.`작업지시번호`), ''),
                '(row:' || l.consolidated_data_id || ')'
            ),
            l.consolidated_data_id,
            l.field_name,
            l.marker,
            l.removed_text,
            l.value_before,
            l.value_after,
            l.source_backup,
            l.recorded_at
        FROM field_change_log l
        LEFT JOIN consolidated_data c ON c.id = l.consolidated_data_id
        """
    )

    cur.execute("DROP TABLE field_change_log")
    cur.execute("ALTER TABLE field_change_log_new RENAME TO field_change_log")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_field_change_wo "
        "ON field_change_log (작업지시번호, field_name)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_field_change_src "
        "ON field_change_log (source_row_id)"
    )

    conn.commit()
    conn.close()
    print("field_change_log 재구성 완료: 작업지시번호 + source_row_id")


if __name__ == "__main__":
    main()
