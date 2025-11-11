# 영화 투자사 Agent 시스템 실행 가이드

ADK(Agent Development Kit)를 사용한 오케스트레이터 실행 방법입니다.

## 빠른 시작

### 1. 환경 변수 설정

`.env` 파일에 다음 키를 설정하세요:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
```

### 2. 실행 방법

#### 방법 1: 간단한 스크립트로 실행 (권장)

```bash
# 단일 질의 실행
python run_agent_simple.py "강형철 감독 경력 및 작품 이력 조회"

# 대화형 모드
python run_agent.py --interactive
```

#### 방법 2: ADK 웹 서버로 실행

```bash
# ADK 웹 서버 시작
adk web apps

# 브라우저에서 http://localhost:8000 접속
# 오케스트레이터에 질의 입력
```

#### 방법 3: Python 코드에서 직접 실행

```python
from apps.root_app.agent import root_agent

# 질의 실행
response = root_agent.run("강형철 감독 경력 및 작품 이력 조회")
print(response.text)
```

## 실행 스크립트 설명

### `run_agent_simple.py`
- 가장 간단한 실행 방법
- 질의를 인자로 받거나 입력받아 실행
- 빠른 테스트에 적합

**사용법:**
```bash
python run_agent_simple.py "질의 내용"
```

### `run_agent.py`
- 더 많은 옵션을 제공하는 실행 스크립트
- 대화형 모드, 웹 서버 모드 지원

**사용법:**
```bash
# 단일 질의 실행
python run_agent.py "강형철 감독 경력 및 작품 이력 조회"

# 대화형 모드
python run_agent.py --interactive
python run_agent.py -i

# 웹 서버 모드 (ADK CLI 사용)
python run_agent.py --server
python run_agent.py -s
```

## 질의 예시

### Day1 (웹 검색, 리스크, 트렌드)
```
"배우 이름"              # 배우 리스크 검색
"넷플릭스 트렌드"        # OTT 트렌드 분석
"디즈니플러스 검색량"    # 검색량 트렌드
"삼성전자 최근 뉴스"     # 웹 검색
```

### Day2 (로컬 RAG, 넷플릭스, 감독)
```
"강형철 감독 경력 및 작품 이력 조회"  # 감독 랭킹 조회
"넷플릭스 한국 영화 TOP10"            # 넷플릭스 TOP 리스트
"인공지능 규제 문서 요약"             # 로컬 RAG 검색
"OTT 규제 문서 검색"                  # 로컬 RAG 검색
```

### Day3 (영상/미디어 기술 정부 공고)
```
"영상 AI 기술 지원사업"      # 영상/미디어 기술 정부 공고
"VR 콘텐츠 제작 바우처"      # VR/AR 관련 공고
"미디어 스트리밍 기술"        # 스트리밍 기술 관련 공고
```

## 오케스트레이터 자동 라우팅

오케스트레이터가 자동으로 적절한 에이전트를 선택합니다:

- **배우 이름, 리스크, 논란, 이슈** → Day1
- **OTT 트렌드, 검색량** → Day1
- **넷플릭스 TOP 리스트, 감독 랭킹** → Day2
- **문서 요약, 근거 찾기** → Day2
- **영상/미디어 기술 정부 공고** → Day3

## 문제 해결

### 환경 변수 오류
```
[경고] OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.
```
**해결:** `.env` 파일에 API 키를 설정하거나 환경 변수로 설정하세요.

### 모듈 import 오류
```
ModuleNotFoundError: No module named 'google.adk'
```
**해결:** 가상환경을 활성화하고 의존성을 설치하세요:
```bash
# uv 사용하는 경우
uv sync

# pip 사용하는 경우
pip install -r requirements.txt
```

### ADK CLI 오류
```
[안내] ADK CLI가 설치되어 있지 않습니다.
```
**해결:** `run_agent.py --interactive` 또는 `run_agent_simple.py`를 사용하세요.

## 추가 정보

- 오케스트레이터: `apps/root_app/agent.py`
- Day1 에이전트: `student/day1/agent.py`
- Day2 에이전트: `student/day2/agent.py`
- Day3 에이전트: `student/day3/agent.py`

