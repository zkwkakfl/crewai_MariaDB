"""레거시 field_change_log → 세로 스키마(필드당 1행) 이관."""

from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ROOT = _SCRIPTS.parent
DB = ROOT / "공정발주내역.sqlite"

from field_change_log import migrate_legacy_schema


def main() -> None:
    if not DB.is_file():
        raise SystemExit(f"DB 없음: {DB}")
    conn = sqlite3.connect(DB)
    try:
        summary = migrate_legacy_schema(conn)
    except RuntimeError as e:
        conn.close()
        raise SystemExit(str(e)) from e
    conn.close()
    print(summary)


if __name__ == "__main__":
    main()
