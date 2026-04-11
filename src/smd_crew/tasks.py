"""순차 태스크: 앞 단계 산출물을 context로 넘겨 협업 흐름을 만듭니다."""

from __future__ import annotations

from typing import Any

from crewai import Task

from smd_crew.config import DOMAIN_CONTEXT


def build_db_design_tasks(
    agents: dict[str, Any],
    *,
    user_brief: str,
) -> list[Task]:
    """
    MariaDB(작업지시 중심) 설계 협업용 태스크 체인.

    [핵심 로직 요약]
    - Sequential Crew에서 이전 Task 출력이 다음 Task의 입력(context)이 됩니다.
    - 4단계: 사업·작업지시 → 공정·현장 → 품질·자재 → 통합·거버넌스(+DDL).

    [잠재적 리스크]
    - user_brief가 비어 있으면 모델이 일반론만 낼 수 있으므로 main에서 검증합니다.
    """
    brief = user_brief.strip()
    domain = DOMAIN_CONTEXT.strip()

    t_biz_pmc = Task(
        description=(
            f"{domain}\n\n"
            f"[사용자 요청]\n{brief}\n\n"
            "영업·CS와 생산관리(PMC) 관점을 한 번에 정리하라(한국어).\n"
            "A) 고객사·사업(프로젝트) 마스터 필드 후보, 납기·수량 협의 이력 포인트, "
            "작업지시 연결 시 식별 규칙(중복·오타 방지)\n"
            "B) `work_orders`(작업지시 헤더) 필드 목록, 작업지시번호 채번 규칙 초안, "
            "고객사납품일·전체 지시 수량·상태값 예시"
        ),
        expected_output="A/B 구역이 구분된 불릿·표(필요 시 마크다운). 필드명은 영문 스네이크 케이스 제안 가능.",
        agent=agents["biz_pmc"],
    )

    t_ops = Task(
        description=(
            f"{domain}\n\n"
            "이전 단계(영업·PMC) 산출물을 반영하여 다음을 수행하라.\n"
            "1) 공정 상세 테이블(예: work_order_processes): 공정순서, 공정 코드/명, "
            "공정별 수량 의미(투입 vs 완료 등), 헤더 '전체 수량'과의 정합성 규칙\n"
            "2) 현장(라인) 관점: 라인이 매일 필요로 하는 실적 입력(착공·완료·불량) 최소 세트와 "
            "DB 필드와 1:1 매핑 가능한 우선순위 목록"
        ),
        expected_output="테이블 초안 + 정합성 규칙 + 현장 실적 항목(한국어).",
        agent=agents["ops"],
        context=[t_biz_pmc],
    )

    t_qm_supply = Task(
        description=(
            f"{domain}\n\n"
            "앞선 산출물을 바탕으로 품질과 자재를 함께 정리하라.\n"
            "품질: LOT/배치 추적, 검사 결과, 보관 기간 등 DB 컬럼·제약(UNIQUE, FK) 제안, "
            "작업지시번호와의 연결 방식, 리스크\n"
            "자재: 작업지시 기준 투입·출고 연동 키(품번, 배치 등), "
            "요청/출고 헤더 개념, 당장 필수 vs Phase 2 구분"
        ),
        expected_output="품질·자재 구역이 구분된 목록(한국어).",
        agent=agents["qm_supply"],
        context=[t_biz_pmc, t_ops],
    )

    t_admin = Task(
        description=(
            f"{domain}\n\n"
            "지금까지 모든 단계 산출물을 통합하여 다음을 산출하라. 설명·표는 한국어, "
            "SQL 식별자는 영문 스네이크 케이스를 유지한다.\n"
            "1) 역할별 RACI 표 (영업·CS+PMC, 공정·현장, 품질·자재, 관리자/시스템)\n"
            "2) 테이블별로 '누가 생성/수정/승인'하는지 한 줄 규칙\n"
            "3) 감사 로그·권한 분리에 대한 최소 권장 사항\n"
            "4) MariaDB 마이그레이션 시 우선순위(Phase 1 스키마)\n"
            "5) **필수: MariaDB 실행용 DDL** — 앞 단계에서 제안된 모든 테이블에 대해 다음을 포함한다.\n"
            "   - `CREATE DATABASE` 는 선택(데이터베이스명은 예시로 `smd_wo` 등 한 가지만, "
            "실제 환경에 맞게 바꿀 수 있음을 주석으로 안내).\n"
            "   - 각 테이블마다 `CREATE TABLE` 문: `ENGINE=InnoDB` `DEFAULT CHARSET=utf8mb4` "
            "`COLLATE=utf8mb4_unicode_ci` 명시.\n"
            "   - **FK(errno 150 방지)**: 참조 컬럼과 피참조 컬럼의 타입·길이·부호·문자셋이 완전히 같아야 한다. "
            "`작업지시번호`(문자열)를 쓸 때는 **`FOREIGN KEY (... ) REFERENCES work_orders(work_order_no)`** 처럼 "
            "**문자열 PK/UK**를 참조하거나, 정수 FK만 쓸 때는 **`work_order_id` BIGINT + `REFERENCES work_orders(id)`** 로 통일한다. "
            "**`VARCHAR`가 `INT` id를 참조하는 실수는 금지.**\n"
            "   - 사용자 요청에 BOM/PCB/메탈 컬럼이 있으면 **NULL 허용**으로 두고 Phase 1에서는 비운다고 명시.\n"
            "   - BOM·거버·좌표 **실파일은 DB 밖** 네트워크 경로 "
            "`{루트}\\{고객사}\\{사업명}\\{품명(품번)}\\` 하위 `BOM`, `원본좌표`, `거버파일` 폴더 시나리오를 "
            "DDL 주석 또는 `path_config` 같은 설정 테이블로 문서화한다.\n"
            "   - PK, FK, UNIQUE, NOT NULL, 인덱스(FK·조회 조건)는 앞 단계 합의와 맞게 작성. "
            "FK가 있으면 참조되는 테이블을 먼저 생성하도록 순서를 맞춘다.\n"
            "   - DDL은 마크다운 안에 **```sql ... ```** 코드 블록으로만 제시하고, "
            "블록은 한 번에 복사해 `mysql` 클라이언트에 붙여넣을 수 있게 완성도로 쓴다.\n"
            "   - 운영 반영 전 검토·백업이 필요함을 한 문장으로 명시한다."
        ),
        expected_output=(
            "마크다운 문서: RACI·운영 규칙·Phase 우선순위 설명 + "
            "복사 가능한 ```sql``` DDL 블록(전체 테이블 CREATE)."
        ),
        agent=agents["admin"],
        context=[t_biz_pmc, t_ops, t_qm_supply],
    )

    return [
        t_biz_pmc,
        t_ops,
        t_qm_supply,
        t_admin,
    ]


def build_quick_smoke_tasks(
    agents: dict[str, Any],
    *,
    user_brief: str,
) -> list[Task]:
    """
    LLM 호출 1회만 하는 스모크 테스트용 (무료 쿼터/부하 절약).

    [잠재적 리스크]
    - 전체 협업 흐름 검증은 전체 태스크(build_db_design_tasks)로 수행해야 함.
    """
    brief = user_brief.strip()
    domain = DOMAIN_CONTEXT.strip()

    t = Task(
        description=(
            f"{domain}\n\n"
            f"[요청 요약]\n{brief}\n\n"
            "이 실행은 스모크 테스트다. 반드시 짧게 답하라.\n"
            "1) 작업지시 헤더 테이블에 넣을 필드 후보를 영문 스네이크 케이스로 정확히 5개만 나열\n"
            "2) 한 문장으로 연결 관계 한 가지\n"
            "총 출력 25줄 이내, 불릿 위주."
        ),
        expected_output="5개 필드명 + 연결 한 문장 (한국어).",
        agent=agents["biz_pmc"],
    )
    return [t]
