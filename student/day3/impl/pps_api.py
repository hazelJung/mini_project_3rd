# -*- coding: utf-8 -*-
"""
PPS OpenAPI 호출 유틸
- 최신 공고만 보기 위해 inqryDiv + inqryBgnDt/inqryEndDt를 엄격히 설정
- .env 없으면 최근 14일로 자동
- 키워드 필터는 클라이언트에서 공고명에 포함 여부로 2차 필터
"""
from __future__ import annotations
import os, math, time, json
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

PPS_BASE = "https://apis.data.go.kr/1230000/BidPublicInfoService"
# 목록 API – 데이터셋마다 오퍼레이션명이 조금 다를 수 있어 두 가지를 시도
OPS_CANDIDATES = [
    "getBidPblancListInfoServcPPSSrch",  # 검색형
    "getBidPblancListInfoServc",         # 일반형
]

def _fmt_yyyymmddhm(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M")

def _date_window_from_env() -> Tuple[str, str]:
    """
    .env에 PPS_DATE_FROM/PPS_DATE_TO가 있으면 사용,
    없으면 최근 14일 ~ 오늘 23:59로 자동
    """
    bgn = os.getenv("PPS_DATE_FROM", "").strip()
    end = os.getenv("PPS_DATE_TO", "").strip()
    if bgn and end:
        return bgn, end
    today = datetime.now(KST)
    start = (today - timedelta(days=14)).replace(hour=0, minute=0, second=0, microsecond=0)
    finish = today.replace(hour=23, minute=59, second=0, microsecond=0)
    return _fmt_yyyymmddhm(start), _fmt_yyyymmddhm(finish)

def _req_params(keyword: Optional[str], page: int, rows: int) -> Dict[str, Any]:
    inqry_bgn, inqry_end = _date_window_from_env()
    params = {
        "type": "json",
        "inqryDiv": "1",           # 1=공고일자 기준(일반적으로 사용)
        "inqryBgnDt": inqry_bgn,   # 예: 202511010000
        "inqryEndDt": inqry_end,   # 예: 202511072359
        "pageNo": str(page),
        "numOfRows": str(rows),
        "serviceKey": os.getenv("PPS_SERVICE_KEY", "").strip() or os.getenv("PPS_API_KEY", "").strip(),
    }
    # 서버측에 제목 검색 파라미터가 제한적일 수 있으므로, 여기서는 넣지 않고
    # 응답 후 클라이언트 필터로 처리(필요시 dminsttNm 등 추가 가능)
    return params

def _call_op(op: str, params: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    url = f"{PPS_BASE}/{op}"
    # API 키 확인
    if not params.get("serviceKey"):
        raise ValueError("PPS_SERVICE_KEY 또는 PPS_API_KEY 환경변수가 설정되지 않았습니다.")
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    result = r.json()
    # API 오류 응답 확인
    if "response" in result and "header" in result["response"]:
        header = result["response"]["header"]
        result_code = header.get("resultCode", "")
        if result_code != "00" and result_code != "0":
            error_msg = header.get("resultMsg", "알 수 없는 오류")
            raise ValueError(f"나라장터 API 오류 (코드: {result_code}): {error_msg}")
    return result

def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    # 표준 응답 구조: response → body → items
    try:
        return payload["response"]["body"].get("items") or []
    except Exception:
        return []

def _link_from_ids(it: Dict[str, Any]) -> str:
    """
    응답에 상세 URL이 없으면 공고번호/차수로 기본 상세URL 조합 (G2B UI는 변동 가능)
    """
    bidno = str(it.get("bidNtceNo") or it.get("bidno") or "").strip()
    bidseq = str(it.get("bidNtceOrd") or it.get("bidseq") or "0").strip()
    if not bidno:
        return ""
    # 대표 상세 페이지 패턴(없으면 공고명만 링크 없이 표시)
    return f"http://www.g2b.go.kr:8101/ep/invitation/publish/bidInfoDtl.do?bidno={bidno}&bidseq={bidseq}"

def _parse_dt(s: str) -> str:
    s = (s or "").strip()
    # 예상 포맷 예: "2025-11-04 15:00:00", "202511041500"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M", "%Y%m%d%H%M%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return s

def _fmt_money(v: Any) -> str:
    try:
        n = int(float(str(v).replace(",", "").strip()))
        return f"{n:,}원"
    except Exception:
        return str(v or "")

def pps_fetch_bids(keyword: Optional[str] = None,
                   page_max: int = 3,
                   rows: int = 50) -> List[Dict[str, Any]]:
    """
    최근 기간(또는 .env 지정 기간)의 입찰공고 목록을 수집.
    - 서버 파라미터로 날짜 필터 적용
    - 제목 키워드는 클라이언트에서 포함여부로 2차 필터
    """
    params0 = _req_params(keyword=keyword, page=1, rows=rows)
    all_items: List[Dict[str, Any]] = []
    last_error = None
    
    for op in OPS_CANDIDATES:
        try:
            # 페이지네이션
            for page in range(1, page_max + 1):
                params = dict(params0, pageNo=str(page))
                data = _call_op(op, params)
                items = _extract_items(data)
                if not items:
                    break
                all_items.extend(items)
            if all_items:
                break
        except Exception as e:
            last_error = e
            continue
    
    # 모든 오퍼레이션이 실패한 경우
    if not all_items and last_error:
        raise last_error

    # 클라이언트 키워드 필터(제목) - 더 유연한 필터링
    if keyword:
        key = keyword.strip()
        if key:
            # 키워드를 단어로 분리 (예: "VFX 용역" -> ["VFX", "용역"])
            keywords = [k.strip().lower() for k in key.split() if k.strip()]
            if keywords:
                filtered = []
                for it in all_items:
                    title = str(it.get("bidNtceNm") or it.get("bidNm") or it.get("ntceNm") or "").lower()
                    agency = str(it.get("dminsttNm") or it.get("ntceInsttNm") or it.get("orgNm") or "").lower()
                    # 전체 키워드 문자열이 포함되거나, 개별 키워드 중 하나라도 포함되면 포함
                    full_key = key.lower()
                    if (full_key in title or full_key in agency or 
                        any(kw in title or kw in agency for kw in keywords)):
                        filtered.append(it)
                all_items = filtered

    return all_items

def to_common_schema(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    공통 표시 스키마로 변환
    title, agency, announce_date, close_date, budget, url, raw
    """
    out: List[Dict[str, Any]] = []
    for it in items:
        title = str(it.get("bidNtceNm") or it.get("bidNm") or it.get("ntceNm") or "").strip()
        agency = str(it.get("dminsttNm") or it.get("ntceInsttNm") or it.get("orgNm") or "").strip()
        announce = _parse_dt(str(it.get("bidNtceDt") or it.get("ntceDt") or it.get("bidBeginDt") or ""))
        close = _parse_dt(str(it.get("bidClseDt") or it.get("opengDt") or it.get("bidEndDt") or ""))
        budget = _fmt_money(it.get("presmptPrce") or it.get("asignBdgtAmt") or it.get("totPrdprc") or "")
        url = str(it.get("bidNtceUrl") or _link_from_ids(it)).strip()
        out.append({
            "title": title or "(제목 없음)",
            "agency": agency or "-",
            "announce_date": announce or "-",
            "close_date": close or "-",
            "budget": budget or "-",
            "url": url,
            "raw": it,
        })
    return out
