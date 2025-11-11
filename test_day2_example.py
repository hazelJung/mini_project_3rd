# -*- coding: utf-8 -*-
"""
Day2 에이전트 질문 예시
- Day2 RAG 에이전트에 직접 질문하는 방법을 보여줍니다.
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Any

def test_day2_direct():
    """Day2 에이전트를 직접 호출하여 테스트"""
    print("=" * 80)
    print("Day2 에이전트 직접 호출 테스트")
    print("=" * 80)
    print()
    
    # 방법 1: Day2Agent 직접 사용 (impl 레벨)
    try:
        from student.day2.impl.rag import Day2Agent
        from student.common.schemas import Day2Plan
        
        # 질의 예시
        query = "인공지능 규제"
        
        print(f"[질의] {query}")
        print("-" * 80)
        
        # Plan 설정
        plan = Day2Plan(
            top_k=5,  # 상위 5개 문서 검색
            score_threshold=0.35,  # 최소 유사도 임계값
        )
        
        # 인덱스 경로
        index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
        
        # 에이전트 생성 및 실행
        agent = Day2Agent(index_dir=index_dir)
        payload = agent.handle(query, plan)
        
        # 결과 출력
        print(f"[결과 타입] {payload.get('type')}")
        print(f"[컨텍스트 개수] {len(payload.get('contexts', []))}")
        print(f"[게이팅 상태] {payload.get('gating', {}).get('status')}")
        print()
        
        # 컨텍스트 요약
        contexts = payload.get('contexts', [])
        if contexts:
            print("[검색된 문서들]")
            for i, ctx in enumerate(contexts[:3], 1):  # 상위 3개만
                score = ctx.get('score', 0)
                text = ctx.get('text', '')[:100]  # 처음 100자만
                print(f"  {i}. (유사도: {score:.3f}) {text}...")
        print()
        
        # 답변 출력
        if payload.get('answer'):
            print("[생성된 답변]")
            print(payload['answer'])
        else:
            print("[알림] 답변이 생성되지 않았습니다. (게이팅 설정 확인)")
        
        return True
        
    except Exception as e:
        print(f"[오류] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_day2_agent():
    """Day2 ADK Agent를 사용하여 테스트 (웹 서버와 유사한 방식)"""
    print()
    print("=" * 80)
    print("Day2 ADK Agent 테스트 (웹 서버 방식)")
    print("=" * 80)
    print()
    
    try:
        from student.day2.agent import day2_rag_agent
        from google.genai import types
        from google.adk.models.llm_request import LlmRequest
        
        # 질의 예시
        query = "의료 AI 규제"
        
        print(f"[질의] {query}")
        print("-" * 80)
        
        # LlmRequest 생성 (웹 서버가 생성하는 것과 유사)
        llm_request = LlmRequest(
            contents=[
                types.Content(
                    parts=[types.Part(text=query)],
                    role="user"
                )
            ]
        )
        
        # CallbackContext 생성 (간단한 버전)
        from google.adk.agents.callback_context import CallbackContext
        callback_context = CallbackContext()
        
        # before_model_callback 호출
        response = day2_rag_agent.before_model_callback(
            callback_context=callback_context,
            llm_request=llm_request
        )
        
        if response:
            print("[응답]")
            print(response.text[:500] if hasattr(response, 'text') else str(response)[:500])
            print("...")
        else:
            print("[알림] 응답이 생성되지 않았습니다.")
        
        return True
        
    except Exception as e:
        print(f"[오류] {e}")
        import traceback
        traceback.print_exc()
        return False


def show_example_queries():
    """Day2에 적합한 질의 예시들"""
    print()
    print("=" * 80)
    print("Day2에 적합한 질의 예시")
    print("=" * 80)
    print()
    
    examples = [
        "인공지능 규제",
        "의료 AI 관련 법규",
        "OTT 서비스 규제",
        "데이터 프라이버시",
        "넷플릭스 한국 영화 TOP10",
        "AI 교육 바우처",
        "개인정보보호법",
        "의료기기 규제",
    ]
    
    print("문서 검색/요약에 적합한 질의:")
    for i, example in enumerate(examples, 1):
        print(f"  {i}. {example}")
    
    print()
    print("참고:")
    print("  - Day2는 로컬 인덱스(indices/day2)에 있는 문서를 검색합니다.")
    print("  - 문서가 인덱스에 있어야 검색 결과를 얻을 수 있습니다.")
    print("  - 질의는 자연어로 작성하면 됩니다.")


def main():
    """메인 함수"""
    # 예시 질의 출력
    show_example_queries()
    
    print()
    print("=" * 80)
    print("테스트 실행")
    print("=" * 80)
    print()
    
    # 방법 1: 직접 호출
    print("[방법 1] Day2Agent 직접 호출")
    success1 = test_day2_direct()
    
    # 방법 2: ADK Agent 사용
    print()
    print("[방법 2] Day2 ADK Agent 사용 (웹 서버 방식)")
    success2 = test_day2_agent()
    
    print()
    print("=" * 80)
    if success1 or success2:
        print("[완료] 테스트 완료")
    else:
        print("[경고] 일부 테스트가 실패했습니다.")
    print("=" * 80)
    print()
    print("웹 서버에서 테스트하려면:")
    print("  1. adk web apps 실행")
    print("  2. 브라우저에서 http://127.0.0.1:8000 접속")
    print("  3. 오케스트레이터에 질의 (예: '인공지능 규제 문서 요약해줘')")
    print("  4. 오케스트레이터가 Day2 에이전트를 자동으로 호출합니다.")


if __name__ == "__main__":
    main()

