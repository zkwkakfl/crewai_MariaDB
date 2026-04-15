"""
[구버전] 백업에서 사업명 이력만 적재하던 스크립트.

현재는 field_change_log 가 **세로 스키마**(변경 필드당 1행, `필드명`·`변경내용` 등)입니다.

- 레거시 → 세로 이관: `python scripts/migrate_field_change_log_wide.py`
- 마커 제거 + 로그 반영: `python scripts/clean_marker_field.py --column 사업명 --marker 사업명변경 --log-column 사업명변경`

이 파일은 호환용으로 남겨 두며, 새 작업에는 `clean_marker_field.py` 사용을 권장합니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def main() -> None:
    print(
        "이 스크립트는 구 방식입니다.\n"
        "  - 세로 로그 이관: python scripts/migrate_field_change_log_wide.py\n"
        "  - 사업명 정리+로그: python scripts/clean_marker_field.py "
        "--column 사업명 --marker 사업명변경 --log-column 사업명변경\n"
    )
    raise SystemExit(0)


if __name__ == "__main__":
    main()
