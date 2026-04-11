"""
consolidated_data.사업명 필드: '사업명변경' 이후(해당 문구 포함) 전부 제거.

백업 후 UPDATE.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "공정발주내역.sqlite"
COL = "사업명"
MARKER = "사업명변경"


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return s
    idx = s.find(MARKER)
    if idx != -1:
        s = s[:idx].strip()
    return s if s else None


def main() -> None:
    if not DB.is_file():
        raise SystemExit(f"DB 없음: {DB}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB.with_suffix(f".sqlite.bak_{COL}_{ts}")
    shutil.copy2(DB, bak)
    print(f"백업: {bak}")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(f'SELECT id, "{COL}" FROM consolidated_data')
    rows = cur.fetchall()
    changed = 0
    for row_id, val in rows:
        new_val = clean(val)
        if (val or "") != (new_val or ""):
            cur.execute(
                f'UPDATE consolidated_data SET "{COL}" = ? WHERE id = ?',
                (new_val, row_id),
            )
            changed += 1

    conn.commit()
    conn.close()
    print(f"행 {len(rows)} 중 변경 {changed}건")


if __name__ == "__main__":
    main()
