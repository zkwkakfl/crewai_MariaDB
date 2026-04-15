"""field_change_log 세로 스키마(필드당 행) — 감사 이력용 공통 유틸."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

# 로그에 허용되는 비즈니스 필드명 (필드 추가 시 여기만 확장)
ALLOWED_FIELD_NAMES = frozenset({"사업명", "품명", "품번", "수량", "납품일정"})

# 마커/로그 컬럼 라벨 → 필드명 (clean_marker_field 등)
LOG_COLUMN_TO_FIELD_NAME: dict[str, str] = {
    "사업명변경": "사업명",
    "품명변경": "품명",
    "품번변경": "품번",
    "수량변경": "수량",
    "납품일정변경": "납품일정",
}

DDL = """
CREATE TABLE IF NOT EXISTS field_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    작업지시번호 TEXT NOT NULL,
    필드명 TEXT NOT NULL,
    변경내용 TEXT,
    변경묶음_id TEXT,
    기록시각 TEXT NOT NULL
);
"""


def ensure_table(cur: sqlite3.Cursor) -> None:
    cur.execute(DDL)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_fcl_wo ON field_change_log (작업지시번호)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_fcl_field ON field_change_log (필드명)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_fcl_batch ON field_change_log (변경묶음_id)"
    )


def normalize_stored_removed(text: str | None, label: str) -> str | None:
    """
    컬럼 의미와 중복되는 접두 제거.
    예: '사업명변경/\\nfoo', '사업명변경: bar' -> 본문만 남김.
    """
    if text is None or not str(text).strip():
        return None
    s = str(text).strip()
    if s.startswith(label):
        s = s[len(label) :]
    s = s.lstrip()
    s = re.sub(r"^[/:：\s]+", "", s)
    return s.strip() or None


def label_for_field(field_name: str) -> str:
    if field_name in ALLOWED_FIELD_NAMES:
        return f"{field_name}변경"
    return field_name


def insert_field_change(
    conn: sqlite3.Connection,
    *,
    work_order_no: str,
    field_name: str,
    change_detail: str | None,
    change_batch_id: str | None = None,
    recorded_at: str | None = None,
) -> None:
    """변경 1건을 append (동일 작업지시에 여러 행 가능)."""
    if field_name not in ALLOWED_FIELD_NAMES:
        raise ValueError(f"허용되지 않은 필드명: {field_name}")
    if change_detail is None or not str(change_detail).strip():
        return
    norm = normalize_stored_removed(change_detail, label_for_field(field_name))
    if not norm:
        return
    ts = recorded_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO field_change_log (작업지시번호, 필드명, 변경내용, 변경묶음_id, 기록시각)
        VALUES (?, ?, ?, ?, ?)
        """,
        (work_order_no, field_name, norm, change_batch_id, ts),
    )


def migrate_legacy_schema(conn: sqlite3.Connection) -> dict[str, Any]:
    """
    레거시(넓은 테이블, 구 세로형) → 현재 세로 스키마.
    반환: 이관 요약 dict.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='field_change_log'"
    )
    if not cur.fetchone():
        ensure_table(cur)
        conn.commit()
        return {"action": "created_empty"}

    cur.execute("PRAGMA table_info(field_change_log)")
    cols = [r[1] for r in cur.fetchall()]

    if "필드명" in cols and "변경내용" in cols:
        ensure_table(cur)
        conn.commit()
        return {"action": "already_current"}

    # 넓은 스키마 (작업지시번호당 1행)
    if "사업명변경" in cols:
        cur.execute(
            "SELECT 작업지시번호, 사업명변경, 품명변경, 품번변경, updated_at "
            "FROM field_change_log"
        )
        rows = cur.fetchall()
        cur.execute("DROP TABLE field_change_log")
        ensure_table(cur)
        inserted = 0
        for wo, sm, pm, pn, ts in rows:
            if not wo:
                continue
            default_ts = ts or datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            for field_name, raw, label in (
                ("사업명", sm, "사업명변경"),
                ("품명", pm, "품명변경"),
                ("품번", pn, "품번변경"),
            ):
                norm = normalize_stored_removed(raw, label)
                if not norm:
                    continue
                cur.execute(
                    """
                    INSERT INTO field_change_log (
                        작업지시번호, 필드명, 변경내용, 변경묶음_id, 기록시각
                    )
                    VALUES (?, ?, ?, NULL, ?)
                    """,
                    (wo, field_name, norm, default_ts),
                )
                inserted += 1
        conn.commit()
        return {"action": "from_wide", "rows_inserted": inserted}

    # 구 세로형: field_name + removed_text
    if "field_name" in cols and "removed_text" in cols:
        ts_col = "recorded_at" if "recorded_at" in cols else "updated_at"
        cur.execute(
            f"""
            SELECT 작업지시번호, field_name, removed_text, {ts_col}
            FROM field_change_log
            """
        )
        rows = cur.fetchall()
        cur.execute("DROP TABLE field_change_log")
        ensure_table(cur)
        inserted = 0
        for wo, fn, detail, ts in rows:
            if not wo or not fn:
                continue
            if str(fn) not in ALLOWED_FIELD_NAMES:
                continue
            d = normalize_stored_removed(detail, label_for_field(str(fn)))
            if not d:
                continue
            t = ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cur.execute(
                """
                INSERT INTO field_change_log (
                    작업지시번호, 필드명, 변경내용, 변경묶음_id, 기록시각
                )
                VALUES (?, ?, ?, NULL, ?)
                """,
                (wo, str(fn), d, t),
            )
            inserted += 1
        conn.commit()
        return {"action": "from_old_narrow_en", "rows_inserted": inserted}

    # 알 수 없는 스키마: 백업 없이 재생성하면 데이터 손실 → 에러
    raise RuntimeError(
        "field_change_log 스키마를 자동 이관할 수 없습니다. "
        f"컬럼: {cols}"
    )
