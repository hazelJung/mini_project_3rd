# -*- coding: utf-8 -*-
"""
Day1 결과 정규화
- 다양한 원시 결과(results dict)를 "표준 스키마"로 정리
"""

from typing import Dict, Any, List


def _top_results(items: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
    """
    검색 결과에서 상위 k개만 반환 (None/빈 리스트 안전 처리)
    - items가 None이면 [] 반환
    - k가 0 이하이면 [] 반환
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY1-M-01] 구현 지침
    #  - if not items: return []
    #  - return items[: max(0, k)]
    # ----------------------------------------------------------------------------
    # 정답 구현:
    if not items:
        return []
    return items[: max(0, k)]


def merge_day1_payload(results: Dict[str, Any]) -> Dict[str, Any]:
    web_top = _top_results(results.get("items"), k=5)
    prices = results.get("tickers", [])
    company_profile = results.get("company_profile") or ""
    profile_sources = results.get("profile_sources") or []
    errors = results.get("errors") or []
    query = results.get("query", "")

    # 기존 리스크 결과 유지
    risk_top = _top_results(results.get("risk_items"), k=results.get("analysis", {}).get("risk_topk", 8))

    # 🔹 신규: 트렌드 보고서/표
    trend_markdown = results.get("trend_markdown") or ""
    trend_scores = results.get("trend_scores") or []  # 필요시 표 구조(리스트/DF 직렬화)

    return {
        "type": "day1",
        "query": query,
        "web_top": web_top,
        "prices": prices,
        "company_profile": company_profile,
        "profile_sources": profile_sources,
        "risk_top": risk_top,
        "trend_markdown": trend_markdown,
        "trend_scores": trend_scores,
        "errors": errors,
    }