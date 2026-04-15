"""
SMD 제조업 · 작업지시 중심 MariaDB 설계 협업 Crew 실행 스크립트.

기본: 로컬 Ollama (`ollama serve` 실행 후 사용). 클라우드는 `.env`에 API 키.
`.env`는 `.gitignore`에 포함되어 있어야 합니다(민감 정보 유출 방지).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# 패키지 경로: src 레이아웃
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import find_dotenv, load_dotenv

from smd_crew.crew_factory import create_smd_db_design_crew


def _load_env(*, profile: str | None) -> None:
    """
    환경 변수 로딩 규칙(낮은 쪽 → 높은 쪽 우선권).

    [핵심 로직 요약]
    - 공통: `.env` (로컬 전용, gitignore)
    - 프로파일: `.env.home` / `.env.office` (로컬 전용, gitignore)
    - 최종 오버라이드: `.env.local` (로컬 전용, gitignore)

    [변경 사항의 이유]
    - 같은 레포를 회사/집에서 쓰더라도, PC 사양에 맞는 모델/옵션을 충돌 없이 분리하기 위함.

    [잠재적 리스크]
    - `.env.*` 파일을 실수로 커밋하면 민감 정보가 유출될 수 있으므로 `.gitignore`가 필수.
    """
    # 1) 프로젝트 루트 기준 로컬 전용 공통값
    base = _ROOT / ".env"
    if base.is_file():
        load_dotenv(base, override=True)

    # 2) 프로파일
    if profile:
        prof = _ROOT / f".env.{profile}"
        if prof.is_file():
            load_dotenv(prof, override=True)

    # 3) 최종 오버라이드
    local = _ROOT / ".env.local"
    if local.is_file():
        load_dotenv(local, override=True)

    # 4) 마지막 보조(상위 경로 탐색) — 이미 로드가 됐더라도 누락 대비
    discovered = find_dotenv(usecwd=True)
    if discovered:
        load_dotenv(discovered, override=False)


def _use_ollama() -> bool:
    return os.getenv("SMD_USE_OLLAMA", "true").lower() in ("1", "true", "yes")


def _has_llm_credentials() -> bool:
    """Ollama 기본 모드면 키 없이 True. 클라우드 모드면 API 키 필요."""
    if _use_ollama():
        return True
    keys = ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY")
    return any(os.getenv(k, "").strip() for k in keys)


def _result_text(result: object) -> str:
    if hasattr(result, "raw") and result.raw is not None:
        return str(result.raw)
    return str(result)


def _default_output_path() -> Path:
    """프로젝트 루트에 타임스탬프 파일명으로 저장 (덮어쓰기 방지)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return _ROOT / f"smd_db_design_{ts}.md"


def _write_design_file(path: Path, *, brief: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    one = " ".join(brief.split()).replace("--", "—")
    preview = one[:500] + ("…" if len(one) > 500 else "")
    header = (
        f"<!-- SMD DB 설계 Crew 출력 | 생성(UTC): {iso} -->\n"
        f"<!-- 요청 요약: {preview} -->\n\n"
    )
    path.write_text(header + body, encoding="utf-8", newline="\n")


def _configure_stdio_utf8_on_windows() -> None:
    """Windows 기본 콘솔(cp949)에서 한글·이모지 출력 깨짐을 줄입니다."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def main() -> None:
    _configure_stdio_utf8_on_windows()
    parser = argparse.ArgumentParser(
        description="SMD 작업지시 중심 DB 설계 CrewAI 실행",
    )
    parser.add_argument(
        "--profile",
        choices=("home", "office"),
        default=None,
        help=(
            "머신 프로파일에 맞는 로컬 설정(.env.home / .env.office)을 로드한다. "
            "예) 집 랩탑: --profile home"
        ),
    )
    parser.add_argument(
        "brief",
        nargs="?",
        default=None,
        help="팀에 전달할 요청/배경 설명 (한국어). 생략 시 --quick 여부에 따라 기본 문구 사용",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="에이전트 verbose 끄기",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="LLM 1회만 호출하는 스모크 테스트(쿼터·부하 최소)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "결과(스키마·DDL 포함 마크다운)를 저장할 경로. "
            "기본: 프로젝트 루트에 smd_db_design_UTC시각.md"
        ),
    )
    parser.add_argument(
        "--no-save-file",
        action="store_true",
        help="파일로 저장하지 않고 콘솔 출력만 한다",
    )
    parser.add_argument(
        "--brief-file",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "UTF-8 마크다운/텍스트. 내용이 요청 문장 뒤에 붙는다 "
            "(예: SQLite에서 뽑은 스키마·샘플)."
        ),
    )
    args = parser.parse_args()

    _load_env(profile=args.profile)
    if not _has_llm_credentials():
        print(
            "클라우드 LLM을 쓰려면 API 키가 필요합니다. "
            f"프로젝트 루트({_ROOT})의 `.env` 또는 `.env.<profile>`에 아래 중 하나를 넣거나, "
            "로컬 Ollama를 쓰려면 SMD_USE_OLLAMA=true(기본)로 두세요.\n"
            "  - Gemini: GOOGLE_API_KEY=... 또는 GEMINI_API_KEY=...\n"
            "  - OpenAI: OPENAI_API_KEY=...",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if args.brief is None:
        if args.quick:
            brief = "작업지시 헤더 스모크 테스트 (필드 5개만)"
        else:
            brief = (
                "고객사·사업·품번·품명 마스터와 작업지시 헤더·공정 상세로 "
                "MariaDB 스키마를 설계하고, 역할별 책임을 정리해 달라."
            )
    else:
        brief = args.brief

    if args.brief_file is not None:
        bf = args.brief_file
        if not bf.is_file():
            alt = _ROOT / bf
            if alt.is_file():
                bf = alt
            else:
                print(f"참고 파일을 찾을 수 없습니다: {args.brief_file}", file=sys.stderr)
                raise SystemExit(2)
        ref = bf.read_text(encoding="utf-8")
        brief = (
            brief.rstrip()
            + "\n\n---\n\n[참고: 실제 작업지시·공정발주 데이터]\n\n"
            + ref
        )

    crew = create_smd_db_design_crew(
        brief,
        verbose=not args.quiet,
        quick=args.quick,
    )
    result = crew.kickoff()
    text = _result_text(result)

    out_path = args.output
    if out_path is None and not args.no_save_file:
        out_path = _default_output_path()
    if out_path is not None:
        _write_design_file(out_path.resolve(), brief=brief, body=text)
        print(f"\n[저장됨] {out_path.resolve()}", file=sys.stderr)

    print("\n--- 최종 출력 ---\n")
    print(text)


if __name__ == "__main__":
    main()
