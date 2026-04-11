"""Crew 조립: Process.sequential + 역할별 에이전트."""

from __future__ import annotations

import os
from typing import Any

from crewai import Crew, LLM, Process

from smd_crew.agents import build_smd_agents
from smd_crew.tasks import build_db_design_tasks, build_quick_smoke_tasks


def _env_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _use_ollama() -> bool:
    """기본 True. SMD_USE_OLLAMA=false 이면 클라우드(Gemini/OpenAI) 분기."""
    return os.getenv("SMD_USE_OLLAMA", "true").lower() in ("1", "true", "yes")


def _ollama_model_id() -> str:
    """CrewAI 형식: ollama/모델명 (ollama/ 접두가 없으면 붙임)."""
    # 기본: Qwen2.5 Coder 3B — `ollama pull qwen2.5-coder:3b` 와 동일한 태그.
    default_tag = "qwen2.5-coder:3b"
    raw = os.getenv("OLLAMA_MODEL", default_tag).strip()
    if not raw:
        raw = default_tag
    if raw.startswith("ollama/") or raw.startswith("ollama_chat/"):
        return raw
    return f"ollama/{raw}"


def _resolve_llm(llm: str | LLM | None, *, quick: bool = False) -> str | LLM | None:
    if llm is not None:
        return llm
    override = os.getenv("SMD_CREW_LLM", "").strip()
    if override:
        return override

    if _use_ollama():
        if quick:
            qm = os.getenv("SMD_CREW_QUICK_MODEL", "").strip()
            if qm:
                return qm if qm.startswith("ollama/") else f"ollama/{qm.lstrip('/')}"
            return _ollama_model_id()
        return _ollama_model_id()

    if quick:
        qm = os.getenv("SMD_CREW_QUICK_MODEL", "").strip()
        if qm:
            return qm
        has_google = bool(
            os.getenv("GOOGLE_API_KEY", "").strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
        )
        if has_google:
            return "gemini-2.0-flash-lite-001"
    # Gemini / OpenAI (SMD_USE_OLLAMA=false)
    has_google = bool(
        os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
    )
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    if has_google and not has_openai:
        return "gemini-2.0-flash-001"
    if has_openai and not has_google:
        return "gpt-4o-mini"
    if has_google:
        return "gemini-2.0-flash-001"
    return "gpt-4o-mini"


def create_smd_db_design_crew(
    user_brief: str,
    *,
    verbose: bool = True,
    llm: str | LLM | None = None,
    quick: bool = False,
) -> Crew:
    """
    SMD 제조업 MariaDB(작업지시 중심) 설계 협업 Crew.

    [핵심 로직 요약]
    - 순차 실행으로 4명(영업+PMC, 공정+현장, 품질+자재, 거버넌스) 관점을 쌓고,
      마지막에 관리자 에이전트가 통합합니다.

    [변경 사항의 이유]
    - allow_delegation=False로 불필요한 위임 루프를 줄입니다.

    [잠재적 리스크]
    - 기본은 로컬 Ollama(SMD_USE_OLLAMA=true). Ollama 미기동 시 연결 오류.
    - 클라우드 사용 시에만 API 키 필요.
    - quick=True일 때는 태스크 1개·에이전트 1명만 사용 (스모크 전용).
    """
    if not user_brief or not user_brief.strip():
        raise ValueError("user_brief는 비어 있을 수 없습니다.")

    resolved = _resolve_llm(llm, quick=quick)
    max_iter = _env_int("SMD_AGENT_MAX_ITER")
    max_rpm = _env_int("SMD_CREW_MAX_RPM")

    full_agents = build_smd_agents(
        verbose=verbose,
        llm=resolved,
        max_iter=max_iter,
    )

    if quick:
        agents_map = {"biz_pmc": full_agents["biz_pmc"]}
        agents_list = [agents_map["biz_pmc"]]
        tasks = build_quick_smoke_tasks(agents_map, user_brief=user_brief)
    else:
        agents_map = full_agents
        agents_list = list(agents_map.values())
        tasks = build_db_design_tasks(agents_map, user_brief=user_brief)

    crew_kw: dict[str, Any] = {
        "agents": agents_list,
        "tasks": tasks,
        "process": Process.sequential,
        "verbose": verbose,
        "llm": resolved,
        "tracing": False if quick else None,
    }
    if max_rpm is not None and max_rpm > 0:
        crew_kw["max_rpm"] = max_rpm

    return Crew(**crew_kw)
