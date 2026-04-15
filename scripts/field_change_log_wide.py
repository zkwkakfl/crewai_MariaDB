"""호환용 별칭: field_change_log 세로 스키마(field_change_log.py)로 위임."""

from __future__ import annotations

import sqlite3

from field_change_log import (
    LOG_COLUMN_TO_FIELD_NAME,
    migrate_legacy_schema,
    normalize_stored_removed,
    ensure_table,
    insert_field_change,
)

# 레거시 스크립트가 expect 하는 이름
migrate_from_narrow_table = migrate_legacy_schema


def ensure_wide_table(cur: sqlite3.Cursor) -> None:
    ensure_table(cur)


def upsert_column(
    conn: sqlite3.Connection,
    *,
    work_order_no: str,
    column: str,
    removed_text: str | None,
) -> None:
    """사업명변경 등 마커 컬럼명 → 필드명으로 매핑 후 이력 1건 append."""
    if column not in LOG_COLUMN_TO_FIELD_NAME:
        raise ValueError(column)
    insert_field_change(
        conn,
        work_order_no=work_order_no,
        field_name=LOG_COLUMN_TO_FIELD_NAME[column],
        change_detail=removed_text,
    )


__all__ = [
    "LOG_COLUMN_TO_FIELD_NAME",
    "ensure_wide_table",
    "migrate_from_narrow_table",
    "normalize_stored_removed",
    "upsert_column",
]
