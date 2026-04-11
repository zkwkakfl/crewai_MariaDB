"""기존 field_change_log 세 컬럼에 대해 접두(OOO변경, /, :) 정규화 적용."""

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

from field_change_log_wide import normalize_stored_removed


def main() -> None:
    if not DB.is_file():
        raise SystemExit(f"DB 없음: {DB}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB, DB.with_suffix(f".sqlite.bak_fcl_norm_{ts}"))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT 작업지시번호, 사업명변경, 품명변경, 품번변경 FROM field_change_log"
    )
    rows = cur.fetchall()
    n = 0
    for wo, sm, pm, pn in rows:
        nsm = normalize_stored_removed(sm, "사업명변경")
        npm = normalize_stored_removed(pm, "품명변경")
        npn = normalize_stored_removed(pn, "품번변경")
        if (sm, pm, pn) != (nsm, npm, npn):
            cur.execute(
                """
                UPDATE field_change_log
                SET 사업명변경 = ?, 품명변경 = ?, 품번변경 = ?,
                    updated_at = ?
                WHERE 작업지시번호 = ?
                """,
                (
                    nsm,
                    npm,
                    npn,
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    wo,
                ),
            )
            n += cur.rowcount
    conn.commit()
    conn.close()
    print(f"갱신된 행: {n} / 전체 {len(rows)}")


if __name__ == "__main__":
    main()
