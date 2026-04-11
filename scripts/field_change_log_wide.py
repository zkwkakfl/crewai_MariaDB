"""field_change_log 넓은 스키마(작업지시번호당 1행) 공통 유틸."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
DDL = """
CREATE TABLE IF NOT EXISTS field_change_log (
    작업지시번호 TEXT PRIMARY KEY,
    사업명변경 TEXT,
    품명변경 TEXT,
    품번변경 TEXT,
    updated_at TEXT NOT NULL
);
"""


def ensure_wide_table(cur: sqlite3.Cursor) -> None:
    cur.execute(DDL)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_fcl_wo ON field_change_log (작업지시번호)"
    )


def normalize_stored_removed(text: str | None, label: str) -> str | None:
    """
    컬럼 의미(사업명변경 등)와 중복되는 접두 제거.
    예: '사업명변경/\\nfoo', '사업명변경: bar' -> 본문만 남김.
    """
    if text is None or not str(text).strip():
        return None
    s = str(text).strip()
    if s.startswith(label):
        s = s[len(label) :]
    s = s.lstrip()
    # 선행 / : ： 및 공백·개행
    s = re.sub(r"^[/:：\s]+", "", s)
    return s.strip() or None


def upsert_column(
    conn: sqlite3.Connection,
    *,
    work_order_no: str,
    column: str,
    removed_text: str | None,
) -> None:
    """사업명변경 / 품명변경 / 품번변경 중 하나만 갱신(나머지 기존 값 유지)."""
    if column not in ("사업명변경", "품명변경", "품번변경"):
        raise ValueError(column)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.cursor()
    cur.execute(
        "SELECT 사업명변경, 품명변경, 품번변경 FROM field_change_log WHERE 작업지시번호 = ?",
        (work_order_no,),
    )
    row = cur.fetchone()
    sm, pm, pn = row if row else (None, None, None)
    norm = normalize_stored_removed(removed_text, column)
    if column == "사업명변경":
        sm = norm
    elif column == "품명변경":
        pm = norm
    else:
        pn = norm

    cur.execute(
        """
        INSERT INTO field_change_log (작업지시번호, 사업명변경, 품명변경, 품번변경, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(작업지시번호) DO UPDATE SET
            사업명변경 = COALESCE(excluded.사업명변경, field_change_log.사업명변경),
            품명변경 = COALESCE(excluded.품명변경, field_change_log.품명변경),
            품번변경 = COALESCE(excluded.품번변경, field_change_log.품번변경),
            updated_at = excluded.updated_at
        """,
        (work_order_no, sm, pm, pn, now),
    )


def migrate_from_narrow_table(conn: sqlite3.Connection) -> int:
    """
    예전(세로) field_change_log 가 있으면 넓은 형태로 옮긴 뒤 예전 테이블 제거.
    반환: 이관된 작업지시번호 개수
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='field_change_log'"
    )
    if not cur.fetchone():
        return 0

    cur.execute("PRAGMA table_info(field_change_log)")
    cols = [r[1] for r in cur.fetchall()]
    if "field_name" not in cols:
        # 이미 넓은 스키마(사업명변경 컬럼 있음)
        if "사업명변경" in cols and "품명변경" in cols:
            return 0
        return 0

    cur.execute(
        """
        SELECT 작업지시번호,
               MAX(CASE WHEN field_name = '사업명' THEN removed_text END),
               MAX(CASE WHEN field_name = '품명' THEN removed_text END),
               MAX(CASE WHEN field_name = '품번' THEN removed_text END),
               MAX(recorded_at)
        FROM field_change_log
        GROUP BY 작업지시번호
        """
    )
    rows = cur.fetchall()
    cur.execute("DROP TABLE field_change_log")
    ensure_wide_table(cur)
    n = 0
    for wo, sm, pm, pn, ts in rows:
        if not wo:
            continue
        sm = normalize_stored_removed(sm, "사업명변경")
        pm = normalize_stored_removed(pm, "품명변경")
        pn = normalize_stored_removed(pn, "품번변경")
        cur.execute(
            """
            INSERT INTO field_change_log (작업지시번호, 사업명변경, 품명변경, 품번변경, updated_at)
            VALUES (?, ?, ?, ?, COALESCE(?, ?))
            """,
            (wo, sm, pm, pn, ts, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
        n += 1
    conn.commit()
    return n
