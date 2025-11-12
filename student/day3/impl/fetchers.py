# -*- coding: utf-8 -*-
"""
정부/공공 포털 및 일반 웹에서 '사업 공고'를 찾기 위한 검색 래퍼

설계 포인트
- '도메인 제한' + '키워드 보강'을 동시에 사용해 노이즈를 줄입니다.
- Tavily Search API를 통해 결과를 가져오며, 결과 스키마는 Day1 web 결과와 동일한 단순 형태를 사용합니다.
- 여기선 '검색'만 담당합니다. 정규화/랭킹은 normalize.py / rank.py에서 수행합니다.

권장 쿼리 전략
- NIPA(정보통신산업진흥원):  site:nipa.kr  +  ("공고" OR "모집" OR "지원")
- Bizinfo(기업마당):       site:bizinfo.go.kr + 유사 키워드
- 일반 웹(Fallback):       쿼리 + "모집 공고 지원 사업" 같은 보조 키워드로 recall 확보
"""

from typing import List, Dict, Any, Optional
import os

# Day1에서 제작한 Tavily 래퍼를 재사용합니다.
from student.day1.impl.tavily_client import search_tavily

DEFAULT_TOPK = 7
DEFAULT_TIMEOUT = 20

# 기본 TopK(권장): NIPA 3, Bizinfo 2, Web 2
NIPA_TOPK = 3
BIZINFO_TOPK = 2
WEB_TOPK = 2

def fetch_nipa(query: str, topk: int = NIPA_TOPK) -> List[Dict[str, Any]]:
    """
    NIPA 도메인에 한정한 사업 공고 검색
    - 영상/미디어 관련 기술에 특화
    - include_domains=["nipa.kr"] 힌트를 주고, 검색 쿼리에도 site:nipa.kr을 붙입니다.
    - '공고/모집/지원' 같은 키워드로 사업 공고 문서를 우선 노출시킵니다.
    반환: Day1 web 스키마 리스트 [{title, url, content/snippet, ...}, ...]
    """
    # 1) API 키 로드
    key = os.getenv("TAVILY_API_KEY", "")

    # 2) 질의어 구성 (영상/미디어 기술 키워드 자동 추가)
    # 영상/미디어 관련 키워드가 없으면 자동 추가
    media_keywords = ["영상", "미디어", "콘텐츠", "스트리밍", "VR", "AR", "AI"]
    has_media_keyword = any(kw in query for kw in media_keywords)
    
    if not has_media_keyword:
        # 영상/미디어 키워드가 없으면 추가 (영화 투자사 관점)
        q = f"{query} 영상 미디어 콘텐츠 공고 모집 지원 site:nipa.kr"
    else:
        q = f"{query} 공고 모집 지원 site:nipa.kr"

    # 3) Tavily 검색 (도메인 한정)
    results = search_tavily(
        q,
        key,
        top_k=int(topk),
        timeout=DEFAULT_TIMEOUT,
        include_domains=["nipa.kr"],
    )

    # 4) source 필드 추가
    for r in (results or []):
        r["source"] = "NIPA"
    
    return results or []

def fetch_bizinfo(query: str, topk: int = BIZINFO_TOPK) -> List[Dict[str, Any]]:
    """
    Bizinfo(기업마당) 도메인에 한정한 사업 공고 검색
    - 영상/미디어 관련 기술에 특화
    - include_domains=["bizinfo.go.kr"]
    - '공고/모집/지원' 키워드 보강
    """
    key = os.getenv("TAVILY_API_KEY", "")

    # 영상/미디어 관련 키워드가 없으면 자동 추가
    media_keywords = ["영상", "미디어", "콘텐츠", "스트리밍", "VR", "AR", "AI"]
    has_media_keyword = any(kw in query for kw in media_keywords)
    
    if not has_media_keyword:
        q = f"{query} 영상 미디어 콘텐츠 공고 모집 지원 site:bizinfo.go.kr"
    else:
        q = f"{query} 공고 모집 지원 site:bizinfo.go.kr"

    results = search_tavily(
        q,
        key,
        top_k=int(topk),
        timeout=DEFAULT_TIMEOUT,
        include_domains=["bizinfo.go.kr"],
    )
    
    # source 필드 추가
    for r in (results or []):
        r["source"] = "BizInfo"
    
    return results or []

def fetch_web(query: str, topk: int = WEB_TOPK, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    일반 웹 Fallback: 영상/미디어 관련 기술 사업 공고와 관련된 키워드를 넣어 Recall 확보
    - 도메인 제한 없이 Tavily 기본 검색 사용
    - 가짜/홍보성 페이지 노이즈는 뒤 단계(normalize/rank)에서 걸러냅니다.
    """
    key = api_key or os.getenv("TAVILY_API_KEY", "")
    
    # 영상/미디어 관련 키워드가 없으면 자동 추가
    media_keywords = ["영상", "미디어", "콘텐츠", "스트리밍", "VR", "AR", "AI"]
    has_media_keyword = any(kw in query for kw in media_keywords)
    
    if not has_media_keyword:
        q = f"{query} 영상 미디어 콘텐츠 모집 공고 지원 사업"
    else:
        q = f"{query} 모집 공고 지원 사업"
    
    results = search_tavily(
        q,
        key,
        top_k=int(topk),
        timeout=DEFAULT_TIMEOUT,
    )
    
    # source 필드 추가
    for r in (results or []):
        r["source"] = "웹"
    
    return results or []

def fetch_all(query: str) -> List[Dict[str, Any]]:
    """
    편의 함수: 현재 설정된 전 소스에서 가져오기
    주의) 실전에서는 소스별 topk를 plan을 통해 주입받아야 합니다.
    """
    # TODO[DAY3-F-04]:
    # - 위 세 함수를 순서대로 호출해 리스트를 이어붙여 반환
    # - 실패 시 빈 리스트라도 반환(try/except로 유연 처리 가능)
    out: List[Dict[str, Any]] = []

    # NIPA
    try:
        out.extend(fetch_nipa(query) or [])
    except Exception:
        # 로깅 가능: logger.exception("fetch_nipa failed", exc_info=True)
        pass

    # Bizinfo
    try:
        out.extend(fetch_bizinfo(query) or [])
    except Exception:
        pass

    # Web (fallback)
    try:
        out.extend(fetch_web(query) or [])
    except Exception:
        pass

    return out
