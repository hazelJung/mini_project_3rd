# -*- coding: utf-8 -*-
"""
Day3Agent: 정부사업 공고 에이전트(Agent-as-a-Tool)
- 입력: query(str), plan(Day3Plan)
- 동작: fetch → normalize → rank
- 출력: {"type":"gov_notices","query": "...","items":[...]}  // items는 정규화된 공고 리스트
"""

from __future__ import annotations
from typing import Dict, Any, List

import os
from ...common.schemas import Day3Plan

# 수집 → 정규화 → 랭크 모듈
from . import fetchers          # NIPA, Bizinfo, 일반 Web 수집
from .normalize import normalize_all   # raw → 공통 스키마 변환
from .rank import rank_items           # 쿼리와의 관련도/마감일/신뢰도 등으로 정렬

from .pipeline import find_notices  # ADK Day3 개선 추가

def _set_source_topk(plan: Day3Plan) -> Day3Plan:
    """
    fetchers 모듈의 (기본)소스별 TopK 상수와 plan 값을 싱크.
    - 이 함수는 실습 편의를 위해 제공. 내부에서 fetchers.NIPA_TOPK 등 값 갱신.
    """
    # TODO[DAY3-I-01]:
    # 1) plan.nipa_topk, plan.bizinfo_topk, plan.web_topk 값을 정수로 변환해 1 이상으로 보정
    # 2) fetchers.NIPA_TOPK / fetchers.BIZINFO_TOPK / fetchers.WEB_TOPK에 반영
    # 3) 보정한 plan을 반환
    import fetchers  # 같은 패키지라면: from . import fetchers

    def _fix(v: Any) -> int:
        try:
            iv = int(v)
        except Exception:
            iv = 1
        return iv if iv >= 1 else 1

    # 1) plan 값 보정
    plan.nipa_topk = _fix(getattr(plan, "nipa_topk", 1))
    plan.bizinfo_topk = _fix(getattr(plan, "bizinfo_topk", 1))
    plan.web_topk = _fix(getattr(plan, "web_topk", 1))

    # 2) fetchers 상수에 반영
    fetchers.NIPA_TOPK = plan.nipa_topk
    fetchers.BIZINFO_TOPK = plan.bizinfo_topk
    fetchers.WEB_TOPK = plan.web_topk

    # 3) 보정된 plan 반환
    return plan


# class Day3Agent:
#     def __init__(self):
#         """
#         외부 API 키 등 환경변수 확인 (없어도 동작은 하되 결과가 빈 배열일 수 있음)
#         - 예: os.getenv("TAVILY_API_KEY", "")
#         """
#         # TODO[DAY3-I-02]: 필요한 키를 읽고, 인스턴스 필드로 보관(옵션)
#         import os
#         self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
#         self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
#         # 선택 필드들(있으면 내부 fetchers에서 활용)
#         self.http_proxy: str = os.getenv("HTTP_PROXY", os.getenv("http_proxy", ""))
#         self.https_proxy: str = os.getenv("HTTPS_PROXY", os.getenv("https_proxy", ""))

#     def handle(self, query: str, plan: Day3Plan = Day3Plan()) -> Dict[str, Any]:
#         """
#         End-to-End 파이프라인:
#           1) _set_source_topk(plan)  // 입력 plan의 topk를 fetchers에 반영
#           2) fetch 단계
#              - NIPA: fetchers.fetch_nipa(query, plan.nipa_topk)
#              - Bizinfo: fetchers.fetch_bizinfo(query, plan.bizinfo_topk)
#              - Web fallback(옵션): plan.use_web_fallback and plan.web_topk > 0 이면 fetchers.fetch_web(...)
#              → raw 리스트에 모두 누적
#           3) normalize 단계: normalize_all(raw)
#              - 출처가 제각각인 raw를 공통 스키마(제목/title, URL, 마감/기간, 주체/부처 등)로 변환
#           4) rank 단계: rank_items(norm, query)
#              - 질의 관련도, 마감 임박도, 신뢰도 점수 등을 반영해 정렬/필터링
#           5) 결과 페이로드 구성:
#              { "type": "gov_notices", "query": query, "items": ranked }
#         예외 처리:
#           - 각 단계에서 예외가 난다면 최소한 비어 있는 리스트라도 반환하도록 하거나,
#             상위에서 try/except로 감싼다(이번 과제에선 간단 구현 권장).
#         """
#         # TODO[DAY3-I-03]: 위 단계 구현
#         # 0) 결과 기본형
#         payload: Dict[str, Any] = {
#             "type": "gov_notices",
#             "query": query or "",
#             "items": [],
#         }

#         try:
#             # 1) 소스별 TopK 동기화
#             _set_source_topk(plan)

#             # 2) 수집 단계
#             raw: List[Dict[str, Any]] = []

#             try:
#                 nipa_items = fetchers.fetch_nipa(query, plan.nipa_topk)
#             except Exception:
#                 nipa_items = []
#             raw.extend(nipa_items or [])

#             try:
#                 bizinfo_items = fetchers.fetch_bizinfo(query, plan.bizinfo_topk)
#             except Exception:
#                 bizinfo_items = []
#             raw.extend(bizinfo_items or [])

#             if getattr(plan, "use_web_fallback", False) and int(getattr(plan, "web_topk", 0)) > 0:
#                 try:
#                     # fetch_web 시그니처에 api_key가 있다면 전달, 없다면 무시됩니다.
#                     web_kwargs = {}
#                     if self.tavily_api_key:
#                         web_kwargs["api_key"] = self.tavily_api_key
#                     web_items = fetchers.fetch_web(query, plan.web_topk, **web_kwargs)
#                 except Exception:
#                     web_items = []
#                 raw.extend(web_items or [])

#             # 3) 정규화
#             try:
#                 norm = normalize_all(raw)
#             except Exception:
#                 norm = []

#             # 4) 랭킹/정렬
#             try:
#                 ranked = rank_items(norm, query)
#             except Exception:
#                 ranked = norm or []

#             # 5) 페이로드 구성
#             payload["items"] = ranked

#         except Exception as e:
#             # 상위에서 잡을 수 있도록 간단 페이로드 유지
#             payload["error"] = f"Day3 handle error: {e}"

#         return payload



class Day3Agent:
    def __init__(self):
        import os
        self.tavily_key = os.getenv("TAVILY_API_KEY", "")
        self.use_pps = os.getenv("USE_PPS", "1")  # 파이프라인에서도 읽지만 진단용으로 보관

    def handle(self, query: str, plan: Day3Plan = Day3Plan()) -> Dict[str, Any]:
        """
        ADK에서도 스모크와 동일한 경로로 실행: pipeline.find_notices 사용
        """
        try:
            return find_notices(query)  # ← 스모크와 같은 함수 호출 (PPS 병합 포함)
        except Exception as e:
            # 폴백: 기존 fetchers 흐름 (원래 구현이 있었다면 여기에 남겨도 OK)
            from .fetchers import fetch_nipa, fetch_bizinfo, fetch_web
            from .normalize import normalize_all
            from .rank import rank_items
            raw = []
            try: raw += fetch_nipa(query, topk=plan.nipa_topk)
            except Exception: pass
            try: raw += fetch_bizinfo(query, topk=plan.bizinfo_topk)
            except Exception: pass
            if plan.use_web_fallback and plan.web_topk > 0:
                try: raw += fetch_web(query, topk=plan.web_topk)
                except Exception: pass
            norm = normalize_all(raw)
            ranked = rank_items(norm, query)
            return {"type":"gov_notices","query":query,"items":ranked}