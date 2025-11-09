# -*- coding: utf-8 -*-
"""
Day1 본체
- 역할: 웹 검색 / 주가 / 기업개요(추출+요약)를 병렬로 수행하고 결과를 정규 스키마로 병합
"""

from __future__ import annotations
from dataclasses import asdict
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.models.lite_llm import LiteLlm
from student.common.schemas import Day1Plan
from student.day1.impl.merge import merge_day1_payload
# 외부 I/O
from student.day1.impl.tavily_client import search_tavily, extract_url
from student.day1.impl.finance_client import get_quotes
from student.day1.impl.web_search import (
    looks_like_ticker,
    search_company_profile,
    extract_and_summarize_profile,
)

DEFAULT_WEB_TOPK = 6
MAX_WORKERS = 4
DEFAULT_TIMEOUT = 20

# ------------------------------------------------------------------------------
# TODO[DAY1-I-01] 요약용 경량 LLM 준비
#  - 목적: 기업 개요 본문을 Extract 후 간결 요약
#  - LiteLlm(model="openai/gpt-4o-mini") 형태로 _SUM에 할당
# ------------------------------------------------------------------------------
_SUM: Optional[LiteLlm] = LiteLlm(model="openai/gpt-4o-mini")


def _summarize(text: str) -> str:
    """
    입력 텍스트를 LLM으로 3~5문장 수준으로 요약합니다.
    실패 시 빈 문자열("")을 반환해 상위 로직이 안전하게 진행되도록 합니다.
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY1-I-02] 구현 지침
    #  - _SUM이 None이면 "" 반환(요약 생략)
    #  - _SUM.invoke({...}) 혹은 단순 텍스트 인자 형태로 호출 가능한 래퍼라면
    #    응답 객체에서 본문 텍스트를 추출하여 반환
    #  - 예외 발생 시 빈 문자열 반환
    # ----------------------------------------------------------------------------
    try:
        prompt = (
            "다음 텍스트를 3-5문장으로 간결하게 요약하세요. 핵심만:\n"
            f"{text}\n\n요약:"
        )
        if _SUM is None:
            return ""
        resp = _SUM.invoke(prompt)

        # 응답 포맷 폴백 처리
        if hasattr(resp, "content") and resp.content:
            return str(resp.content).strip()
        if hasattr(resp, "output_text") and resp.output_text:
            return str(resp.output_text).strip()
        if isinstance(resp, dict) and resp.get("content"):
            return str(resp["content"]).strip()
        if isinstance(resp, str):
            return resp.strip()
        return (str(resp) if resp else "").strip()
    
    except Exception as e:
        print(f"요약 실패: {type(e).__name__}: {e}")
        return ""


class Day1Agent:
    def __init__(self, tavily_api_key: Optional[str], web_topk: int = DEFAULT_WEB_TOPK, request_timeout: int = DEFAULT_TIMEOUT):
        """
        필드 저장만 담당합니다.
        - tavily_api_key: Tavily API 키(없으면 웹 호출 실패 가능)
        - web_topk: 기본 검색 결과 수
        - request_timeout: 각 HTTP 호출 타임아웃(초)
        """
        # ----------------------------------------------------------------------------
        # TODO[DAY1-I-03] 필드 저장
        #  self.tavily_api_key = tavily_api_key
        #  self.web_topk = web_topk
        #  self.request_timeout = request_timeout
        # ----------------------------------------------------------------------------
        self.tavily_api_key = tavily_api_key 
        self.web_topk = web_topk 
        self.request_timeout = request_timeout 

    def handle(self, query: str, plan: Day1Plan) -> Dict[str, Any]:
        """
        병렬 파이프라인:
          1) results 스켈레톤 만들기
             results = {"type":"web_results","query":query,"analysis":asdict(plan),"items":[],
                        "tickers":[], "errors":[], "company_profile":"", "profile_sources":[]}
          2) ThreadPoolExecutor(max_workers=MAX_WORKERS)에서 작업 제출:
             - plan.do_web: search_tavily(검색어, 키, top_k=self.web_topk, timeout=...)
             - plan.do_stocks: get_quotes(plan.tickers)
             - (기업개요) looks_like_ticker(query) 또는 plan에 tickers가 있을 때:
                 · search_company_profile(query, api_key, topk=2) → URL 상위 1~2개
                 · extract_and_summarize_profile(urls, api_key, summarizer=_summarize)
          3) as_completed로 결과 수집. 실패 시 results["errors"]에 '작업명:에러' 저장.
          4) merge_day1_payload(results) 호출해 최종 표준 스키마 dict 반환.
        """
        # ----------------------------------------------------------------------------
        # TODO[DAY1-I-04] 구현 지침(권장 구조)
        #  - results 초기화 (위 키 포함)
        #  - futures 딕셔너리: future -> "web"/"stock"/"profile" 등 라벨링
        #  - 병렬 제출 조건 체크(plan.do_web, plan.do_stocks, 기업개요 조건)
        #  - 완료 수집:
        #      kind == "web"    → results["items"] = data
        #      kind == "stock"  → results["tickers"] = data
        #      kind == "profile"→ results["company_profile"] = text; results["profile_sources"] = urls(옵션)
        #  - 예외: results["errors"].append(f"{kind}: {type(e).__name__}: {e}")
        #  - return merge_day1_payload(results)
        # ----------------------------------------------------------------------------
# 1) results 스켈레톤 초기화 

        results = { 
            "type": "web_results", 
            "query": query, 
            "analysis": asdict(plan), 
            "items": [], 
            "tickers": [], 
            "errors": [], 
            "company_profile": "", 
            "profile_sources": [] 
        } 

        futures = {} 

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor: 
            # 웹 검색 작업 제출 
            if plan.do_web: 
                # web_keywords가 리스트이므로 첫 번째 키워드 사용 (또는 query 직접 사용) 
                search_query = plan.web_keywords[0] if (plan.web_keywords and len(plan.web_keywords) > 0) else query 
                future = executor.submit( 
                    search_tavily, 
                    search_query, 
                    self.tavily_api_key, 
                    top_k=self.web_topk, 
                    timeout=self.request_timeout 
                ) 
                futures[future] = "web" 

            # 주가 조회 작업 제출 
            if plan.do_stocks and plan.tickers: 
                future = executor.submit( 
                    get_quotes, 
                    plan.tickers 
                ) 
                futures[future] = "stock" 

            should_fetch_profile = ( 
                looks_like_ticker(query) or  
                (plan.tickers and len(plan.tickers) > 0) 
            ) 

            if should_fetch_profile: 
                # 기업 개요 검색 (2단계: URL 검색 → 내용 추출) 
                def fetch_company_profile():
                    # 1) 기업 프로필 URL 검색
                    raw = search_company_profile(query, self.tavily_api_key, topk=2)

                    # 딕셔너리 리스트/문자열 리스트 모두 허용 → URL 문자열 리스트로 정규화
                    if not raw:
                        return ("", [])
                    if isinstance(raw, list):
                        if all(isinstance(x, dict) for x in raw):
                            urls = [x.get("url") for x in raw if x.get("url")]
                        else:
                            urls = [str(x) for x in raw if x]
                    else:
                        urls = [str(raw)]

                    urls = [u for u in urls if u]  # 빈 값 제거
                    if not urls:
                        return ("", [])

                    # 2) URL에서 내용 추출 및 요약
                    # 배포본에 따라 api_key 인자를 안 받는 시그니처가 존재 → 두 형태 모두 시도
                    try:
                        profile_text = extract_and_summarize_profile(urls, self.tavily_api_key, summarizer=_summarize)
                    except TypeError:
                        profile_text = extract_and_summarize_profile(urls, summarizer=_summarize)

                    return (profile_text or "", urls)
                
                future = executor.submit(fetch_company_profile) 
                futures[future] = "profile" 

            # 3) 완료된 작업 수집 
            for future in as_completed(futures): 
                kind = futures[future] 
                try: 
                    data = future.result() 
                    # 작업 종류별 결과 처리 
                    if kind == "web": 
                        # 웹 검색 결과 
                        results["items"] = data if data else [] 
                    elif kind == "stock": 
                        # 주가 정보 
                        results["tickers"] = data if data else [] 
                    elif kind == "profile": 
                        # 기업 개요 
                        if data: 
                            profile_text, profile_urls = data 
                            results["company_profile"] = profile_text 
                            results["profile_sources"] = profile_urls 

                except Exception as e: 
                    # 에러 기록 
                    error_msg = f"{kind}: {type(e).__name__}: {str(e)}" 
                    results["errors"].append(error_msg) 
                    print(f"⚠️ {error_msg}") 

        # 4) 결과 병합 및 반환 
        merged_payload = merge_day1_payload(results) 
        return merged_payload 