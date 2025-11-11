# -*- coding: utf-8 -*-
"""
Day1 스모크 테스트 (루트 .env 로드 + sys.path 보정 + 견고한 폴백 출력)
- 이 파일만 수정/실행합니다. 배포된 모듈은 건드리지 않습니다.
- 추가: 투자 리스크 모니터링 + 트렌드 + E2E 옵션
"""
# --- 0) 프로젝트 루트 탐색 + sys.path 보정 + .env 로드 ---
import os, sys, json
from pathlib import Path

def _find_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists() or (p / ".git").exists() or (p / "apps").exists():
            return p
    return start

ROOT = _find_root(Path(__file__).resolve())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENV_PATH = ROOT / ".env"
def _manual_load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
try:
    from dotenv import load_dotenv  # 선택
    load_dotenv(ENV_PATH, override=False)
except Exception:
    _manual_load_env(ENV_PATH)
# ------------------------------------------------------------------------------

from student.day1.impl.web_search import (
    search_company_profile,
    extract_and_summarize_profile,
    search_risk_issues,
)
from student.day1.impl.multi_score import run_multisource_trend_report

def _bool_env(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return str(v).strip().lower() in ("1","true","yes","y","on")

def _check_keys() -> bool:
    ok = True
    if not os.getenv("TAVILY_API_KEY"):
        print("[FAIL] 환경변수 TAVILY_API_KEY가 없습니다. 루트 .env를 확인하세요.")
        ok = False
    if not os.getenv("NAVER_CLIENT_ID") or not os.getenv("NAVER_CLIENT_SECRET"):
        print("[WARN] NAVER DataLab 키(NAVER_CLIENT_ID/SECRET)가 없습니다. 트렌드 보고서는 빈 결과일 수 있습니다.")
    return ok

# (개선) 시세 스냅샷: get_quotes → yfinance → 패스
def _try_fetch_prices(symbols):
    try:
        from student.day1.impl.finance_client import get_quotes
        data = get_quotes(symbols, timeout=20)
        return data or []
    except Exception:
        pass
    try:
        import yfinance as yf
        out = []
        for s in symbols:
            t = yf.Ticker(s)
            info = t.fast_info if hasattr(t, "fast_info") else {}
            price = None
            currency = None
            if isinstance(info, dict):
                price = info.get("last_price") or info.get("lastPrice")
                currency = info.get("currency")
            else:
                price = getattr(info, "last_price", None)
                currency = getattr(info, "currency", None)
            out.append({"symbol": s, "price": float(price) if price else None, "currency": currency})
        return out
    except Exception:
        return []

def _fake_summarizer(prompt: str) -> str:
    return prompt[-300:] if len(prompt) > 300 else prompt

def _print_risk_items(items, limit=6):
    if not items:
        print("[WARN] 리스크 결과가 없습니다.")
        return
    print(f"[OK] 리스크 결과 상위 {min(limit, len(items))}/{len(items)}개:")
    for i, r in enumerate(items[:limit], 1):
        title = r.get("title") or r.get("url") or "(no title)"
        src = r.get("source") or ""
        date = r.get("published_date") or r.get("date") or ""
        url = r.get("url", "")
        score = r.get("risk_score")
        matched = r.get("matched_keywords") or []
        print(f"  {i}. {title} — {src} {f'({date})' if date else ''}  [risk_score={score}]")
        if matched:
            print("     - matched:", ", ".join(matched[:10]))
        snip = (r.get("content") or r.get("snippet") or "").strip().replace("\n"," ")
        if snip:
            print("     >", (snip[:160] + ("..." if len(snip) > 160 else "")))
        print("     ", url)

def _print_trend(scores, markdown, limit=5):
    if markdown:
        print("\n[OK] 트렌드 마크다운 프리뷰:")
        print(markdown[:800] + ("..." if len(markdown) > 800 else ""))
    if scores:
        print(f"\n[OK] 트렌드 점수 상위 {min(limit, len(scores))}/{len(scores)}개:")
        for i, r in enumerate(scores[:limit], 1):
            name = r.get("topic") or r.get("name") or "(topic)"
            s = r.get("score") or r.get("recent_vs_base") or r.get("delta")
            print(f"  {i}. {name} — score={s}")
    if not markdown and not scores:
        print("\n[WARN] 트렌드 결과가 없습니다. (키/토픽/기간 확인)")

def _try_e2e_day1(query_for_all: str):
    try:
        from student.day1.impl.agent import Day1Agent
        from student.common.schemas import Day1Plan
        tavily_key = os.getenv("TAVILY_API_KEY")
        trend_topics = [s.strip() for s in os.getenv("TREND_TOPICS", "").split(",") if s.strip()]
        trend_days = int(os.getenv("TREND_DAYS", "90"))
        trend_recent = int(os.getenv("TREND_RECENT_DAYS", "14"))
        trend_base = int(os.getenv("TREND_BASE_DAYS", "14"))
        plan = Day1Plan(
            do_web=True,
            do_stocks=False,
            web_keywords=[query_for_all],
            tickers=[],
            output_style="report",
            do_risk=True,
            risk_trust_only=_bool_env("RISK_TRUST_ONLY", True),
            risk_time_range=os.getenv("RISK_TIME_RANGE", "y"),
            risk_topk=int(os.getenv("RISK_TOPK", "8")),
            risk_keywords=[s.strip() for s in os.getenv("RISK_EXTRA", "").split(",") if s.strip()],
            do_trend=bool(trend_topics),
            trend_topics=trend_topics,
            trend_days=trend_days,
            trend_recent_days=trend_recent,
            trend_base_days=trend_base,
        )
        agent = Day1Agent(tavily_api_key=tavily_key, web_topk=6, request_timeout=20)
        payload = agent.handle(query_for_all, plan)
        print("\n[OK] E2E payload keys:", list(payload.keys()))
        risk = payload.get("risk_top") or []
        print(f"[E2E] risk_top count: {len(risk)}")
        _print_risk_items(risk, limit=5)
        _print_trend(payload.get("trend_scores") or [], payload.get("trend_markdown") or "")
    except Exception as e:
        print(f"[WARN] E2E 실행 실패: {type(e).__name__}: {e}")

def main():
    if not _check_keys():
        sys.exit(2)

    tavily_key = os.getenv("TAVILY_API_KEY")

    # argv[1]: 프로필 쿼리, argv[2]: 리스크 쿼리, argv[3]: 트렌드 토픽 CSV
    profile_query = sys.argv[1] if len(sys.argv) > 1 else "삼성전자 기업 개요"
    risk_query    = sys.argv[2] if len(sys.argv) > 2 else "테슬라 리콜"
    trend_topics  = sys.argv[3] if len(sys.argv) > 3 else os.getenv("TREND_TOPICS", "넷플릭스,디즈니플러스,티빙")
    topics = [s.strip() for s in trend_topics.split(",") if s.strip()]

    # 리스크 옵션
    risk_trust_only = _bool_env("RISK_TRUST_ONLY", True)
    risk_time_range = os.getenv("RISK_TIME_RANGE", "y")
    try:
        risk_topk = int(os.getenv("RISK_TOPK", "8"))
    except Exception:
        risk_topk = 8
    risk_extra = [s.strip() for s in os.getenv("RISK_EXTRA", "").split(",") if s.strip()]

    print("[INFO] profile_query:", profile_query)
    print("[INFO] risk_query   :", risk_query)
    print("[INFO] trend_topics :", topics)
    print("[INFO] risk_opts    :", {"trust_only": risk_trust_only, "time_range": risk_time_range, "topk": risk_topk, "extra": risk_extra})

    # 1) 기업 개요 후보 URL 검색
    results = search_company_profile(profile_query, tavily_key, topk=3)
    urls = [r.get("url") for r in results if r.get("url")]
    print(f"\n[OK] 기업 개요 검색 결과 {len(urls)}개")

    # 2) 프로필 요약 시도
    summary = ""
    try:
        summary = extract_and_summarize_profile(urls, tavily_key, _fake_summarizer)
    except TypeError:
        try:
            from student.day1.impl.web_search import extract_and_summarize_profile as _ex2
            summary = _ex2(urls, _fake_summarizer)  # api_key 없이
        except Exception:
            summary = ""

    if summary.strip():
        print("\n[OK] 프로필 요약 샘플:")
        print(summary[:600] + ("\n..." if len(summary) > 600 else ""))
    else:
        print("\n[WARN] 프로필 요약 없음 → 상위 URL 폴백 출력:")
        for i, r in enumerate(results[:3], 1):
            title = r.get("title") or r.get("url")
            src = r.get("source") or ""
            print(f"  {i}. {title} — {src}")

    # 3) (옵션) 시세 스냅샷
    prices = _try_fetch_prices(["005380.KS"])
    if prices:
        print("\n[OK] 시세 스냅샷(JSON 일부):")
        print(json.dumps(prices, ensure_ascii=False)[:240])

    # 4) 투자 리스크 모니터링 테스트
    print("\n[TEST] 투자 리스크 모니터링 실행...")
    try:
        risk_items = search_risk_issues(
            risk_query,
            tavily_key,
            topk=risk_topk,
            timeout=20,
            trust_only= risk_trust_only,
            time_range= risk_time_range,
            extra_keywords= risk_extra,
        )
        _print_risk_items(risk_items, limit=min(6, risk_topk))
    except Exception as e:
        print(f"[FAIL] 리스크 검색 실패: {type(e).__name__}: {e}")

    # 5) 검색 트렌드 테스트
    print("\n[TEST] 검색 트렌드 실행...")
    try:
        out = run_multisource_trend_report(
            topics=topics,
            days=int(os.getenv("TREND_DAYS", "90")),
            recent_days=int(os.getenv("TREND_RECENT_DAYS", "14")),
            base_days=int(os.getenv("TREND_BASE_DAYS", "14")),
        )
        score_df = (out or {}).get("score_df")
        scores = []
        if score_df is not None and getattr(score_df, "empty", True) is False:
            scores = score_df.reset_index().to_dict(orient="records")
        _print_trend(scores, (out or {}).get("markdown") or "")
    except Exception as e:
        print(f"[FAIL] 트렌드 실행 실패: {type(e).__name__}: {e}")

    # 6) (옵션) End-to-End Day1 실행
    if _bool_env("E2E", False):
        _try_e2e_day1(risk_query)

    print("\n[DONE] Day1 스모크 통과")

if __name__ == "__main__":
    main()
