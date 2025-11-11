# 감독 조회 기능 가이드

Day2 에이전트에서 감독 이름으로 rank1_count (1위 횟수)를 조회하는 기능입니다.

## 기능 개요

- **데이터 소스**: `data/raw/director_ranking.csv`
- **기능**: 감독 이름을 입력하면 해당 감독의 1위 횟수(rank1_count) 반환
- **작동 방식**: 질의에서 감독 이름을 추출하여 CSV 파일에서 조회

## 사용 방법

### 웹 서버를 통한 질의

```bash
# 웹 서버 실행
adk web apps

# 브라우저에서 http://127.0.0.1:8000 접속
```

**질의 예시:**
- "봉준호 감독 1위 횟수"
- "김한민 감독"
- "최동훈 감독 랭킹"
- "브래드 버드 감독"

### 코드로 직접 테스트

```python
from student.day2.agent import _load_director_csv, _find_director_in_query

# CSV 로드
csv_path = "data/raw/director_ranking.csv"
director_map = _load_director_csv(csv_path)

# 감독 찾기
query = "봉준호 감독"
result = _find_director_in_query(query, director_map)
if result:
    director, count = result
    print(f"{director}: {count}회")
```

## 데이터 소스

### 기존 CSV 파일 (`data/raw/director_ranking.csv`)

현재 126개 감독 정보가 포함되어 있습니다.

**CSV 형식:**
```csv
,director,rank1_count
18,김한민,48
80,장재현,48
97,최동훈,39
...
```

### KOBIS에서 새로 수집하기 (선택사항)

기존 CSV 파일이 작동하지 않거나 새로운 데이터가 필요한 경우:

```bash
# KOBIS에서 감독 정보 수집
python student/day2/impl/scrape_kobis_directors.py \
    --input_csv data/raw/director_ranking.csv \
    --output_csv data/raw/director_ranking_kobis.csv \
    --limit 10  # 테스트용으로 10개만

# 또는 특정 감독만 수집
python student/day2/impl/scrape_kobis_directors.py \
    --directors "봉준호" "김한민" "최동훈" \
    --output_csv data/raw/director_ranking_kobis.csv
```

**주의사항:**
- KOBIS 스크래핑은 시간이 오래 걸릴 수 있습니다
- 웹 사이트 구조 변경 시 스크립트 수정이 필요할 수 있습니다
- 요청 간 딜레이를 두어 서버 부하를 줄입니다

## 문제 해결

### CSV 파일을 찾을 수 없는 경우

```python
# CSV 경로 확인
import os
csv_path = os.path.join("data", "raw", "director_ranking.csv")
print(f"CSV 경로: {os.path.abspath(csv_path)}")
print(f"파일 존재: {os.path.exists(csv_path)}")
```

### 감독을 찾을 수 없는 경우

1. **감독 이름 확인**: CSV 파일에 해당 감독이 있는지 확인
2. **부분 매칭**: 질의에 감독 이름이 포함되어 있는지 확인
3. **대소문자**: 대소문자는 무시됩니다

### CSV 파싱 오류

```bash
# CSV 파싱 테스트
python test_director_csv_parse.py
```

## 데이터 업데이트

### 수동 업데이트

1. `data/raw/director_ranking.csv` 파일을 직접 편집
2. 형식: `인덱스,감독명,rank1_count`

### KOBIS에서 자동 수집

```bash
# 전체 감독 목록으로 수집
python student/day2/impl/scrape_kobis_directors.py \
    --input_csv data/raw/director_ranking.csv \
    --output_csv data/raw/director_ranking_new.csv
```

## RAG 인덱스에 추가하기

감독 정보를 RAG 인덱스에 추가하여 더 풍부한 검색을 할 수 있습니다:

```bash
# 1. 감독 정보를 텍스트 파일로 변환
python -c "
import csv
with open('data/raw/director_ranking.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    with open('data/raw/director_info.txt', 'w', encoding='utf-8') as out:
        for row in reader:
            director = row.get('director', '').strip().strip('\"')
            count = row.get('rank1_count', '').strip().strip('\"')
            if director and count:
                out.write(f'{director} 감독은 {count}번 1위를 했습니다.\\n')
"

# 2. Day2 인덱스에 추가
python student/day2/impl/build_index.py \
    --paths data/raw/director_info.txt \
    --index_dir indices/day2
```

## 참고 자료

- CSV 파일: `data/raw/director_ranking.csv`
- KOBIS 스크래핑 스크립트: `student/day2/impl/scrape_kobis_directors.py`
- Day2 에이전트: `student/day2/agent.py`
- 테스트 스크립트: `test_director_csv_parse.py`

