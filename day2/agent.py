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

from .impl.rag import Day2Agent
from ..common.writer import render_day2, render_enveloped
from ..common.schemas import Day2Plan
from ..common.fs_utils import save_markdown


# ------------------------------------------------------------------------------
# TODO[DAY2-A-01] 모델 선택
#  - LiteLlm(model="openai/gpt-4o-mini") 등 경량 모델 지정
# ------------------------------------------------------------------------------
MODEL = LiteLlm(model="openai/gpt-4o-mini")  # 예: MODEL = LiteLlm(model="openai/gpt-4o-mini")


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
    plan = Day2Plan()  # 필요 시 Day2Plan(top_k=5, score_threshold=0.35, ...) 등으로 조정
    index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
    agent = Day2Agent(index_dir=index_dir)

    payload: Dict[str, Any] = agent.handle(query, plan)
    return payload


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
    try:
        # 1) 사용자 메시지에서 query 텍스트 추출
        last = llm_request.contents[-1]
        query: str = last.parts[0].text if last and last.parts else ""

        if not query:
            # query가 비어있으면 LLM 호출을 진행하지 않음
            return LlmResponse(text="[DAY2] 질의가 비어있습니다. 검색 키워드를 입력해주세요.")

        # 2) Day2 파이프라인 실행
        payload: Dict[str, Any] = _handle(query)

        # 3) 본문 마크다운 렌더링
        body_md: str = render_day2(query, payload)

        # 4) 마크다운 저장
        saved: Dict[str, Any] = save_markdown(query, "day2", body_md)

        # 5) envelope 형식으로 최종 문서 렌더링
        md: str = render_enveloped("day2", query, payload, saved)

        # 6) LlmResponse로 반환
        return LlmResponse(text=md)

    except Exception as e:
        # 필요 시 로깅
        # logger.exception("before_model_callback failed", exc_info=e)
        return LlmResponse(text=f"[DAY2] 처리 중 오류가 발생했습니다: {e}")


day2_rag_agent = Agent(
    name="Day2RagAgent",
    model=MODEL,
    description="로컬 인덱스를 활용한 RAG 요약/근거 제공",
    instruction="사용자 질의와 관련된 문서를 인덱스에서 찾아 요약하고 근거를 함께 제시하라.",
    tools=[],
    before_model_callback=before_model_callback,
)
