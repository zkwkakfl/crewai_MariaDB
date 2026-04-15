"""기존 field_change_log 행에 대해 변경내용 접두(OOO변경, /, :) 정규화 적용."""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ROOT = _SCRIPTS.parent
DB = ROOT / "공정발주내역.sqlite"

from field_change_log import label_for_field, migrate_legacy_schema, normalize_stored_removed


def main() -> None:
    if not DB.is_file():
        raise SystemExit(f"DB 없음: {DB}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB, DB.with_suffix(f".sqlite.bak_fcl_norm_{ts}"))
    conn = sqlite3.connect(DB)
    migrate_legacy_schema(conn)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(field_change_log)")
    cols = [r[1] for r in cur.fetchall()]
    if "필드명" not in cols or "변경내용" not in cols:
        conn.close()
        raise SystemExit("field_change_log 가 세로 스키마가 아닙니다. migrate_field_change_log_wide.py 를 먼저 실행하세요.")

    cur.execute("SELECT id, 필드명, 변경내용 FROM field_change_log")
    rows = cur.fetchall()
    n = 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for row_id, field_name, detail in rows:
        label = label_for_field(str(field_name))
        new_d = normalize_stored_removed(detail, label)
        if (detail or "") != (new_d or ""):
            cur.execute(
                """
                UPDATE field_change_log
                SET 변경내용 = ?, 기록시각 = ?
                WHERE id = ?
                """,
                (new_d, now, row_id),
            )
            n += cur.rowcount
    conn.commit()
    conn.close()
    print(f"갱신된 행: {n} / 전체 {len(rows)}")


if __name__ == "__main__":
    main()
