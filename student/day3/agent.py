# -*- coding: utf-8 -*-
"""
Day3: 정부사업 공고 에이전트
- 역할: 사용자 질의를 받아 Day3 본체(impl/agent.py)의 Day3Agent.handle을 호출
- 결과를 writer로 표/요약 마크다운으로 렌더 → 파일 저장(envelope 포함) → LlmResponse 반환
- 이 파일은 의도적으로 '구현 없음' 상태입니다. TODO만 보고 직접 채우세요.
"""

from __future__ import annotations
from typing import Dict, Any, Optional

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

# Day3 본체
from student.day3.impl.agent import Day3Agent
# 공용 렌더/저장/스키마
from student.common.fs_utils import save_markdown
from student.common.writer import render_day3, render_enveloped
from student.common.schemas import Day3Plan


# ------------------------------------------------------------------------------
# TODO[DAY3-A-01] 모델 선택:
#  - 경량 LLM 식별자를 정해 MODEL에 넣으세요. (예: "openai/gpt-4o-mini")
#  - LiteLlm(model=...) 형태로 초기화합니다.
# ------------------------------------------------------------------------------
MODEL = LiteLlm(model="openai/gpt-4o-mini")  # <- LiteLlm(...)


# ------------------------------------------------------------------------------
# TODO[DAY3-A-02] _handle(query):
#  요구사항
#   1) Day3Plan 인스턴스를 만든다. (필요 시 소스별 topk / 웹 폴백 여부 등 지정)
#      - 예: Day3Plan(nipa_topk=3, bizinfo_topk=2, web_topk=2, use_web_fallback=True)
#   2) Day3Agent 인스턴스를 만든다. (외부 키는 본체에서 환경변수로 접근)
#   3) agent.handle(query, plan)을 호출해 payload(dict)를 반환한다.
#  반환 형태(예):
#   {"type":"gov_notices","query":"...", "items":[{title, url, deadline, agency, ...}, ...]}
# ------------------------------------------------------------------------------
def _handle(query: str) -> Dict[str, Any]:
    # 1) 계획 생성 (필요 시 값 조정 가능)
    plan = Day3Plan(
        nipa_topk=3,
        bizinfo_topk=3,
        web_topk=2,
        use_web_fallback=True,
    )

    # 2) 에이전트 생성
    agent = Day3Agent()

    # 3) 실행 및 반환
    payload: Dict[str, Any] = agent.handle(query, plan)
    return payload


# ------------------------------------------------------------------------------
# TODO[DAY3-A-03] before_model_callback:
#  요구사항
#   1) llm_request에서 사용자 최근 메시지를 찾아 query 텍스트를 꺼낸다.
#   2) _handle(query)로 payload를 만든다.
#   3) writer로 본문 MD를 만든다: render_day3(query, payload)
#   4) 파일 저장: save_markdown(query=query, route='day3', markdown=본문MD)
#   5) envelope로 감싸기: render_enveloped(kind='day3', query=query, payload=payload, saved_path=경로)
#   6) LlmResponse로 최종 마크다운을 반환한다.
#  예외 처리
#   - try/except로 감싸고, 실패 시 "Day3 에러: {e}" 형식의 짧은 메시지로 반환
# ------------------------------------------------------------------------------
def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
    **kwargs,
) -> Optional[LlmResponse]:
    try:
        # 1) 사용자 최근 메시지에서 질의 추출
        last = llm_request.contents[-1] if llm_request.contents else None
        query: str = last.parts[0].text if last and getattr(last, "parts", None) else ""
        if not query:
            return LlmResponse(text="[DAY3] 질의가 비어있습니다. 사업명이나 키워드를 입력해주세요.")

        # 2) 에이전트 실행
        payload: Dict[str, Any] = _handle(query)

        # 3) 본문 마크다운 생성
        body_md: str = render_day3(query, payload)

        # 4) 저장
        saved = save_markdown(query=query, route="day3", markdown=body_md)

        # saved 반환 형태가 문자열 또는 dict일 수 있으므로 경로 보정
        if isinstance(saved, dict):
            saved_path = saved.get("path") or saved.get("filepath") or saved.get("file") or ""
        else:
            saved_path = str(saved)

        # 5) envelope로 감싸기
        md: str = render_enveloped(kind="day3", query=query, payload=payload, saved_path=saved_path)

        # 6) 응답
        return LlmResponse(text=md)

    except Exception as e:
        # 필요 시 로깅 가능: logger.exception("Day3 before_model_callback failed", exc_info=e)
        return LlmResponse(text=f"Day3 에러: {e}")


# ------------------------------------------------------------------------------
# TODO[DAY3-A-04] 에이전트 메타데이터:
#  - name/description/instruction 문구를 명확하게 다듬으세요.
#  - MODEL은 위 TODO[DAY3-A-01]에서 설정한 LiteLlm 인스턴스를 사용합니다.
# ------------------------------------------------------------------------------
day3_gov_agent = Agent(
    name="Day3GovAgent",                        # <- 필요 시 수정
    model=MODEL,                                # <- TODO[DAY3-A-01]에서 설정
    description="정부사업 공고/바우처 정보 수집 및 표 제공",   # <- 필요 시 수정 
    instruction="질의를 기반으로 정부/공공 포털에서 관련 공고를 수집하고 표로 요약해라.", # 프로젝트 목표 결정되면 수정
    tools=[],
    before_model_callback=before_model_callback,
)
