# -*- coding: utf-8 -*-
"""
impl 전용: PPS(나라장터) 검색 + 렌더 + 저장 유틸
- writer.py / fs_utils.py에 의존하지 않도록 독립 저장 로직 포함
- .env의 PPS_* 파라미터를 흡수하고, 없으면 최근 N일(기본 30일)로 자동
- pps_api 함수명/시그니처 차이에 방어적으로 대응
"""
from __future__ import annotations
import os, re
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# pps_api: 환경마다 함수명이 다를 수 있으므로 유연하게 import
try:
    from student.day3.impl.pps_api import pps_fetch_bids as _FETCH  # type: ignore[attr-defined]
except Exception:
    try:
        from student.day3.impl.pps_api import fetch_pps_notices as _FETCH  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        _FETCH = None  # type: ignore[assignment]

try:
    from student.day3.impl.pps_api import to_common_schema as _TO_COMMON  # type: ignore[attr-defined]
except Exception:
    _TO_COMMON = None  # type: ignore[assignment]

KST = timezone(timedelta(hours=9))

# 경로/저장 유틸(독립 구현)
def _slugify(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9A-Za-z가-힣\-_\.]+", "", text)
    return text[:120] or "output"

def _find_project_root() -> Path:
    start = Path(__file__).resolve()
    markers = ("uv.lock", "pyproject.toml", "apps", "student", ".git")
    for p in [start, *start.parents]:
        try:
            if any((p / m).exists() for m in markers):
                return p
        except Exception:
            pass
    return Path.cwd().resolve()

def _default_output_dir() -> Path:
    env_dir = os.getenv("OUTPUT_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (_find_project_root() / "data" / "processed").resolve()

def _save_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding=encoding, newline="\n") as f:
        f.write(text)

# 파라미터 해석
def _yyyymmddhhmm(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M")

@dataclass
class PpsParams:
    keyword: str
    date_from: str
    date_to: str
    rows: int
    page_max: int
    inqry_div: str  # 쿼리 구분(예: '1': 공고)

def resolve_params(user_query: str) -> PpsParams:
    # 날짜 기본: 최근 N일
    last_days = int(os.getenv("PPS_DEFAULT_LAST_DAYS", "30") or "30")
    now = datetime.now(KST)
    default_from = _yyyymmddhhmm(now - timedelta(days=last_days))
    default_to = _yyyymmddhhmm(now)

    date_from = (os.getenv("PPS_DATE_FROM", "") or default_from).replace(" ", "").replace("-", "")
    date_to   = (os.getenv("PPS_DATE_TO", "")   or default_to).replace(" ", "").replace("-", "")
    rows      = int(os.getenv("PPS_ROWS", "100") or "100")
    page_max  = int(os.getenv("PPS_PAGE_MAX", "3") or "3")
    inqry_div = os.getenv("PPS_INQRY_DIV", "1").strip() or "1"

    keyword = (user_query or os.getenv("PPS_DEFAULT_QUERY", "")).strip()
    # 키워드가 비어있으면 None으로 설정 (모든 공고 검색)
    if not keyword:
        keyword = None
    return PpsParams(keyword=keyword, date_from=date_from, date_to=date_to,
                     rows=rows, page_max=page_max, inqry_div=inqry_div)

# 데이터 렌더 & 저장
def _render_table(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "관련 공고를 찾지 못했습니다."
    lines = [
        "| 공고명 | 발주기관 | 공고번호 | 공고일자 | 마감일자 | 예산 | 링크 | 첨부 |",
        "|---|---|---|---|---|---:|---|---|",
    ]
    def link(u: str) -> str:
        return f"[바로가기]({u})" if u else "-"
    def attach(a: Any) -> str:
        if not a:
            return "-"
        if isinstance(a, list):
            head = []
            for i, att in enumerate(a[:2], 1):
                name = att.get("name") or att.get("title") or f"첨부{i}"
                url = att.get("url") or ""
                head.append(f"[{name}]({url})" if url else name)
            if len(a) > 2:
                head.append(f"...(+{len(a)-2})")
            return ", ".join(head)
        return str(a)

    for it in items[:30]:
        lines.append(
            "| {title} | {agency} | {bid_no} | {ann} | {close} | {budget} | {url} | {att} |".format(
                title=it.get("title", "-"),
                agency=it.get("agency", "-"),
                bid_no=it.get("bid_no", "") or it.get("bidNo", ""),
                ann=it.get("announce_date", "") or it.get("announceDate", ""),
                close=it.get("close_date", "") or it.get("closeDate", ""),
                budget=it.get("budget", "-"),
                url=link(it.get("url", "")),
                att=attach(it.get("attachments")),
            )
        )
    return "\n".join(lines)

def _render_markdown(query: str, items: List[Dict[str, Any]], saved_path: str) -> str:
    header = (
        f"---\noutput_schema: v1\ntype: markdown\nroute: pps\n"
        f"saved: {saved_path}\nquery: \"{query.replace('\"','\\\"')}\"\n---\n\n"
    )
    body = [f"# 나라장터 입찰공고(최근)","",f"- 질의: {query}","",_render_table(items)]
    footer = f"\n\n---\n> 저장 위치: `{saved_path}`\n"
    return header + "\n".join(body) + footer

def save_markdown(query: str, items: List[Dict[str, Any]], route: str="pps") -> str:
    outdir = _default_output_dir()
    ts = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}__{route}__{_slugify(query)}.md"
    abspath = (outdir / fname).resolve()
    md = _render_markdown(query, items, saved_path=str(abspath))
    _save_text(abspath, md)
    return str(abspath)

# 검색 실행(외부 노출 함수)
def pps_search(query: str) -> str:
    """
    나라장터(G2B) 입찰공고를 검색합니다.
    
    Args:
        query: 검색 키워드 (예: "VFX 용역", "AI 교육 입찰", "나라장터 콘텐츠")
    
    Returns:
        마크다운 형식의 검색 결과 (표 형태로 공고명, 발주기관, 공고번호, 공고일자, 마감일자, 예산, 링크 포함)
    """
    if _FETCH is None:
        return "⚠️ PPS API 모듈(student/day3/impl/pps_api.py)을 찾을 수 없습니다."

    try:
        p = resolve_params(query)
    except Exception as e:
        return f"⚠️ 파라미터 해석 오류: {e}"

    # 호출: pps_fetch_bids는 keyword, page_max, rows만 받음
    raw: List[Dict[str, Any]] = []
    try:
        # pps_fetch_bids의 실제 시그니처에 맞게 호출
        raw = _FETCH(
            keyword=p.keyword if p.keyword else None,
            page_max=p.page_max,
            rows=p.rows,
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f"⚠️ 나라장터 API 호출 오류: {e}\n\n디버그 정보:\n{error_detail}"

    # 공통 스키마 정규화
    items: List[Dict[str, Any]] = []
    if _TO_COMMON:
        try:
            items = _TO_COMMON(raw)
        except Exception:
            items = []

    if not items:
        # 최소 매핑
        for r in (raw or []):
            items.append({
                "title": r.get("bidNtceNm") or r.get("title") or "-",
                "agency": r.get("dminsttNm") or r.get("agency") or r.get("organ", "-"),
                "bid_no": r.get("bidNtceNo") or r.get("bid_no") or r.get("bidNo", ""),
                "announce_date": r.get("bidNtceDate") or r.get("announce_date") or r.get("announceDate", ""),
                "close_date": r.get("opengDt") or r.get("close_date") or r.get("closeDate", ""),
                "budget": r.get("presmptPrce") or r.get("budget", "-"),
                "url": r.get("bidNtceDtlUrl") or r.get("url", ""),
                "attachments": r.get("atchFileList") or r.get("attachments", []),
            })

    # 결과가 비어있을 때 안내 메시지
    if not items:
        keyword_info = f" (키워드: '{p.keyword or query}')" if (p.keyword or query) else ""
        return f"""---
output_schema: v1
type: markdown
route: pps
saved: (no results)
query: "{query.replace('\"','\\\"')}"
---

# 나라장터 입찰공고 검색 결과

- 질의: {query}{keyword_info}

**관련 공고를 찾지 못했습니다.**

가능한 원인:
1. 검색 키워드가 너무 구체적일 수 있습니다. 더 일반적인 키워드로 시도해보세요.
2. 최근 {os.getenv('PPS_DEFAULT_LAST_DAYS', '30')}일 이내에 해당 키워드와 관련된 공고가 없을 수 있습니다.
3. PPS_SERVICE_KEY 환경변수가 설정되지 않았거나 유효하지 않을 수 있습니다.

**제안:**
- 키워드를 더 일반적으로 변경해보세요 (예: "VFX" → "영상", "AI" → "인공지능")
- Day3GovAgent를 사용하여 정부 지원사업/바우처를 검색해보세요.
"""
    
    # 저장 + 본문 반환
    try:
        save_markdown(p.keyword or query, items, route="pps")
    except Exception:
        pass  # 저장 실패해도 결과는 반환
    
    # 렌더 본문만 반환(ADK FunctionTool은 문자열 반환이 간단)
    return _render_markdown(p.keyword or query, items, saved_path="(see header)")
