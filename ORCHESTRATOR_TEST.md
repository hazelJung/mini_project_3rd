# 오케스트레이터 테스트 가이드

오케스트레이터와 각 Day별 에이전트가 잘 연결되어 작동하는지 확인하는 방법입니다.

## 1. 빠른 구성 확인 (코드 레벨)

테스트 스크립트를 실행하여 각 에이전트가 제대로 import되고 오케스트레이터가 구성되었는지 확인:

```bash
# 가상환경 활성화 후
python test_orchestrator.py
```

이 스크립트는 다음을 확인합니다:
- ✅ 프롬프트 로드 (ORCHESTRATOR_DESC, ORCHESTRATOR_PROMPT)
- ✅ 각 Day 에이전트 import (Day1, Day2, Day3)
- ✅ 오케스트레이터 구성 (도구 등록, 메타데이터)

## 2. 실제 실행 테스트 (웹 서버)

가장 확실한 방법은 웹 서버를 실행하고 실제로 질의를 보내는 것입니다:

```bash
# 웹 서버 실행
adk web apps

# 브라우저에서 http://127.0.0.1:8000 접속
```

### 테스트 시나리오

#### Day1 (웹 검색) 테스트
```
질의: "삼성전자 최근 뉴스"
예상: Day1 에이전트가 웹 검색 결과를 반환
```

#### Day2 (RAG) 테스트
```
질의: "인공지능 규제 관련 문서 요약"
예상: Day2 에이전트가 로컬 인덱스에서 관련 문서를 검색하여 요약
```

#### Day3 (정부 공고) 테스트
```
질의: "AI 교육 바우처 공고"
예상: Day3 에이전트가 정부 공고를 검색하여 표로 제공
```

#### 오케스트레이터 라우팅 테스트
```
질의: "최근 넷플릭스 동향과 관련 문서 찾아줘"
예상: 오케스트레이터가 Day1(웹)과 Day2(RAG)를 모두 호출
```

## 3. 구성 확인 체크리스트

### 오케스트레이터 (`apps/root_app/agent.py`)
- [x] `ORCHESTRATOR_DESC`가 설정되어 있음
- [x] `ORCHESTRATOR_PROMPT`가 설정되어 있음
- [x] `root_agent`에 Day1, Day2, Day3 에이전트가 도구로 등록됨
- [x] 모델이 설정됨 (`LiteLlm`)

### Day1 에이전트 (`student/day1/agent.py`)
- [x] `day1_web_agent`가 정의되어 있음
- [x] `before_model_callback`이 구현되어 있음
- [x] 모델이 설정되어 있음

### Day2 에이전트 (`student/day2/agent.py`)
- [x] `day2_rag_agent`가 정의되어 있음
- [x] `before_model_callback`이 구현되어 있음
- [x] 모델이 설정되어 있음
- [x] 인덱스 경로가 설정되어 있음 (`indices/day2`)

### Day3 에이전트 (`student/day3/agent.py`)
- [x] `day3_gov_agent`가 정의되어 있음
- [x] `before_model_callback`이 구현되어 있음
- [x] 모델이 설정되어 있음

## 4. 문제 해결

### Import 오류
```
No module named 'google'
```
**해결**: 가상환경을 활성화하세요.
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 프롬프트 오류
```
ValidationError: description/instruction이 None
```
**해결**: `apps/root_app/prompt.py`에서 `ORCHESTRATOR_DESC`와 `ORCHESTRATOR_PROMPT`를 설정하세요.

### 에이전트를 찾을 수 없음
```
ImportError: cannot import name 'day1_web_agent'
```
**해결**: 각 day의 `agent.py` 파일에서 에이전트가 올바르게 정의되어 있는지 확인하세요.

## 5. 다음 단계

구성이 확인되면:
1. 웹 서버에서 실제 질의를 테스트
2. 각 에이전트의 응답 품질 확인
3. 오케스트레이터의 라우팅 로직이 올바르게 작동하는지 확인
4. 필요시 프롬프트 튜닝

## 참고

- 테스트 스크립트: `test_orchestrator.py`
- 오케스트레이터: `apps/root_app/agent.py`
- 프롬프트: `apps/root_app/prompt.py`
- 각 Day 에이전트: `student/day{1,2,3}/agent.py`

