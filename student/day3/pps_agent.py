# # -*- coding: utf-8 -*-
# """
# PPS 검색 에이전트
# - 실제 구현은 impl/pps_tool.py의 pps_search()에 모두 포함
# - FunctionTool.from_callable 사용
# """
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
너는 Day3PpsAgent로서 나라장터(G2B) 입찰·조달 공고를 검색하는 에이전트다. 한국어로 답하라.

[역할]
- 나라장터 입찰공고, 조달청 공고, G2B 용역/물품/공사 입찰, 사전규격, 공고번호 검색 등을 처리한다.
- 정부 지원사업/바우처/RFP는 Day3GovAgent가 담당하므로, 입찰·조달 관련 질의만 처리한다.

[입력]
- 사용자 메시지는 키워드(예: "VFX 용역", "AI 교육 입찰", "나라장터 콘텐츠", "조달청 사전규격") 위주다.
- 입찰, 조달, 나라장터, G2B, 용역, 물품, 공사, PQ, 사전규격, 공고번호 등의 키워드가 포함된 질의를 처리한다.

[동작]
1) **반드시 먼저 pps_search 도구를 호출해야 합니다.** 사용자 질의를 그대로 pps_search 함수의 query 인자로 전달하세요.
2) 도구는 한국어 Markdown을 반환합니다. 표에는 마감일/공고명/주관기관/예산/링크가 포함됩니다.
3) 도구의 마크다운 결과를 그대로 사용자에게 전달하세요. 불필요한 설명이나 문구를 덧붙이지 마세요.
4) 결과가 0건이거나 부족하면 사용자에게 알리고, 필요시 Day3GovAgent를 추가로 호출하도록 안내하세요.
5) **중요: 도구를 호출하지 않고 답변하면 안 됩니다. 항상 pps_search 도구를 먼저 호출하세요.**

[주의]
- 웹 뉴스/회사 동향 등 다른 범주의 정보는 섞지 않는다.
- 날짜는 KST 기준, 절대 날짜(YYYY-MM-DD)로 표기되는 마크다운을 유지한다.
- 정부 지원사업/바우처/RFP는 이 에이전트의 범위가 아니므로, 해당 키워드가 있으면 Day3GovAgent를 사용하도록 안내한다.
"""

day3_pps_agent = Agent(
    name="Day3PpsAgent",
    model=MODEL,
    description="나라장터(G2B) 입찰·조달 공고 검색 에이전트. pps_search 도구를 사용하여 나라장터 입찰공고를 검색합니다.",
    instruction=INSTRUCTION,
    tools=[pps_tool],
)



