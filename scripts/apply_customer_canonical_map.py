"""
고객사 컬럼: 사용자 매핑표(원본 → 수정) 적용.

실행 전 현재 DB 백업 생성.
원복: `공정발주내역.sqlite.bak_고객사_step1_*` 를 `공정발주내역.sqlite` 로 복사한 뒤 이 스크립트 실행.

최신 표:
- 웨이브 → 웨이브일렉트로닉스
- 웨이브 일렉트로닉스 / 줄바꿈 변형 → 웨이브일렉트로닉스
- 아이스팩·글랜에어테크놀로지·시그웍스: 변경 없음
- 글린에어테크놀로지 → 글랜에어테크놀로지
- 에스엘→SL, KB테크→KB-TECH, LIG 정밀기술→LIG정밀기술, 제이앤에스→JNS
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "공정발주내역.sqlite"
COL = "고객사"

# 순서: 구체적 문자열(공백·줄바꿈) 먼저, 마지막에 단독 '웨이브'
MAPPING: list[tuple[str, str]] = [
    ("웨이브 일렉트로닉스", "웨이브일렉트로닉스"),
    ("웨이브\n일렉트로닉스", "웨이브일렉트로닉스"),
    ("웨이브", "웨이브일렉트로닉스"),
    ("글린에어테크놀로지", "글랜에어테크놀로지"),
    ("에스엘", "SL"),
    ("KB테크", "KB-TECH"),
    ("LIG 정밀기술", "LIG정밀기술"),
    ("제이앤에스", "JNS"),
    ("글랜에어테크놀리지", "글랜에어테크놀로지"),
]


def main() -> None:
    if not DB.is_file():
        raise SystemExit(f"DB 없음: {DB}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB.with_suffix(f".sqlite.bak_고객사_map_{ts}")
    shutil.copy2(DB, bak)
    print(f"백업(실행 전): {bak}")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    total = 0
    for old, new in MAPPING:
        if old == new:
            continue
        cur.execute(
            f'UPDATE consolidated_data SET "{COL}" = ? WHERE "{COL}" = ?',
            (new, old),
        )
        n = cur.rowcount
        total += n
        if n:
            print(f"  {old!r} → {new!r} : {n}행")

    conn.commit()

    cur.execute(f'SELECT id, "{COL}" FROM consolidated_data WHERE "{COL}" LIKE "%시그웍스%"')
    trim_count = 0
    for row_id, val in cur.fetchall():
        if val is None:
            continue
        t = val.strip()
        if t != val:
            cur.execute(
                f'UPDATE consolidated_data SET "{COL}" = ? WHERE id = ?',
                (t, row_id),
            )
            trim_count += cur.rowcount
    conn.commit()
    if trim_count:
        print(f"  (시그웍스 앞뒤 공백 제거) : {trim_count}행")

    conn.close()
    print(f"총 변경 행(매핑): {total}")


if __name__ == "__main__":
    main()
