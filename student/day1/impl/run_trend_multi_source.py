# --- robust .env loader: pick exactly one .env with non-empty keys ---
from pathlib import Path as _Path
import os as _os

def _load_env_once() -> str | None:
    try:
        from dotenv import load_dotenv, find_dotenv, dotenv_values  # type: ignore
    except Exception:
        return None

    wanted = {"NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "YOUTUBE_API_KEY"}
    candidates = []

    p1 = _Path.cwd() / ".env"
    p2 = _Path(__file__).resolve().parent / ".env"
    p3s = find_dotenv(filename=".env", usecwd=True)
    if p1.exists(): candidates.append(p1)
    if p2.exists(): candidates.append(p2)
    if p3s: candidates.append(_Path(p3s))

    chosen = None
    for p in candidates:
        try:
            kv = dotenv_values(p)
        except Exception:
            continue
        if any(kv.get(k) for k in wanted):
            chosen = p
            break
    if chosen is None and candidates:
        chosen = candidates[0]
    if chosen:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=chosen, override=True)
        return str(chosen)
    return None

_LOADED_ENV_PATH = _load_env_once()
# --------------------------------------------------------------------

# -*- coding: utf-8 -*-
import os
from datetime import datetime
from pathlib import Path
import traceback

try:
    import numpy as np  # noqa: F401
except Exception:
    np = None  # type: ignore
try:
    import pandas as pd  # noqa: F401
except Exception:
    pd = None  # type: ignore

def _env_bool(name: str) -> bool:
    v = os.getenv(name)
    return bool(v and v.strip())

def _print_env_check():
    print("ENV FILE LOADED:", _LOADED_ENV_PATH or "(none)")
    print(
        "ENV CHECK:",
        "NAVER_CLIENT_ID:", _env_bool("NAVER_CLIENT_ID"),
        "NAVER_CLIENT_SECRET:", _env_bool("NAVER_CLIENT_SECRET"),
    )

# Import after .env is loaded
def _import_runner():
    from student.trends.multi_score import run_multisource_trend_report, SourceWeights  # type: ignore
    return run_multisource_trend_report, SourceWeights

TOPICS = [
    "넷플릭스", "넷플릭스 코리아", "넷플릭스 한국",
    "디즈니플러스", "디즈니플러스 한국", "디즈니플러스 코리아",
    "티빙",
    "웨이브",
]

def _ensure_output_dir() -> Path:
    out_dir = Path("data") / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def main():
    _print_env_check()

    try:
        run_multisource_trend_report, SourceWeights = _import_runner()
    except Exception as e:
        out_dir = _ensure_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"{ts}__trend_multisource.md"
        md = [
            "# 콘텐츠 트렌드 스코어링(멀티소스)",
            f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 오류",
            f"- `student.trends.multi_score` 임포트 실패: {e.__class__.__name__}",
            "",
            "### Traceback (요약)",
            "```",
            "\n".join(traceback.format_exc().splitlines()[-10:]),
            "```",
        ]
        md_text = "\n".join(md)
        md_path.write_text(md_text, encoding="utf-8")
        print(md_text)
        return

    # Weights 객체는 호환용(네이버만 사용)
    weights = SourceWeights(google=0.0, naver=1.0, sns=0.0, youtube=0.0)

    try:
        out = run_multisource_trend_report(
            topics=TOPICS,
            days=90,
            recent_days=14,
            base_days=14,
            geo="KR",
            weights=weights,
        )
    except Exception as e:
        out_dir = _ensure_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = out_dir / f"{ts}__trend_multisource.md"
        md = [
            "# 콘텐츠 트렌드 스코어링(멀티소스)",
            f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 실행 중 예외",
            f"- {e.__class__.__name__}: {e}",
            "",
            "### Traceback (요약)",
            "```",
            "\n".join(traceback.format_exc().splitlines()[-20:]),
            "```",
        ]
        md_text = "\n".join(md)
        md_path.write_text(md_text, encoding="utf-8")
        print(md_text)
        return

    md = out.get("markdown") if isinstance(out, dict) else None
    if not md:
        md = "# 결과 없음\n- 보고서 생성에 실패했습니다."

    print(md)

    out_dir = _ensure_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"{ts}__trend_multisource.md"
    md_path.write_text(md, encoding="utf-8")

    df = out.get("score_df") if isinstance(out, dict) else None
    if df is not None and getattr(df, "empty", True) is False:
        try:
            df.to_csv(str(md_path).replace(".md", ".csv"), encoding="utf-8-sig", index=False)
        except Exception:
            pass

if __name__ == "__main__":
    main()
