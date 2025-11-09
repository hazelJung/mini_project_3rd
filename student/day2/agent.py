# -*- coding: utf-8 -*-
"""
Day2: RAG 도구 에이전트
- 역할: Day2 RAG 본체 호출 → 결과 렌더 → 저장(envelope) → 응답
"""

from __future__ import annotations
from typing import Dict, Any
import os

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from kt_aivle.sub_agents.day2.impl.rag import Day2Agent
from kt_aivle.sub_agents.common.writer import render_day2, render_enveloped
from kt_aivle.sub_agents.common.schemas import Day2Plan
from kt_aivle.sub_agents.common.fs_utils import save_markdown


# ------------------------------------------------------------------------------
# TODO[DAY2-A-01] 모델 선택
#  - LiteLlm(model="openai/gpt-4o-mini") 등 경량 모델 지정
# ------------------------------------------------------------------------------
MODEL = None  # 예: MODEL = LiteLlm(model="openai/gpt-4o-mini")


def _handle(query: str) -> Dict[str, Any]:
    """
    1) plan = Day2Plan()  (필요 시 top_k 등 파라미터 명시)
    2) agent = Day2Agent(index_dir=os.getenv("DAY2_INDEX_DIR","indices/day2"))
    3) return agent.handle(query, plan)
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY2-A-02] 구현 지침
    #  - plan = Day2Plan()
    #  - index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
    #  - agent = Day2Agent(index_dir=index_dir)
    #  - payload = agent.handle(query, plan); return payload
    # ----------------------------------------------------------------------------
    raise NotImplementedError("TODO[DAY2-A-02]: Day2 본체 호출")


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
    **kwargs,
) -> LlmResponse | None:
    """
    1) 사용자 메시지에서 query 텍스트 추출
    2) payload = _handle(query)
    3) body_md = render_day2(query, payload)
    4) saved = save_markdown(query, 'day2', body_md)
    5) md = render_enveloped('day2', query, payload, saved)
    6) LlmResponse로 반환 (예외 발생 시 간단 메시지)
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY2-A-03] 구현 지침
    #  - last = llm_request.contents[-1]
    #  - query = last.parts[0].text
    #  - payload → 렌더/저장/envelope → 응답
    # ----------------------------------------------------------------------------
    raise NotImplementedError("TODO[DAY2-A-03]: Day2 before_model_callback 구현")


day2_rag_agent = Agent(
    name="Day2RagAgent",
    model=MODEL,
    description="로컬 인덱스를 활용한 RAG 요약/근거 제공",
    instruction="사용자 질의와 관련된 문서를 인덱스에서 찾아 요약하고 근거를 함께 제시하라.",
    tools=[],
    before_model_callback=before_model_callback,
)
