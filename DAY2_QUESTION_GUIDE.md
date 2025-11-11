# Day2 에이전트 질문 가이드

Day2 RAG 에이전트에 질문하는 방법과 예시를 안내합니다.

## Day2 에이전트란?

Day2는 **RAG (Retrieval-Augmented Generation)** 에이전트로, 로컬 인덱스에 저장된 문서를 검색하여 질의에 대한 답변을 제공합니다.

- **기능**: 문서 검색, 요약, 근거 제시
- **데이터 소스**: `indices/day2` 디렉토리의 FAISS 인덱스
- **용도**: 문서 요약, 근거 찾기, 첨부 자료 검색

## 질문 방법

### 방법 1: 웹 서버를 통한 질문 (권장)

가장 간단한 방법은 웹 서버를 실행하고 오케스트레이터를 통해 질문하는 것입니다.

```bash
# 1. 웹 서버 실행
adk web apps

# 2. 브라우저에서 http://127.0.0.1:8000 접속

# 3. 질문 입력
```

#### 질문 예시

**Day2를 직접 호출하려면:**
- "문서 요약해줘" 같은 키워드 포함
- "근거 찾아줘"
- "관련 문서 검색"

**오케스트레이터가 자동으로 Day2를 선택하는 경우:**
```
질의: "인공지능 규제 관련 문서 요약해줘"
→ 오케스트레이터가 Day2 에이전트를 호출
```

### 방법 2: 코드로 직접 테스트

테스트 스크립트를 실행하여 Day2 에이전트를 직접 테스트할 수 있습니다.

```bash
python test_day2_example.py
```

또는 Python 코드에서 직접 호출:

```python
from student.day2.impl.rag import Day2Agent
from student.common.schemas import Day2Plan
import os

# 질의
query = "인공지능 규제"

# Plan 설정
plan = Day2Plan(
    top_k=5,  # 상위 5개 문서 검색
    score_threshold=0.35,  # 최소 유사도 임계값
)

# 에이전트 생성 및 실행
index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
agent = Day2Agent(index_dir=index_dir)
payload = agent.handle(query, plan)

# 결과 확인
print(f"검색된 문서 개수: {len(payload.get('contexts', []))}")
print(f"답변: {payload.get('answer', '')}")
```

### 방법 3: ADK Agent 사용 (웹 서버 방식)

웹 서버와 동일한 방식으로 테스트:

```python
from student.day2.agent import day2_rag_agent
from google.genai import types
from google.adk.models.llm_request import LlmRequest
from google.adk.agents.callback_context import CallbackContext

# 질의
query = "의료 AI 규제"

# LlmRequest 생성
llm_request = LlmRequest(
    contents=[
        types.Content(
            parts=[types.Part(text=query)],
            role="user"
        )
    ]
)

# CallbackContext 생성
callback_context = CallbackContext()

# before_model_callback 호출
response = day2_rag_agent.before_model_callback(
    callback_context=callback_context,
    llm_request=llm_request
)

# 응답 확인
if response:
    print(response.text)
```

## 좋은 질문 예시

Day2에 적합한 질의는 다음과 같습니다:

### 문서 검색/요약
- ✅ "인공지능 규제 관련 문서 요약해줘"
- ✅ "의료 AI 관련 법규 찾아줘"
- ✅ "OTT 서비스 규제 문서 검색"
- ✅ "데이터 프라이버시 관련 자료"

### 근거 찾기
- ✅ "넷플릭스 한국 영화 TOP10 근거"
- ✅ "AI 교육 바우처 관련 문서"
- ✅ "개인정보보호법 관련 내용"

### 특정 주제 검색
- ✅ "의료기기 규제"
- ✅ "AI 윤리 가이드라인"
- ✅ "데이터 보호 규정"

## 피해야 할 질문

Day2는 문서 검색에 특화되어 있으므로, 다음 유형의 질의는 다른 에이전트가 더 적합합니다:

- ❌ "삼성전자 최근 뉴스" → Day1 (웹 검색)
- ❌ "정부 공고 찾아줘" → Day3 (정부 공고)
- ❌ "오늘 날씨" → Day1 (웹 검색)

## 오케스트레이터를 통한 자동 라우팅

오케스트레이터는 질의를 분석하여 적절한 에이전트를 자동으로 선택합니다:

```
질의: "인공지능 규제 문서 요약해줘"
→ 오케스트레이터 분석: "문서 요약" 키워드 발견
→ Day2 에이전트 호출

질의: "최근 AI 뉴스와 관련 문서 모두 찾아줘"
→ 오케스트레이터 분석: "뉴스" + "문서" 키워드
→ Day1 (웹) + Day2 (RAG) 순차 호출
```

## 문제 해결

### 검색 결과가 없을 때

**원인**: 인덱스에 관련 문서가 없거나, 질의가 너무 구체적일 수 있습니다.

**해결**:
1. 인덱스 확인: `indices/day2/docs.jsonl` 파일 확인
2. 질의 변경: 더 일반적인 키워드로 시도
3. 인덱스 재구성: 새로운 문서를 인덱스에 추가

### 응답이 느릴 때

**원인**: 인덱스 크기나 검색 파라미터 설정

**해결**:
1. `top_k` 값 줄이기 (기본값: 5)
2. `score_threshold` 높이기 (더 관련성 높은 문서만)

### 오류 발생 시

```python
# 환경 변수 확인
import os
index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
print(f"인덱스 경로: {index_dir}")

# 인덱스 파일 존재 확인
import pathlib
index_path = pathlib.Path(index_dir)
print(f"FAISS 인덱스: {index_path / 'faiss.index'}")
print(f"문서 파일: {index_path / 'docs.jsonl'}")
```

## 참고 자료

- Day2 에이전트: `student/day2/agent.py`
- RAG 구현: `student/day2/impl/rag.py`
- 테스트 스크립트: `test_day2_example.py`
- 인덱스 디렉토리: `indices/day2/`

## 다음 단계

1. 웹 서버에서 실제 질의 테스트
2. 검색 결과 품질 확인
3. 필요시 인덱스에 문서 추가
4. 질의 프롬프트 튜닝

