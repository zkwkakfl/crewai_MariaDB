"""역할별 에이전트 정의 (SMD 제조 · 작업지시 중심 DB 협업)."""

from __future__ import annotations

from typing import Any

from crewai import Agent

from smd_crew.config import DOMAIN_CONTEXT


def _base_kwargs(verbose: bool, llm: Any, max_iter: int | None) -> dict:
    kw: dict[str, Any] = {
        "verbose": verbose,
        "allow_delegation": False,
        "llm": llm,
    }
    if max_iter is not None:
        kw["max_iter"] = max_iter
    return kw


def build_smd_agents(
    *,
    verbose: bool = True,
    llm: Any = None,
    max_iter: int | None = None,
) -> dict[str, Agent]:
    """
    역할별 에이전트를 생성합니다.

    [핵심 로직 요약]
    - 협업 구분을 위해 역할·목표·배경을 역할마다 분리합니다.
    - 순차 호출 부하를 줄이기 위해 4명(영업+PMC, 공정+현장, 품질+자재, 거버넌스)으로 묶었습니다.

    [변경 시 주의]
    - llm은 Crew 수준에서 통일하거나, 에이전트별로 오버라이드할 수 있습니다.
    - max_iter를 낮추면 에이전트 재시도·루프가 줄어들어 호출·토큰이 감소합니다.
    """
    kw = _base_kwargs(verbose, llm, max_iter)
    ctx = DOMAIN_CONTEXT.strip()

    return {
        "biz_pmc": Agent(
            role="영업·CS · 생산관리(PMC)",
            goal="고객사·사업 마스터와 작업지시 헤더(채번, 수량, 납기, 상태)를 한 흐름으로 운영 가능하게 정의한다.",
            backstory=f"{ctx} 고객 응대·견적·수주와 작업지시 확정·일정 관리를 모두 다루며, "
            "마스터 정확성과 현장 핸드오프에 필요한 필드를 빠짐없이 케어한다.",
            **kw,
        ),
        "ops": Agent(
            role="공정·기술 · 현장(라인)",
            goal="공정 라우팅·공정별 수량 의미를 기술 관점에서 정리하고, 라인 실적(착수·완료 등) 최소 세트를 실무적으로 제시한다.",
            backstory=f"{ctx} SMD 공정(인쇄·실장·Reflow 등)과 라인 배치·일일 진행 상황을 함께 다룬다.",
            **kw,
        ),
        "qm_supply": Agent(
            role="품질 · 자재",
            goal="검사·LOT 추적·보관 요구와 작업지시 기준 자재 투입·출고 연동 포인트를 정리한다.",
            backstory=f"{ctx} 불량·감사 추적과 투입·재고 정합성을 동시에 맞추는 역할이다.",
            **kw,
        ),
        "admin": Agent(
            role="시스템·거버넌스",
            goal="역할별 책임(RACI)·운영 정책을 정리하고, 앞 단계 합의를 바탕으로 MariaDB용 CREATE TABLE 등 DDL을 완성한다.",
            backstory=f"{ctx} 데이터 주권과 보안·권한 분리 원칙을 지키며, "
            "스키마는 InnoDB·utf8mb4 기준으로 정합성 있게 제시한다.",
            **kw,
        ),
    }
