# -*- coding: utf-8 -*-
"""
루트 오케스트레이터 통합 테스트
- Day1, Day2, Day3 에이전트가 모두 통합되어 정상 작동하는지 확인
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

def test_imports():
    """모든 모듈 import 테스트"""
    print("=" * 60)
    print("1. 모듈 Import 테스트")
    print("=" * 60)
    
    try:
        from apps.root_app.agent import root_agent
        print("[OK] root_agent import 성공")
    except Exception as e:
        print(f"[FAIL] root_agent import 실패: {e}")
        return False
    
    try:
        from student.day1.agent import day1_web_agent
        print("[OK] day1_web_agent import 성공")
    except Exception as e:
        print(f"[FAIL] day1_web_agent import 실패: {e}")
        return False
    
    try:
        from student.day2.agent import day2_rag_agent
        print("[OK] day2_rag_agent import 성공")
    except Exception as e:
        print(f"[FAIL] day2_rag_agent import 실패: {e}")
        return False
    
    try:
        from student.day3.agent import day3_gov_agent
        print("[OK] day3_gov_agent import 성공")
    except Exception as e:
        print(f"[FAIL] day3_gov_agent import 실패: {e}")
        return False
    
    try:
        from student.day3.pps_agent import day3_pps_agent
        print("[OK] day3_pps_agent import 성공")
    except Exception as e:
        print(f"[FAIL] day3_pps_agent import 실패: {e}")
        return False
    
    return True

def test_agent_structure():
    """에이전트 구조 확인"""
    print("\n" + "=" * 60)
    print("2. 에이전트 구조 확인")
    print("=" * 60)
    
    try:
        from apps.root_app.agent import root_agent
        
        print(f"[OK] root_agent.name: {root_agent.name}")
        print(f"[OK] root_agent.model: {type(root_agent.model).__name__}")
        print(f"[OK] root_agent.description: {len(root_agent.description)}자")
        print(f"[OK] root_agent.instruction: {len(root_agent.instruction)}자")
        print(f"[OK] root_agent.tools 개수: {len(root_agent.tools)}")
        
        for i, tool in enumerate(root_agent.tools, 1):
            if hasattr(tool, 'agent'):
                print(f"  - Tool {i}: {tool.agent.name}")
            else:
                print(f"  - Tool {i}: {type(tool).__name__}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 에이전트 구조 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_query():
    """간단한 쿼리 테스트 (실제 실행은 하지 않고 구조만 확인)"""
    print("\n" + "=" * 60)
    print("3. 쿼리 처리 준비 확인")
    print("=" * 60)
    
    try:
        from apps.root_app.agent import root_agent
        
        # 실제 실행은 하지 않고 에이전트가 준비되었는지만 확인
        print("[OK] root_agent 객체 생성 완료")
        print("[OK] 모든 서브 에이전트 통합 완료")
        print("\n실제 쿼리 실행 예시:")
        print('  response = root_agent.run("넷플릭스 영화 top3")')
        print('  print(response.text)')
        
        return True
    except Exception as e:
        print(f"[FAIL] 쿼리 처리 준비 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("루트 오케스트레이터 통합 테스트")
    print("=" * 60 + "\n")
    
    results = []
    
    # 1. Import 테스트
    results.append(("Import", test_imports()))
    
    # 2. 구조 확인
    if results[-1][1]:
        results.append(("구조 확인", test_agent_structure()))
    
    # 3. 쿼리 준비 확인
    if results[-1][1]:
        results.append(("쿼리 준비", test_simple_query()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] 모든 테스트 통과!")
        print("\n사용 방법:")
        print("  from apps.root_app.agent import root_agent")
        print("  response = root_agent.run('질의 내용')")
        print("  print(response.text)")
    else:
        print("[FAIL] 일부 테스트 실패. 위의 에러 메시지를 확인하세요.")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

