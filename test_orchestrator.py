# -*- coding: utf-8 -*-
"""
오케스트레이터 및 서브 에이전트 검증 테스트
- 각 day의 agent가 제대로 import되고 초기화되는지 확인
- 오케스트레이터가 모든 agent를 도구로 등록하는지 확인

사용법:
    가상환경을 활성화한 후 실행:
    - Windows: .venv\Scripts\activate
    - Linux/Mac: source .venv/bin/activate
    - python test_orchestrator.py
"""

from __future__ import annotations
import sys
import os
from typing import List, Tuple

def check_environment() -> Tuple[bool, str]:
    """환경 확인 (가상환경, 모듈 등)"""
    issues = []
    
    # google.adk 모듈 확인
    try:
        import google.adk
    except ImportError:
        issues.append("google.adk 모듈을 찾을 수 없습니다. 가상환경이 활성화되었는지 확인하세요.")
    
    # 가상환경 경로 확인
    venv_path = os.path.join(os.path.dirname(__file__), ".venv")
    if os.path.exists(venv_path):
        if sys.prefix == sys.base_prefix:
            issues.append("가상환경이 활성화되지 않은 것 같습니다. .venv를 활성화하세요.")
    else:
        issues.append(".venv 디렉토리를 찾을 수 없습니다.")
    
    if issues:
        return False, "\n".join(issues)
    return True, "환경 확인 완료"

def test_agent_imports() -> List[Tuple[str, bool, str]]:
    """각 day의 agent import 테스트"""
    results = []
    
    # Day1 Agent
    try:
        from student.day1.agent import day1_web_agent
        from google.adk.agents import Agent
        assert isinstance(day1_web_agent, Agent), "day1_web_agent는 Agent 인스턴스여야 함"
        assert day1_web_agent.name == "Day1WebAgent", f"day1_web_agent.name이 예상과 다름: {day1_web_agent.name}"
        results.append(("Day1 Web Agent", True, f"[OK] 이름: {day1_web_agent.name}, 설명: {day1_web_agent.description[:50]}..."))
    except Exception as e:
        results.append(("Day1 Web Agent", False, f"[FAIL] Import 실패: {e}"))
    
    # Day2 Agent
    try:
        from student.day2.agent import day2_rag_agent
        assert isinstance(day2_rag_agent, Agent), "day2_rag_agent는 Agent 인스턴스여야 함"
        assert day2_rag_agent.name == "Day2RagAgent", f"day2_rag_agent.name이 예상과 다름: {day2_rag_agent.name}"
        results.append(("Day2 RAG Agent", True, f"[OK] 이름: {day2_rag_agent.name}, 설명: {day2_rag_agent.description[:50]}..."))
    except Exception as e:
        results.append(("Day2 RAG Agent", False, f"[FAIL] Import 실패: {e}"))
    
    # Day3 Gov Agent
    try:
        from student.day3.agent import day3_gov_agent
        assert isinstance(day3_gov_agent, Agent), "day3_gov_agent는 Agent 인스턴스여야 함"
        assert day3_gov_agent.name == "Day3GovAgent", f"day3_gov_agent.name이 예상과 다름: {day3_gov_agent.name}"
        results.append(("Day3 Gov Agent", True, f"[OK] 이름: {day3_gov_agent.name}, 설명: {day3_gov_agent.description[:50]}..."))
    except Exception as e:
        results.append(("Day3 Gov Agent", False, f"[FAIL] Import 실패: {e}"))
    
    # Day3 PPS Agent (선택적)
    try:
        from student.day3.pps_agent import day3_pps_agent
        assert isinstance(day3_pps_agent, Agent), "day3_pps_agent는 Agent 인스턴스여야 함"
        assert day3_pps_agent.name == "Day3PpsAgent", f"day3_pps_agent.name이 예상과 다름: {day3_pps_agent.name}"
        results.append(("Day3 PPS Agent", True, f"[OK] 이름: {day3_pps_agent.name}"))
    except Exception as e:
        results.append(("Day3 PPS Agent", False, f"[WARN] Import 실패 (선택적): {e}"))
    
    return results


def test_orchestrator() -> Tuple[bool, str]:
    """오케스트레이터 구성 테스트"""
    try:
        from apps.root_app.agent import root_agent
        from google.adk.agents import Agent
        from google.adk.tools.agent_tool import AgentTool
        
        # 오케스트레이터가 Agent 인스턴스인지 확인
        assert isinstance(root_agent, Agent), "root_agent는 Agent 인스턴스여야 함"
        
        # 이름 확인
        assert root_agent.name == "KT_AIVLE_Orchestrator", f"root_agent.name이 예상과 다름: {root_agent.name}"
        
        # description과 instruction이 None이 아닌지 확인
        assert root_agent.description is not None and root_agent.description.strip() != "", \
            "root_agent.description이 비어있음"
        assert root_agent.instruction is not None and root_agent.instruction.strip() != "", \
            "root_agent.instruction이 비어있음"
        
        # 도구 확인
        assert len(root_agent.tools) > 0, "root_agent.tools가 비어있음"
        
        # 각 도구가 AgentTool인지 확인
        tool_names = []
        for tool in root_agent.tools:
            assert isinstance(tool, AgentTool), f"도구가 AgentTool 인스턴스가 아님: {type(tool)}"
            if hasattr(tool, 'agent') and hasattr(tool.agent, 'name'):
                tool_names.append(tool.agent.name)
        
        return True, f"[OK] 오케스트레이터 구성 성공\n  - 이름: {root_agent.name}\n  - 도구 개수: {len(root_agent.tools)}\n  - 등록된 도구: {', '.join(tool_names)}\n  - 설명 길이: {len(root_agent.description)}자\n  - 지시 길이: {len(root_agent.instruction)}자"
    
    except Exception as e:
        import traceback
        return False, f"[FAIL] 오케스트레이터 구성 실패: {e}\n{traceback.format_exc()}"


def test_prompt_imports() -> Tuple[bool, str]:
    """프롬프트 import 테스트"""
    try:
        from apps.root_app.prompt import ORCHESTRATOR_DESC, ORCHESTRATOR_PROMPT
        
        assert ORCHESTRATOR_DESC is not None and ORCHESTRATOR_DESC.strip() != "", \
            "ORCHESTRATOR_DESC가 비어있음"
        assert ORCHESTRATOR_PROMPT is not None and ORCHESTRATOR_PROMPT.strip() != "", \
            "ORCHESTRATOR_PROMPT가 비어있음"
        
        return True, f"[OK] 프롬프트 로드 성공\n  - 설명 길이: {len(ORCHESTRATOR_DESC)}자\n  - 지시 길이: {len(ORCHESTRATOR_PROMPT)}자"
    
    except Exception as e:
        return False, f"[FAIL] 프롬프트 로드 실패: {e}"


def main() -> int:
    """메인 테스트 실행"""
    print("=" * 80)
    print("오케스트레이터 및 서브 에이전트 검증 테스트")
    print("=" * 80)
    print()
    
    # 0. 환경 확인
    print("[0] 환경 확인")
    print("-" * 80)
    env_ok, env_msg = check_environment()
    if not env_ok:
        print(f"[WARN] {env_msg}")
        print()
        print("해결 방법:")
        print("1. 가상환경 활성화:")
        print("   - Windows: .venv\\Scripts\\activate")
        print("   - Linux/Mac: source .venv/bin/activate")
        print("2. 또는 uv를 사용하는 경우: uv run python test_orchestrator.py")
        print()
        print("참고: 실제 웹 서버 실행 시 'adk web apps' 명령은 환경을 자동으로 처리합니다.")
        print("      이 테스트는 개발 중 구성 확인용입니다.")
        print()
        # 환경 문제가 있어도 계속 진행 (프롬프트는 확인 가능)
    else:
        print(f"[OK] {env_msg}")
    print()
    
    # 1. 프롬프트 테스트
    print("[1] 프롬프트 로드 테스트")
    print("-" * 80)
    success, msg = test_prompt_imports()
    print(msg)
    print()
    
    if not success:
        print("[ERROR] 프롬프트 로드 실패로 인해 테스트 중단")
        return 1
    
    # 2. 서브 에이전트 import 테스트
    print("[2] 서브 에이전트 Import 테스트")
    print("-" * 80)
    agent_results = test_agent_imports()
    for name, success, msg in agent_results:
        print(f"  {name}: {msg}")
    print()
    
    # 실패한 에이전트가 있는지 확인
    failed_agents = [name for name, success, _ in agent_results if not success and "선택적" not in _ and "WARN" not in _]
    if failed_agents:
        print(f"[ERROR] 필수 에이전트 import 실패: {', '.join(failed_agents)}")
        return 2
    
    # 3. 오케스트레이터 구성 테스트
    print("[3] 오케스트레이터 구성 테스트")
    print("-" * 80)
    success, msg = test_orchestrator()
    print(msg)
    print()
    
    if not success:
        print("[ERROR] 오케스트레이터 구성 실패")
        return 3
    
    # 4. 최종 결과
    print("=" * 80)
    print("[SUCCESS] 모든 테스트 통과!")
    print("=" * 80)
    print()
    print("오케스트레이터가 정상적으로 구성되었습니다.")
    print("이제 'adk web apps' 명령으로 웹 서버를 실행할 수 있습니다.")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

