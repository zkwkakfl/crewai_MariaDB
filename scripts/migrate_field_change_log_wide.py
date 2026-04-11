"""기존 field_change_log(세로 형식) → 작업지시번호당 1행(넓은 형식) 이관."""

from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ROOT = _SCRIPTS.parent
DB = ROOT / "공정발주내역.sqlite"

from field_change_log_wide import ensure_wide_table, migrate_from_narrow_table


def main() -> None:
    conn = sqlite3.connect(DB)
    n = migrate_from_narrow_table(conn)
    if n == 0:
        cur = conn.cursor()
        ensure_wide_table(cur)
        conn.commit()
        print("이관할 세로 형식 로그 없음 — 넓은 테이블만 확인")
    else:
        print(f"이관 완료: {n}개 작업지시번호")
    conn.close()


if __name__ == "__main__":
    main()
