"""
SQLite `field_change_log` → MariaDB 스테이징용 CREATE + INSERT (UTF-8).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQLITE = ROOT / "공정발주내역.sqlite"
OUT_SQL = ROOT / "seed" / "insert.sql"


def _esc(val: object) -> str:
    if val is None:
        return "NULL"
    s = " ".join(str(val).split())
    s = s.replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def main() -> None:
    if not SQLITE.is_file():
        raise SystemExit(f"SQLite 없음: {SQLITE}")
    OUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM field_change_log")
    total = cur.fetchone()[0]
    cur.execute(
        "SELECT 작업지시번호, 사업명변경, 품명변경, 품번변경, updated_at "
        "FROM field_change_log ORDER BY 작업지시번호"
    )
    rows = cur.fetchall()
    conn.close()

    cols = ("작업지시번호", "사업명변경", "품명변경", "품번변경", "updated_at")
    col_sql = ", ".join(f"`{c}`" for c in cols)

    lines = [
        "-- 스테이징: SQLite field_change_log 미러 (작업지시번호당 1행)\n",
        "SET NAMES utf8mb4;\n",
        "SET FOREIGN_KEY_CHECKS=0;\n",
        "DROP TABLE IF EXISTS field_change_log;\n",
        "CREATE TABLE field_change_log (\n",
        "  `작업지시번호` VARCHAR(128) NOT NULL COMMENT '작업지시번호(PK)',\n",
        "  `사업명변경` TEXT NULL COMMENT '제거·정규화된 사업명 변경 구간',\n",
        "  `품명변경` TEXT NULL COMMENT '제거·정규화된 품명 변경 구간',\n",
        "  `품번변경` TEXT NULL COMMENT '제거·정규화된 품번 변경 구간',\n",
        "  `updated_at` VARCHAR(64) NOT NULL COMMENT '갱신 시각(ISO8601 UTC 등)',\n",
        "  PRIMARY KEY (`작업지시번호`)\n",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci\n",
        "COMMENT='필드 변경 이력(넓은 스키마)';\n\n",
        f"-- 원본 행 수: {total}, 아래 INSERT 수: {len(rows)}\n\n",
    ]

    for row in rows:
        vals = ", ".join(_esc(row[c]) for c in cols)
        lines.append(f"INSERT INTO field_change_log ({col_sql}) VALUES ({vals});\n")

    lines.append("\nSET FOREIGN_KEY_CHECKS=1;\n")
    OUT_SQL.write_text("".join(lines), encoding="utf-8")
    print(f"작성: {OUT_SQL} (INSERT {len(rows)}행)")


if __name__ == "__main__":
    main()
