# -*- coding: utf-8 -*-
"""
Day2 에이전트 빠른 사용 예시
- 가장 간단한 방법으로 Day2에 질문하는 예시
"""

# ============================================================================
# 예시 1: 웹 서버를 통한 질문 (가장 쉬운 방법)
# ============================================================================
"""
1. 터미널에서 웹 서버 실행:
   adk web apps

2. 브라우저에서 http://127.0.0.1:8000 접속

3. 다음 질의 중 하나 입력:
   - "인공지능 규제 문서 요약해줘"
   - "의료 AI 관련 법규 찾아줘"
   - "OTT 서비스 규제 관련 문서 검색"
   - "데이터 프라이버시 관련 자료"

4. 오케스트레이터가 자동으로 Day2 에이전트를 호출합니다.
"""

# ============================================================================
# 예시 2: 코드로 직접 호출 (테스트용)
# ============================================================================
def example_direct_call():
    """Day2Agent를 직접 호출하는 예시"""
    from student.day2.impl.rag import Day2Agent
    from student.common.schemas import Day2Plan
    import os
    
    # 질의
    query = "인공지능 규제"
    
    # 설정
    plan = Day2Plan(top_k=5)
    index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
    
    # 실행
    agent = Day2Agent(index_dir=index_dir)
    payload = agent.handle(query, plan)
    
    # 결과
    print(f"검색된 문서: {len(payload.get('contexts', []))}개")
    if payload.get('answer'):
        print(payload['answer'])


# ============================================================================
# 예시 3: ADK Agent 사용 (웹 서버와 동일한 방식)
# ============================================================================
def example_adk_agent():
    """ADK Agent를 사용하는 예시"""
    from student.day2.agent import day2_rag_agent
    from google.genai import types
    from google.adk.models.llm_request import LlmRequest
    from google.adk.agents.callback_context import CallbackContext
    
    # 질의
    query = "의료 AI 규제"
    
    # 요청 생성
    llm_request = LlmRequest(
        contents=[
            types.Content(
                parts=[types.Part(text=query)],
                role="user"
            )
        ]
    )
    
    # 콜백 호출
    callback_context = CallbackContext()
    response = day2_rag_agent.before_model_callback(
        callback_context=callback_context,
        llm_request=llm_request
    )
    
    # 응답
    if response and hasattr(response, 'text'):
        print(response.text)


# ============================================================================
# 실행 예시
# ============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("Day2 에이전트 질문 예시")
    print("=" * 80)
    print()
    print("가장 쉬운 방법: 웹 서버를 통한 질문")
    print("  1. adk web apps 실행")
    print("  2. 브라우저에서 http://127.0.0.1:8000 접속")
    print("  3. 질의 입력: '인공지능 규제 문서 요약해줘'")
    print()
    print("코드로 테스트:")
    print("  python test_day2_example.py")
    print()
    print("좋은 질문 예시:")
    print("  - '인공지능 규제 관련 문서 요약해줘'")
    print("  - '의료 AI 관련 법규 찾아줘'")
    print("  - 'OTT 서비스 규제 문서 검색'")
    print("  - '데이터 프라이버시 관련 자료'")
    print()

