# -*- coding: utf-8 -*-
"""
Day2: RAG 도구 에이전트
- 역할: Day2 RAG 본체 호출 → 결과 렌더 → 저장(envelope) → 응답
- 넷플릭스 TOP 리스트 지원: 질의에서 country/category/top_n 추출하여 rank 기반 TOP 리스트 반환
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import os
import json
import re
from pathlib import Path

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from .impl.rag import Day2Agent
from ..common.writer import render_day2, render_enveloped
from ..common.schemas import Day2Plan
from ..common.fs_utils import save_markdown


# ------------------------------------------------------------------------------
# TODO[DAY2-A-01] 모델 선택
#  - LiteLlm(model="openai/gpt-4o-mini") 등 경량 모델 지정
# ------------------------------------------------------------------------------
MODEL = LiteLlm(model="openai/gpt-4o-mini")  # 예: MODEL = LiteLlm(model="openai/gpt-4o-mini")

# 넷플릭스 TOP 리스트 관련 상수 및 함수
COUNTRY_ALIASES = {
    "united state": "United States",
    "united states": "United States",
    "usa": "United States",
    "us": "United States",
    "south korea": "South Korea",
    "republic of korea": "South Korea",
    "korea, south": "South Korea",
    "turkiye": "Türkiye",
    "türkiye": "Türkiye",
}

def _normalize_country(name: str) -> str:
    if not name:
        return name
    key = (name or "").strip().lower()
    return COUNTRY_ALIASES.get(key, name)

def _normalize_category(name: str) -> str:
    if not name:
        return name
    key = (name or "").strip().lower()
    if key.startswith("show"):
        return "Shows"
    if key.startswith("movie"):
        return "Movies"
    return name.strip().capitalize()

def _load_docs_jsonl(docs_path: str) -> List[Dict[str, Any]]:
    """docs.jsonl 파일 로드"""
    docs = []
    if not os.path.exists(docs_path):
        return docs
    with open(docs_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                docs.append(json.loads(line))
            except Exception:
                pass
    return docs

def _available_values(docs: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """인덱스에서 사용 가능한 country와 category 목록 추출"""
    countries = set()
    categories = set()
    for doc in docs:
        meta = doc.get("meta", {}) or {}
        if meta.get("country"):
            countries.add(meta["country"])
        if meta.get("category"):
            categories.add(meta["category"])
    return sorted(countries), sorted(categories)

def _parse_from_query(query: str, known_countries: List[str], known_categories: List[str]) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """질의에서 country, category, top_n 추출"""
    if not query:
        return None, None, None
    
    qnorm = " " + re.sub(r"\s+", " ", query).strip() + " "
    cand_country = None
    cand_category = None
    cand_topn = None
    
    # (1) 카테고리 추출
    if re.search(r"\bshow(s)?\b", qnorm, flags=re.I):
        cand_category = "Shows"
    elif re.search(r"\bmovie(s)?\b", qnorm, flags=re.I):
        cand_category = "Movies"
    
    # (2) 국가명 추출 (긴 이름 우선)
    for name in sorted(known_countries, key=len, reverse=True):
        pattern = r"\b" + re.escape(name) + r"\b"
        if re.search(pattern, qnorm, flags=re.I):
            cand_country = name
            break
    
    # (3) 별칭 시도
    if not cand_country:
        for alias, canon in COUNTRY_ALIASES.items():
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, qnorm, flags=re.I):
                if canon in known_countries:
                    cand_country = canon
                    break
    
    # (4) Top N 숫자 추출
    m = re.search(r"(?:top|상위)\s*[-_#:]?\s*(\d{1,3})", qnorm, flags=re.I)
    if m:
        try:
            cand_topn = int(m.group(1))
        except Exception:
            pass
    
    return cand_country, cand_category, cand_topn

def _pick_top_netflix(docs: List[Dict[str, Any]], country: Optional[str], category: Optional[str], top_n: Optional[int]) -> List[Dict[str, Any]]:
    """넷플릭스 TOP 리스트 추출 (rank 기반)"""
    want_c = _normalize_country(country) if country else None
    want_cat = _normalize_category(category) if category else None
    
    rows = []
    for doc in docs:
        meta = doc.get("meta", {}) or {}
        title = (doc.get("text") or "").strip()
        rank = meta.get("rank")
        if not title or rank is None:
            continue
        if want_c and meta.get("country") != want_c:
            continue
        if want_cat and (meta.get("category") or "").capitalize() != want_cat:
            continue
        rows.append({
            "rank": int(rank),
            "title": title,
            "country": meta.get("country"),
            "category": meta.get("category"),
            "weeks_in_top": meta.get("weeks_in_top"),
        })
    
    rows.sort(key=lambda x: x["rank"])
    if top_n:
        rows = [x for x in rows if x["rank"] <= top_n]
    return rows

def _is_netflix_query(query: str) -> bool:
    """넷플릭스 TOP 리스트 요청인지 판단"""
    q_lower = query.lower()
    netflix_keywords = ["넷플릭스", "netflix", "top", "상위", "랭킹", "ranking"]
    return any(kw in q_lower for kw in netflix_keywords)

def _load_director_csv(csv_path: str) -> Dict[str, int]:
    """감독 랭킹 CSV 파일 로드 (감독명 -> rank1_count 매핑)"""
    director_map = {}
    if not os.path.exists(csv_path):
        return director_map
    
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            if not lines:
                return director_map
            
            # 첫 번째 줄은 헤더 (예: ",director,rank1_count")
            # 각 줄의 형식: "숫자,감독명,rank1_count"
            for line_num, line in enumerate(lines[1:], start=2):  # 헤더 제외
                line = line.strip().strip('"')
                if not line:
                    continue
                
                # 빈 컬럼 제거 (시작 부분의 쉼표)
                if line.startswith(","):
                    line = line[1:]
                
                # 쉼표로 분리
                parts = [p.strip().strip('"') for p in line.split(",")]
                
                # 최소 3개 컬럼 필요: 인덱스, 감독명, rank1_count
                if len(parts) >= 3:
                    # parts[0]은 인덱스, parts[1]은 감독명, parts[2]는 rank1_count
                    director = parts[1] if len(parts) > 1 else None
                    rank1_count_str = parts[2] if len(parts) > 2 else None
                    
                    if director and rank1_count_str:
                        try:
                            # 숫자만 추출 (쉼표 등 제거)
                            rank1_count = int(rank1_count_str.replace(",", "").strip())
                            director_map[director] = rank1_count
                        except ValueError:
                            # 숫자 변환 실패 시 스킵
                            pass
    except Exception as e:
        print(f"[WARN] 감독 CSV 로드 실패: {e}")
        import traceback
        traceback.print_exc()
    
    return director_map

def _find_director_in_query(query: str, director_map: Dict[str, int]) -> Optional[Tuple[str, int]]:
    """질의에서 감독 이름 찾기"""
    if not director_map:
        return None
    
    query_lower = query.lower().strip()
    
    # 모든 감독 이름을 길이순으로 정렬 (긴 이름 우선 매칭)
    sorted_directors = sorted(director_map.keys(), key=len, reverse=True)
    
    # 1. 정확한 매칭 시도 (대소문자 무시)
    for director in sorted_directors:
        if director.lower() == query_lower:
            return (director, director_map[director])
    
    # 2. 부분 매칭 시도 (감독 이름이 질의에 포함되어 있는지)
    for director in sorted_directors:
        director_lower = director.lower()
        # 질의에 감독 이름이 포함되어 있는지 확인
        if director_lower in query_lower:
            return (director, director_map[director])
        # 부분 매칭 (예: "봉준호" -> "봉준호 감독")
        if query_lower in director_lower and len(query_lower) >= 2:
            return (director, director_map[director])
    
    return None

def _is_director_query(query: str) -> bool:
    """감독 조회 요청인지 판단"""
    q_lower = query.lower()
    director_keywords = ["감독", "director", "랭킹", "ranking", "1위", "rank1"]
    return any(kw in q_lower for kw in director_keywords)

def _is_detailed_director_query(query: str) -> bool:
    """감독의 상세 정보(경력, 작품 이력 등) 조회 요청인지 판단"""
    q_lower = query.lower()
    detailed_keywords = ["경력", "이력", "작품", "필모", "filmography", "career", "작품 목록", "대표작"]
    return any(kw in q_lower for kw in detailed_keywords)

def _is_simple_ranking_query(query: str) -> bool:
    """단순 랭킹 조회(1위 횟수만) 요청인지 판단"""
    q_lower = query.lower()
    ranking_keywords = ["1위 횟수", "랭킹", "ranking", "rank1", "1위 몇번"]
    return any(kw in q_lower for kw in ranking_keywords) and not _is_detailed_director_query(query)

def _handle_director_query(query: str, csv_path: str) -> Dict[str, Any]:
    """감독 조회 처리"""
    director_map = _load_director_csv(csv_path)
    
    if not director_map:
        return {
            "type": "director_query",
            "query": query,
            "found": False,
            "error": "감독 랭킹 데이터를 로드할 수 없습니다.",
        }
    
    director_info = _find_director_in_query(query, director_map)
    
    if director_info:
        director_name, rank1_count = director_info
        return {
            "type": "director_query",
            "query": query,
            "found": True,
            "director": director_name,
            "rank1_count": rank1_count,
            "message": f"{director_name} 감독은 {rank1_count}번 1위를 했습니다.",
        }
    else:
        # 질의에 감독 키워드는 있지만 매칭되는 감독이 없는 경우
        return {
            "type": "director_query",
            "query": query,
            "found": False,
            "error": "질의에서 감독을 찾을 수 없습니다.",
            "available_directors": list(director_map.keys())[:10],  # 처음 10개만 힌트로 제공
        }

def _handle_netflix_top(query: str, index_dir: str) -> Dict[str, Any]:
    """넷플릭스 TOP 리스트 처리"""
    try:
        docs_path = os.path.join(index_dir, "docs.jsonl")
        
        if not os.path.exists(docs_path):
            # 넷플릭스 인덱스가 없으면 netflix_multi 시도
            netflix_multi_dir = os.path.join(os.path.dirname(index_dir), "netflix_multi")
            netflix_multi_path = os.path.join(netflix_multi_dir, "docs.jsonl")
            if os.path.exists(netflix_multi_path):
                docs_path = netflix_multi_path
            else:
                return {
                    "type": "netflix_top",
                    "query": query,
                    "items": [],
                    "error": f"넷플릭스 인덱스를 찾을 수 없습니다: {index_dir} 또는 {netflix_multi_dir}",
                }
        
        docs = _load_docs_jsonl(docs_path)
        
        if not docs:
            return {
                "type": "netflix_top",
                "query": query,
                "items": [],
                "error": "인덱스에 데이터가 없습니다.",
            }
        
        # 사용 가능한 값들 확인
        known_countries, known_categories = _available_values(docs)
        
        # 질의에서 파라미터 추출
        country, category, top_n = _parse_from_query(query, known_countries, known_categories)
        
        # TOP 리스트 추출
        items = _pick_top_netflix(docs, country, category, top_n)
        
        return {
            "type": "netflix_top",
            "query": query,
            "items": items,
            "country": country,
            "category": category,
            "top_n": top_n,
            "available_countries": known_countries,
            "available_categories": known_categories,
        }
    except Exception as e:
        return {
            "type": "netflix_top",
            "query": query,
            "items": [],
            "error": f"넷플릭스 TOP 리스트 처리 중 오류: {str(e)}",
        }

def _handle_with_web_fallback(query: str) -> Dict[str, Any]:
    """RAG 검색 후 결과가 부족하면 웹 검색으로 보강"""
    index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
    
    # 1. RAG 검색 먼저 시도
    try:
        plan = Day2Plan()
        plan.index_dir = index_dir
        agent = Day2Agent(plan_defaults=plan)
        rag_payload: Dict[str, Any] = agent.handle(query, plan)
    except Exception as e:
        # RAG 검색 실패 시 빈 payload 반환
        return {
            "type": "rag_answer",
            "query": query,
            "contexts": [],
            "gating": {"status": "insufficient", "top_score": 0.0, "mean_topk": 0.0},
            "answer": "",
            "error": f"RAG 검색 실패: {str(e)}",
            "web_fallback": {"used": False, "error": str(e)},
        }
    
    # payload에 type 추가 (기본값: rag_answer)
    if "type" not in rag_payload:
        rag_payload["type"] = "rag_answer"
    
    # 2. RAG 결과 평가
    gating = rag_payload.get("gating", {})
    status = gating.get("status", "insufficient")
    contexts = rag_payload.get("contexts", [])
    
    # 3. 결과가 부족하면 웹 검색으로 보강
    use_web_fallback = os.getenv("DAY2_USE_WEB_FALLBACK", "true").lower() in ("1", "true", "yes", "y")
    
    if use_web_fallback and status == "insufficient" and len(contexts) == 0:
        # 웹 검색으로 보강
        try:
            from student.day1.agent import _handle as day1_handle
            
            web_payload = day1_handle(query)
            
            # Day1의 반환값 구조 확인: web_top 또는 items
            web_items = web_payload.get("web_top", []) or web_payload.get("items", [])
            
            # RAG 결과와 웹 검색 결과 병합
            rag_payload["web_fallback"] = {
                "used": True,
                "reason": "no_contexts",
                "web_results": web_items[:5],  # 상위 5개만
                "web_count": len(web_items),
            }
            # type은 rag_answer 유지 (render_day2에서 처리)
            
        except Exception as e:
            # 웹 검색 실패 시 RAG 결과만 반환
            rag_payload["web_fallback"] = {
                "used": False,
                "error": str(e),
            }
    elif use_web_fallback and status == "insufficient" and len(contexts) > 0:
        # RAG 결과가 있지만 신뢰도가 낮은 경우에도 웹 검색으로 보강
        try:
            from student.day1.agent import _handle as day1_handle
            
            web_payload = day1_handle(query)
            
            # Day1의 반환값 구조 확인: web_top 또는 items
            web_items = web_payload.get("web_top", []) or web_payload.get("items", [])
            
            rag_payload["web_fallback"] = {
                "used": True,
                "reason": "low_confidence",
                "rag_score": gating.get("top_score", 0.0),
                "web_results": web_items[:3],  # 상위 3개만
                "web_count": len(web_items),
            }
            # type은 rag_answer 유지 (render_day2에서 처리)
            
        except Exception as e:
            rag_payload["web_fallback"] = {
                "used": False,
                "error": str(e),
            }
    else:
        # RAG 결과가 충분한 경우
        rag_payload["web_fallback"] = {
            "used": False,
            "reason": "rag_sufficient",
            "rag_score": gating.get("top_score", 0.0),
        }
    
    return rag_payload

def _handle(query: str) -> Dict[str, Any]:
    """
    Day2 핸들러: 
    1. 넷플릭스 TOP 리스트 요청이면 rank 기반 추출
    2. 감독 조회 요청:
       - 단순 랭킹 조회(1위 횟수만) → CSV에서 rank1_count 반환
       - 상세 정보 조회(경력, 작품 이력) → CSV에서 rank1_count 가져온 후 RAG/웹 검색으로 보강
    3. 그 외는 일반 RAG 검색 (결과 부족 시 웹 검색으로 보강)
    """
    try:
        # 넷플릭스 TOP 리스트는 netflix_multi 인덱스 사용
        netflix_index_dir = os.getenv("NETFLIX_INDEX_DIR", "indices/netflix_multi")
        if not os.path.exists(netflix_index_dir):
            # 기본 인덱스 디렉토리에서 찾기
            base_index_dir = os.getenv("DAY2_INDEX_DIR", "indices/day2")
            netflix_index_dir = os.path.join(os.path.dirname(base_index_dir), "netflix_multi")
        
        # 넷플릭스 TOP 리스트 요청인지 확인
        if _is_netflix_query(query):
            return _handle_netflix_top(query, netflix_index_dir)
        
        # 감독 조회 요청인지 확인
        # CSV 경로: 프로젝트 루트/data/raw/director_ranking.csv
        # student/day2/agent.py -> student/ -> 프로젝트 루트
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(project_root, "data", "raw", "director_ranking.csv")
        
        if _is_director_query(query):
            director_result = _handle_director_query(query, csv_path)
            
            # 감독을 찾았을 때
            if director_result.get("found"):
                # 단순 랭킹 조회면 CSV 결과만 반환
                if _is_simple_ranking_query(query):
                    return director_result
                # 상세 정보 조회면 CSV 결과에 RAG/웹 검색으로 보강
                elif _is_detailed_director_query(query):
                    # RAG 검색으로 경력/작품 정보 수집
                    rag_result = _handle_with_web_fallback(query)
                    
                    # CSV 결과와 RAG 결과를 병합
                    director_name = director_result.get("director", "")
                    rank1_count = director_result.get("rank1_count", 0)
                    
                    # RAG 결과에 CSV 정보 추가
                    if "director_info" not in rag_result:
                        rag_result["director_info"] = {}
                    rag_result["director_info"]["name"] = director_name
                    rag_result["director_info"]["rank1_count"] = rank1_count
                    rag_result["director_info"]["message"] = f"{director_name} 감독은 {rank1_count}번 1위를 했습니다."
                    rag_result["type"] = "director_detail"  # 상세 정보 타입으로 변경
                    
                    return rag_result
                else:
                    # 기본적으로는 CSV 결과만 반환 (호환성 유지)
                    return director_result
        
        # 일반 RAG 검색 (결과 부족 시 웹 검색으로 보강)
        return _handle_with_web_fallback(query)
    
    except Exception as e:
        # 전역 예외 처리
        import traceback
        return {
            "type": "rag_answer",
            "query": query,
            "contexts": [],
            "gating": {"status": "insufficient", "top_score": 0.0, "mean_topk": 0.0},
            "answer": "",
            "error": f"Day2 핸들러 오류: {type(e).__name__}: {e}",
        }


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
    **kwargs,
) -> Optional[LlmResponse]:
    """
    UI 엔트리포인트 (Day1과 동일한 패턴):
      1) llm_request.contents[-1]에서 사용자 메시지 텍스트(query) 추출
      2) _handle(query) 호출 → payload 획득
      3) 본문 마크다운 렌더: render_day2(query, payload)
      4) 저장: save_markdown(query, route='day2', markdown=본문MD) → 경로
      5) envelope: render_enveloped('day2', query, payload, saved_path)
      6) LlmResponse로 반환 (AgentTool 호환 형식)
      7) 예외시 간단한 오류 텍스트 반환
    """
    try:
        # Day1과 정확히 동일한 패턴
        last = llm_request.contents[-1]
        if last.role == "user":
            query = last.parts[0].text
            payload = _handle(query)

            body_md = render_day2(query, payload)
            saved_path = save_markdown(query=query, route="day2", markdown=body_md)
            enveloped_md = render_enveloped(
                kind="day2",
                query=query,
                payload=payload,
                saved_path=saved_path,
            )

            return LlmResponse(
                content=types.Content(
                    parts=[types.Part(text=enveloped_md)],
                    role="model",
                )
            )
    except Exception as e:
        # 강사용: 에러 원인을 바로 확인할 수 있도록 간결 메시지 반환
        return LlmResponse(
            content=types.Content(
                parts=[types.Part(text=f"Day2 에러: {e}")],
                role="model",
            )
        )
    return None


day2_rag_agent = Agent(
    name="Day2RagAgent",
    model=MODEL,
    description="로컬 RAG 검색, 넷플릭스 TOP 리스트, 감독 랭킹 조회, 웹 검색 보강 (영화 투자사용)",
    instruction=(
        "영화 투자사 관점에서 로컬 인덱스 문서를 검색하여 요약하고 근거를 제시하라. "
        "넷플릭스 TOP 리스트 요청(예: '넷플릭스 한국 영화 TOP10')이면 rank 기반으로 TOP 리스트를 표로 제공하라. "
        "감독 조회 요청(예: '봉준호 감독 1위 횟수')이면 감독의 rank1_count를 반환하라. "
        "RAG 검색 결과가 부족하거나 신뢰도가 낮으면 자동으로 웹 검색으로 보강하여 최신 정보를 제공하라."
    ),
    tools=[],
    before_model_callback=before_model_callback,
)
