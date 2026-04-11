# 참고: 공정발주내역.sqlite + 설계 지시

## 1) SQLite 원본 `consolidated_data` (실제 파일 기준)

```sql
-- PRAGMA로 확인한 스키마 (공정발주내역.sqlite)
-- 컬럼: id, exported_at, 날짜, 작업지시번호, 고객사, 사업명, 품명, 품번, 공정,
--       고객사납품, 자재입고수량, 발주사양, 폴더명, BOM파일명, 발행리스트
```

| 컬럼명 | 비고 |
|--------|------|
| id | PK |
| exported_at | 내보낸 시각 |
| 날짜 | 작업일 등 |
| 작업지시번호 | 업무 키(문자열) |
| 고객사, 사업명, 품명, 품번 | 마스터 식별 |
| 공정, 고객사납품, 자재입고수량, 발주사양 | 운영 필드 |
| 폴더명, BOM파일명, 발행리스트 | 메타 |

## 2) MariaDB Phase 1 — BOM·PCB·메탈 컬럼

- `BOM`, `PCB`, `메탈TOP`, `메탈BOT` **(또는 rev 필드)** 는 **테이블에는 두되 초기 값은 NULL/공백**으로 둔다.
- 실제 리비전·파일 내용은 아래 **네트워크 폴더 규칙**으로 조회한다.

## 3) FK / errno 150 방지 (필수)

- **`작업지시번호`(VARCHAR)가 `work_orders.id`(INT)를 FK로 참조하면 안 된다** — 타입 불일치로 `errno: 150` 발생.
- 선택지 (하나로 통일):
  - **A)** 자식 테이블은 `work_order_id BIGINT UNSIGNED NOT NULL` + `FOREIGN KEY (work_order_id) REFERENCES work_orders(id)`  
  - **B)** 문자열로만 연결할 때: `work_orders.work_order_no`에 **UNIQUE** + `FOREIGN KEY (work_order_no) REFERENCES work_orders(work_order_no)` (**양쪽 모두 동일 VARCHAR 길이·문자셋**)

## 4) 파일 저장 시나리오 (DB 외부)

- 네트워크 공유 **루트**는 설정 테이블 또는 환경변수로 둔다.
- **경로 규칙**: `{네트워크루트}\{고객사}\{사업명}\{품명(품번)}\` 아래 하위 폴더:
  - `BOM\` — BOM 엑셀 등
  - `원본좌표\`
  - `거버파일\`
- DB에서는 **작업지시번호**로 `고객사, 사업명, 품명, 품번`을 조회한 뒤, 애플리케이션이 위 규칙으로 **물리 경로를 조립**해 엑셀/거버를 연다.
- DB에 파일 BLOB을 넣지 않는다(경로·파일명 메타만 필요 시 VARCHAR).

## 5) 샘플 데이터

- `python scripts/export_sqlite_seed.py` 실행 시 `seed/staging_consolidated_inserts.sql` 에 **CREATE staging_consolidated + INSERT 전체 행**이 생성된다.
- 본 테이블(`work_orders` 등) DDL은 Crew 산출물 기준으로 만든 뒤, **`INSERT ... SELECT`** 로 스테이징에서 이전하거나 컬럼 매핑한다.
