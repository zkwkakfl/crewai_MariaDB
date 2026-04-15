"""
consolidated_data 한 필드에서 '마커' 이후(마커 포함) 제거 + field_change_log(세로형)에 제거 구간 기록.

사용 예:
  python scripts/clean_marker_field.py --column 품명 --marker 품명변경 --log-column 품명변경
  python scripts/clean_marker_field.py --column 품번 --marker 품번변경 --log-column 품번변경
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ROOT = _SCRIPTS.parent
DB = ROOT / "공정발주내역.sqlite"

from field_change_log import LOG_COLUMN_TO_FIELD_NAME
from field_change_log_wide import ensure_wide_table, migrate_from_narrow_table, upsert_column


def clean_value(value: str | None, marker: str) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return s
    idx = s.find(marker)
    if idx != -1:
        s = s[:idx].strip()
    return s if s else None


def removed_suffix(value: str | None, marker: str) -> str | None:
    if value is None or marker not in value:
        return None
    idx = value.find(marker)
    return value[idx:].strip()


def main() -> None:
    p = argparse.ArgumentParser(description="마커 이후 제거 + field_change_log 반영")
    p.add_argument("--column", required=True, help="consolidated_data 컬럼명 (예: 품명)")
    p.add_argument("--marker", required=True, help="잘라낼 시작 마커 (예: 품명변경)")
    p.add_argument(
        "--log-column",
        required=True,
        choices=sorted(LOG_COLUMN_TO_FIELD_NAME.keys()),
        help="field_change_log 에 매핑할 마커 종류(→필드명)",
    )
    args = p.parse_args()

    if not DB.is_file():
        raise SystemExit(f"DB 없음: {DB}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB.with_suffix(f".sqlite.bak_{args.column}_{ts}")
    shutil.copy2(DB, bak)
    print(f"백업: {bak}")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    migrate_from_narrow_table(conn)
    ensure_wide_table(cur)
    conn.commit()

    cur.execute(f'SELECT id, `작업지시번호`, "{args.column}" FROM consolidated_data')
    rows = cur.fetchall()
    changed = 0
    for row_id, work_no, val in rows:
        if val is None or args.marker not in val:
            continue
        new_val = clean_value(val, args.marker)
        rem = removed_suffix(val, args.marker)
        wo = (work_no or "").strip() or f"(row:{row_id})"
        if (val or "") == (new_val or ""):
            continue
        cur.execute(
            f'UPDATE consolidated_data SET "{args.column}" = ? WHERE id = ?',
            (new_val, row_id),
        )
        changed += cur.rowcount
        upsert_column(conn, work_order_no=wo, column=args.log_column, removed_text=rem)

    conn.commit()
    conn.close()
    print(f"행 {len(rows)} 스캔, consolidated_data 변경 {changed}건")


if __name__ == "__main__":
    main()
