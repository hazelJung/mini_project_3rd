# -*- coding: utf-8 -*-
"""
PPS 검색 에이전트
- 실제 구현은 impl/pps_tool.py의 pps_search()에 모두 포함
- FunctionTool.from_callable 사용
"""
from __future__ import annotations
import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.function_tool import FunctionTool
from student.day3.impl.pps_tool import pps_search 

MODEL = LiteLlm(model=os.getenv("DAY4_INTENT_MODEL","gpt-4o-mini"))

# FunctionTool — 필수 인자만!
pps_tool = FunctionTool(func=pps_search)

INSTRUCTION = """\
너는 Day3PpsAgent로서 '나라장터 용역 공고' 질의만 처리한다. 한국어로 답하라.

[입력]
- 사용자 메시지는 키워드(예: "인공지능", "AI 교육") 위주다.

[동작]
1) 반드시 도구(pps_search)를 1회 호출하여 결과를 받는다. (서버사이드 키워드 검색)
2) 도구는 한국어 Markdown을 반환한다. 표에는 마감일/공고명/주관기관/예산/링크가 포함된다.
3) 도구의 마크다운을 그대로 전달하되, 불필요한 문구를 덧붙이지 않는다.

[주의]
- 웹 뉴스/회사 동향 등 다른 범주의 정보는 섞지 않는다.
- 날짜는 KST 기준, 절대 날짜(YYYY-MM-DD)로 표기되는 마크다운을 유지한다.
"""

day3_pps_agent = Agent(
    name="Day3PpsAgent",
    model=MODEL,
    instruction="키워드를 받으면 나라장터(OpenAPI)에서 최근 공고를 표로 만들고 저장하라.",
    tools=[pps_tool],
)
