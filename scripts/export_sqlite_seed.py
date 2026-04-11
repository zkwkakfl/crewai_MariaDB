"""
SQLite `consolidated_data` → MariaDB 스테이징용 CREATE + INSERT (UTF-8).

Crew가 준 본 테이블(`work_orders` 등)과 별개로, 원본 샘플을 그대로 옮길 때 사용한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQLITE = ROOT / "공정발주내역.sqlite"
OUT_SQL = ROOT / "seed" / "staging_consolidated_inserts.sql"


def _esc(val: object) -> str:
    if val is None:
        return "NULL"
    # 줄바꿈은 MariaDB 문자열 리터럴을 깨므로 공백으로 합침
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
    cur.execute("PRAGMA table_info(consolidated_data)")
    pragma = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM consolidated_data")
    total = cur.fetchone()[0]
    cur.execute("SELECT * FROM consolidated_data ORDER BY id")
    rows = cur.fetchall()
    cols = [r[1] for r in pragma]

    def maria_type(sqlite_decl: str) -> str:
        u = (sqlite_decl or "TEXT").upper()
        if "INT" in u:
            return "BIGINT"
        return "TEXT"

    col_defs = []
    for cid, name, ctype, notnull, dflt, pk in pragma:
        line = f"  `{name}` {maria_type(ctype)}"
        if pk:
            line += " AUTO_INCREMENT PRIMARY KEY" if "INT" in maria_type(ctype) else " PRIMARY KEY"
        elif notnull:
            line += " NOT NULL"
        col_defs.append(line)

    lines = [
        "-- 스테이징: SQLite consolidated_data 미러 (샘플 적재용)\n",
        "SET NAMES utf8mb4;\n",
        "SET FOREIGN_KEY_CHECKS=0;\n",
        "DROP TABLE IF EXISTS staging_consolidated;\n",
        "CREATE TABLE staging_consolidated (\n",
        ",\n".join(col_defs),
        "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\n",
        f"-- 원본 행 수: {total}, 아래 INSERT 수: {len(rows)}\n\n",
    ]
    col_sql = ", ".join(f"`{c}`" for c in cols)
    for row in rows:
        vals = ", ".join(_esc(row[c]) for c in cols)
        lines.append(f"INSERT INTO staging_consolidated ({col_sql}) VALUES ({vals});\n")

    lines.append("SET FOREIGN_KEY_CHECKS=1;\n")
    OUT_SQL.write_text("".join(lines), encoding="utf-8")
    print(f"작성: {OUT_SQL} (INSERT {len(rows)}행)")


if __name__ == "__main__":
    main()
