"""
consolidated_data.고객사 필드 1단계 가공.

규칙:
1) '고객사변경' 이 보이면 해당 위치부터 끝까지 제거(앞부분만 유지).
2) 괄호 ( ... ) 안이 영어(라틴 문자 중심, 한글 없음)면 → 필드 전체를 괄호 안 영어 텍스트만 남김.
3) 괄호 안에 한글이 있으면 → 해당 (한글...) 구간만 제거하고 괄호 밖 텍스트는 유지.

백업: 공정발주내역.sqlite.bak 고객사_step1 (타임스탬프)
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "공정발주내역.sqlite"
COL = "고객사"


def _has_hangul(s: str) -> bool:
    return bool(re.search(r"[\uAC00-\uD7A3]", s))


def _paren_english_only(inner: str) -> bool:
    """괄호 안이 '영어 쪽'으로 볼 때: 한글 없고, 라틴 문자가 하나 이상."""
    if _has_hangul(inner):
        return False
    return bool(re.search(r"[A-Za-z]", inner))


def clean_customer(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return s

    # 1) 고객사변경 이후 제거
    idx = s.find("고객사변경")
    if idx != -1:
        s = s[:idx].strip()

    # 2) 괄호: (영어)면 필드 전체를 그 안의 영어로 치환 후 종료.
    #    (한글 등)이면 해당 괄호 블록만 제거하고 반복.
    while True:
        m = re.search(r"\(([^)]*)\)", s)
        if not m:
            break
        inner = m.group(1)
        if _paren_english_only(inner):
            s = inner.strip()
            break
        s = (s[: m.start()] + s[m.end() :]).strip()

    return s if s else None


def main() -> None:
    if not DB.is_file():
        raise SystemExit(f"DB 없음: {DB}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB.with_suffix(f".sqlite.bak_고객사_step1_{ts}")
    shutil.copy2(DB, bak)
    print(f"백업: {bak}")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(f'SELECT id, "{COL}" FROM consolidated_data')
    rows = cur.fetchall()
    changed = 0
    for row_id, val in rows:
        new_val = clean_customer(val)
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
