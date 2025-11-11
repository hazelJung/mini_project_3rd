# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os, math, json
import pandas as pd
import requests

# 디버그 메시지 수집
_DEBUG: List[str] = []
def _dbg(msg: str): _DEBUG.append(msg)

# ---- 공통 유틸 ----
def _now_kr() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))

def _pct(a: float, b: float) -> float:
    if b == 0:
        return float("inf") if a > 0 else 0.0
    return (a - b) / b * 100.0

def _to_datestr(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def _split_windows(ser: pd.Series, recent_days: int, base_days: int) -> Tuple[pd.Series, pd.Series]:
    if ser is None or ser.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    recent = ser.iloc[-recent_days:]
    prev = ser.iloc[-(recent_days + base_days):-recent_days] if len(ser) >= (recent_days + base_days) else ser.iloc[:-recent_days]
    return recent, prev

def _safe_mean(s: pd.Series) -> float:
    return float(s.mean()) if s is not None and len(s) > 0 else 0.0

# ---- NAVER DataLab (검색어트렌드) ----
def _naver_headers() -> Optional[Dict[str, str]]:
    cid = os.getenv("NAVER_CLIENT_ID")
    csec = os.getenv("NAVER_CLIENT_SECRET")
    if not (cid and csec):
        _dbg("NAVER 키 미발견(.env 미로딩 또는 환경변수 미설정)")
        return None
    return {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec, "Content-Type": "application/json"}

def fetch_naver_datalab(topics: List[str], days: int = 90, time_unit: str = "date") -> pd.DataFrame:
    """
    네이버 DataLab 검색량 시계열 수집.
    - 제약: keywordGroups 최대 5개/요청 → 5개씩 나눠 호출 후 outer join 병합
    - 반환: index=datetime, columns=topics
    """
    headers = _naver_headers()
    if headers is None:
        return pd.DataFrame(columns=topics)

    end = _now_kr().date()
    start = end - timedelta(days=days)
    url = "https://openapi.naver.com/v1/datalab/search"

    def _one_call(group: List[str]) -> pd.DataFrame:
        payload = {
            "startDate": _to_datestr(datetime.combine(start, datetime.min.time())),
            "endDate": _to_datestr(datetime.combine(end, datetime.min.time())),
            "timeUnit": time_unit,     # 'date'|'week'|'month'
            "keywordGroups": [{"groupName": t, "keywords": [t]} for t in group],
            "device": "", "ages": [], "gender": ""
        }
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        except requests.RequestException as e:
            _dbg(f"NAVER 요청 오류: {e.__class__.__name__}({e})")
            return pd.DataFrame()

        if r.status_code != 200:
            _dbg(f"NAVER 응답 실패: status={r.status_code} body={r.text[:200]}")
            return pd.DataFrame()

        data = r.json()
        series_map: Dict[str, pd.Series] = {}
        for item in data.get("results", []):
            title = item.get("title")
            rows = item.get("data", []) or []
            if not rows:
                continue
            s = pd.Series({pd.to_datetime(d.get("period")).normalize(): float(d.get("ratio", 0.0)) for d in rows}).sort_index()
            series_map[title] = s

        if not series_map:
            _dbg(f"NAVER 결과 비어있음(그룹={group})")
            return pd.DataFrame()

        df = pd.concat(series_map, axis=1, join="outer")
        df.columns = list(series_map.keys())
        df = df.sort_index()
        return df

    all_df = pd.DataFrame()
    for i in range(0, len(topics), 5):
        group = topics[i:i+5]
        part = _one_call(group)
        if part.empty:
            continue
        all_df = part if all_df.empty else all_df.join(part, how="outer")

    if all_df.empty:
        _dbg("NAVER 전체 결과가 비어있음(청크 호출 후)")
        return pd.DataFrame(columns=topics)

    for t in topics:
        if t not in all_df.columns:
            all_df[t] = 0.0
    return all_df.sort_index()

# ---- 스코어링/렌더 ----
@dataclass
class SourceWeights:
    # 과거 호환을 위해 남겨두지만 네이버만 사용합니다.
    google: float = 0.0
    naver:  float = 1.0
    sns:    float = 0.0
    youtube:float = 0.0

def score_multisource(
    topics: List[str],
    naver_ts: pd.DataFrame,
    recent_days: int = 14,
    base_days: int = 14,
    weights: SourceWeights = SourceWeights(),
) -> pd.DataFrame:
    rows = []
    for t in topics:
        n_mom = None
        if t in getattr(naver_ts, "columns", []):
            nr, np_ = _split_windows(naver_ts[t], recent_days, base_days)
            n_mom = _pct(_safe_mean(nr), _safe_mean(np_))

        # 네이버만 사용
        score = float(n_mom) if (n_mom is not None and math.isfinite(float(n_mom))) else 0.0

        rows.append({
            "topic": t,
            "naver_mom": None if n_mom is None else round(float(n_mom), 2),
            "naver_available": (n_mom is not None and math.isfinite(float(n_mom))),
            "trend_score": round(score, 2),
        })
    return pd.DataFrame(rows).set_index("topic").sort_values("trend_score", ascending=False)

def _fmt_delta(v, available: bool) -> str:
    try:
        if (v is None) or (not available) or (not math.isfinite(float(v))):
            return "+0.0%"
        x = float(v)
        return f"{'+' if x >= 0 else ''}{x:.1f}%"
    except Exception:
        return "+0.0%"

def render_multisource_markdown(score_df: pd.DataFrame, title: str, query_desc: str, notes: Optional[List[str]] = None) -> str:
    ts = _now_kr().strftime("%Y-%m-%d %H:%M")
    lines = [f"# {title}", f"- 질의: {query_desc}", f"- 생성: {ts}"]
    for n in (notes or []): lines.append(f"- 참고: {n}")
    for d in _DEBUG: lines.append(f"- 디버그: {d}")
    lines.append("")
    if score_df.empty:
        lines.append("_데이터가 비어 있습니다._")
        return "\n".join(lines)

    # 하이라이트 (상승 5 / 하락 5)
    top_up = score_df.head(5)
    top_down = score_df.tail(5).sort_values("trend_score")
    lines.append("## 하이라이트")
    for t, row in top_up.iterrows():
        lines.append(f"- **{t} {_fmt_delta(row.get('naver_mom'), bool(row.get('naver_available')))} 검색 변화** (네이버 {_fmt_delta(row.get('naver_mom'), bool(row.get('naver_available')))})")
    if len(score_df) > 7:
        lines.append("")
        for t, row in top_down.iterrows():
            lines.append(f"- **{t} 언급/관심 하락** (네이버 {_fmt_delta(row.get('naver_mom'), bool(row.get('naver_available')))})")

    # 표 (네이버 단일 소스)
    lines.append("")
    lines.append("## 종합 순위(합성 스코어 기준)")
    lines.append("| 순위 | 토픽 | 네이버 모멘텀 | 합성 스코어 |")
    lines.append("|---:|---|---:|---:|")
    for i, (t, row) in enumerate(score_df.iterrows(), 1):
        lines.append(
            f"| {i} | {t} | "
            f"{_fmt_delta(row.get('naver_mom'), bool(row.get('naver_available')))} | "
            f"{row.get('trend_score'):.1f} |"
        )
    return "\n".join(lines)

def run_multisource_trend_report(
    topics: List[str],
    days: int = 90,
    recent_days: int = 14,
    base_days: int = 14,
    geo: str = "KR",  # 호환용 인자
    weights: SourceWeights = SourceWeights(),  # 호환용 인자
) -> Dict[str, Any]:
    naver_ts  = fetch_naver_datalab(topics, days=days, time_unit="date")
    score_df = score_multisource(topics, naver_ts, recent_days, base_days, weights)

    notes = []
    if naver_ts.empty:  notes.append("네이버 DataLab 데이터 사용 불가(빈 응답/권한/쿼터/청크 실패)")

    md = render_multisource_markdown(
        score_df,
        title="콘텐츠 트렌드 스코어링(멀티소스)",
        query_desc="네이버 검색량 기반 모멘텀",
        notes=notes or None,
    )
    return {"score_df": score_df, "markdown": md, "notes": notes, "debug": list(_DEBUG)}
