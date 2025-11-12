# -*- coding: utf-8 -*-
from typing import Dict, Any
from textwrap import dedent

# --------- 본문 렌더러들 ---------
def render_day1(query: str, payload: Dict[str, Any]) -> str:
    web = payload.get("web_top", []) or []
    prices = payload.get("prices", []) or []
    profile = (payload.get("company_profile") or "").strip()
    profile_sources = payload.get("profile_sources") or []
    risk = payload.get("risk_top", []) or []    # 리스크 기능 추가


    lines = [f"# 웹 리서치 리포트", f"- 질의: {query}", ""]

    # 1) 시세 스냅샷
    if prices:
        lines.append("## 시세 스냅샷")
        for p in prices:
            sym = p.get("symbol", "")
            cur = f" {p.get('currency')}" if p.get("currency") else ""
            if p.get("price") is not None:
                lines.append(f"- **{sym}**: {p['price']}{cur}")
            else:
                lines.append(f"- **{sym}**: (가져오기 실패) — {p.get('error','')}")
        lines.append("")

    # 2) 기업 정보 요약(발췌 + 출처)
    if profile:
        # 500자 정도로 길이 제한(가독)
        short = profile[:500].rstrip()
        if len(profile) > 500:
            short += "…"
        lines.append("## 기업 정보 요약")
        lines.append(short)
        if profile_sources:
            lines.append("")
            lines.append("**출처(기업 정보):**")
            for u in profile_sources[:3]:
                lines.append(f"- {u}")
        lines.append("")

    # (2.5) 투자 리스크 모니터링
    if risk:
        lines.append("## 투자 리스크 모니터링")
        for r in risk:
            title = r.get("title") or r.get("url") or "link"
            src = r.get("source") or ""
            date = r.get("published_date") or r.get("date") or ""
            url = r.get("url", "")
            risk_score = r.get("risk_score")
            tail = f" — {src}" + (f" ({date})" if date else "")
            score_str = f" [risk_score: {risk_score}]" if risk_score is not None else ""
            lines.append(f"- [{title}]({url}){tail}{score_str}")

            # 매칭된 부정 키워드
            matched = r.get("matched_keywords") or []
            if matched:
                lines.append(f"  - 부정 키워드 매칭: {', '.join(matched[:10])}")

            # 두 줄 발췌
            raw = (r.get("content") or r.get("snippet") or "").strip().replace("\n"," ")
            if raw:
                excerpt = raw[:280].rstrip()
                if len(raw) > 280:
                    excerpt += "…"
                lines.append(f"  > {excerpt}")
        lines.append("")


    # 3) 상위 웹 결과(타이틀 + 메타 + 2줄 발췌)
    if web:
        lines.append("## 관련 링크 & 발췌")
        for r in web[:5]:
            title = r.get("title") or r.get("url") or "link"
            src = r.get("source") or ""
            date = r.get("published_date") or r.get("date") or ""
            url = r.get("url", "")
            tail = f" — {src}" + (f" ({date})" if date else "")
            lines.append(f"- [{title}]({url}){tail}")

            # 2줄 발췌: content > snippet > '' 우선순위
            raw = (r.get("content") or r.get("snippet") or "").strip().replace("\n", " ")
            if raw:
                excerpt = raw[:280].rstrip()
                if len(raw) > 280:
                    excerpt += "…"
                lines.append(f"  > {excerpt}")
        lines.append("")

    # 웹 결과가 전혀 없을 때 힌트
    if not (web or profile or prices):
        lines.append("_참고: 결과가 비어있습니다. 쿼리/도메인 제한/키워드 설정을 확인하세요._")
        lines.append("")

    return "\n".join(lines)


def render_day2(query: str, payload: dict) -> str:
    """
    Day2 렌더러:
    - director_query: 감독 랭킹 조회 (CSV만)
    - director_detail: 감독 상세 정보 (CSV + RAG/웹 검색)
    - netflix_top: 넷플릭스 TOP 리스트
    - rag_answer: 일반 RAG 검색
    """
    lines = []
    lines.append(f"# Day2 – RAG 요약")
    lines.append("")
    lines.append(f"**질의:** {query}")
    lines.append("")

    # ── 감독 조회 처리
    payload_type = (payload or {}).get("type", "")
    
    # 감독 상세 정보 (CSV + RAG/웹 검색)
    if payload_type == "director_detail":
        director_info = (payload or {}).get("director_info", {})
        director_name = director_info.get("name", "")
        rank1_count = director_info.get("rank1_count", 0)
        message = director_info.get("message", "")
        
        lines.append("## 감독 상세 정보")
        lines.append("")
        
        # CSV 정보 (랭킹)
        if director_name:
            lines.append(f"**감독:** {director_name}")
            lines.append("")
            if rank1_count > 0:
                lines.append(f"**1위 횟수:** {rank1_count}회")
                lines.append("")
            if message:
                lines.append(message)
                lines.append("")
        
        # RAG/웹 검색 결과 (경력, 작품 이력 등)
        answer = (payload or {}).get("answer") or ""
        if answer:
            lines.append("## 경력 및 작품 이력")
            lines.append("")
            lines.append(answer.strip())
            lines.append("")
        
        # 근거 표시
        contexts = (payload or {}).get("contexts") or []
        if contexts:
            lines.append("## 근거(Top-K)")
            lines.append("")
            lines.append("| rank | score | path | chunk_id | excerpt |")
            lines.append("|---:|---:|---|---:|---|")
            for i, c in enumerate(contexts[:5], 1):  # 상위 5개만
                score = f"{float(c.get('score', 0.0)):.3f}"
                path = str(c.get("path") or c.get("meta", {}).get("path") or "")
                raw = (
                    c.get("text")
                    or c.get("chunk")
                    or c.get("content")
                    or ""
                )
                excerpt = (str(raw).replace("\n", " ").strip())[:200]
                chunk_id = (
                    c.get("doc_id")
                    or c.get("id")
                    or c.get("meta", {}).get("chunk")
                    or c.get("chunk_id")
                    or c.get("chunk_index")
                    or ""
                )
                lines.append(f"| {i} | {score} | {path} | {chunk_id} | {excerpt} |")
            lines.append("")
        
        # 웹 검색 보강 결과
        web_fallback = (payload or {}).get("web_fallback", {})
        if web_fallback.get("used"):
            web_results = web_fallback.get("web_results", [])
            if web_results:
                lines.append("## 웹 검색 보강 결과")
                lines.append("")
                lines.append(f"*RAG 결과가 부족하여 웹 검색으로 보강했습니다.*")
                lines.append("")
                lines.append("| 순위 | 제목 | URL | 요약 |")
                lines.append("|:---:|:---|:---|:---|")
                for i, item in enumerate(web_results[:5], 1):
                    title = item.get("title", "")[:100]
                    url = item.get("url", "")[:80]
                    snippet = item.get("snippet", item.get("content", ""))[:150]
                    lines.append(f"| {i} | {title} | {url} | {snippet} |")
                lines.append("")
        
        return "\n".join(lines)
    
    # 단순 감독 랭킹 조회 (CSV만)
    if payload_type == "director_query":
        found = (payload or {}).get("found", False)
        if found:
            director = (payload or {}).get("director", "")
            rank1_count = (payload or {}).get("rank1_count", 0)
            message = (payload or {}).get("message", "")
            
            lines.append("## 감독 랭킹 조회 결과")
            lines.append("")
            lines.append(f"**감독:** {director}")
            lines.append("")
            lines.append(f"**1위 횟수:** {rank1_count}회")
            lines.append("")
            if message:
                lines.append(message)
                lines.append("")
        else:
            error = (payload or {}).get("error", "")
            available_directors = (payload or {}).get("available_directors", [])
            
            lines.append("## 감독 랭킹 조회 결과")
            lines.append("")
            if error:
                lines.append(f"**오류:** {error}")
                lines.append("")
            if available_directors:
                lines.append("**참고:** 사용 가능한 감독 예시")
                lines.append("")
                for director in available_directors[:10]:
                    lines.append(f"- {director}")
                lines.append("")
        
        return "\n".join(lines)
    
    # ── 넷플릭스 TOP 리스트 처리
    if payload_type == "netflix_top":
        items = (payload or {}).get("items", [])
        country = (payload or {}).get("country")
        category = (payload or {}).get("category")
        top_n = (payload or {}).get("top_n")
        
        lines.append("## 넷플릭스 TOP 리스트")
        lines.append("")
        
        # 필터 정보 표시
        if country or category or top_n:
            filter_info = []
            if country:
                filter_info.append(f"국가: {country}")
            if category:
                filter_info.append(f"카테고리: {category}")
            if top_n:
                filter_info.append(f"상위 {top_n}개")
            if filter_info:
                lines.append(f"**필터:** {', '.join(filter_info)}")
                lines.append("")
        
        if not items:
            error = (payload or {}).get("error", "")
            if error:
                lines.append(f"**오류:** {error}")
            else:
                lines.append("검색 결과가 없습니다.")
            lines.append("")
        else:
            # TOP 리스트 표
            lines.append("| 순위 | 제목 | 국가 | 카테고리 | 주차 |")
            lines.append("|:---:|:---|:---|:---|:---:|")
            for item in items:
                rank = item.get("rank", "")
                title = item.get("title", "")
                country_val = item.get("country", "")
                category_val = item.get("category", "")
                weeks = item.get("weeks_in_top", "")
                weeks_str = f"{weeks}주" if weeks else ""
                lines.append(f"| {rank} | {title} | {country_val} | {category_val} | {weeks_str} |")
            lines.append("")
        
        # 사용 가능한 값들 표시 (디버깅용, 선택적)
        available_countries = (payload or {}).get("available_countries", [])
        available_categories = (payload or {}).get("available_categories", [])
        if available_countries or available_categories:
            lines.append("**참고:** 사용 가능한 필터 값")
            if available_countries:
                lines.append(f"- 국가: {', '.join(available_countries)}")
            if available_categories:
                lines.append(f"- 카테고리: {', '.join(available_categories)}")
            lines.append("")
        
        return "\n".join(lines)

    # ── 일반 RAG 요약 처리
    # ── 추가: 초안(answer) 표시
    answer = (payload or {}).get("answer") or ""
    if answer:
        lines.append("## 초안 요약")
        lines.append("")
        lines.append(answer.strip())
        lines.append("")

    # ── 추가: 근거 상위 K 표
    contexts = (payload or {}).get("contexts") or []
    if contexts:
        lines.append("## 근거(Top-K)")
        lines.append("")
        lines.append("| rank | score | path | chunk_id | excerpt |")
        lines.append("|---:|---:|---|---:|---|")
        for i, c in enumerate(contexts, 1):
            score = f"{float(c.get('score', 0.0)):.3f}"
            path = str(c.get("path") or c.get("meta", {}).get("path") or "")

            # excerpt 후보(우선순위: text > chunk > content)
            raw = (
                c.get("text")
                or c.get("chunk")
                or c.get("content")
                or ""
            )
            excerpt = (str(raw).replace("\n", " ").strip())[:200]

            # chunk_id 후보(우선순위: doc_id > id > meta.chunk > chunk_id > chunk_index)
            chunk_id = (
                c.get("doc_id")
                or c.get("id")
                or c.get("meta", {}).get("chunk")
                or c.get("chunk_id")
                or c.get("chunk_index")
                or ""
            )

            lines.append(f"| {i} | {score} | {path} | {chunk_id} | {excerpt} |")
        lines.append("")
    
    # ── 웹 검색 보강 결과 표시
    web_fallback = (payload or {}).get("web_fallback", {})
    if web_fallback.get("used"):
        web_results = web_fallback.get("web_results", [])
        if web_results:
            lines.append("## 웹 검색 보강 결과")
            lines.append("")
            lines.append(f"*RAG 결과가 부족하여 웹 검색으로 보강했습니다.*")
            lines.append("")
            
            # 웹 검색 결과 표
            lines.append("| 순위 | 제목 | URL | 요약 |")
            lines.append("|:---:|:---|:---|:---|")
            for i, item in enumerate(web_results[:5], 1):  # 상위 5개만
                title = item.get("title", "")[:100]
                url = item.get("url", "")[:80]
                snippet = item.get("snippet", item.get("content", ""))[:150]
                lines.append(f"| {i} | {title} | {url} | {snippet} |")
            lines.append("")
        else:
            lines.append("## 웹 검색 보강")
            lines.append("")
            lines.append("*웹 검색을 시도했지만 결과를 찾을 수 없었습니다.*")
            lines.append("")

    return "\n".join(lines)

def render_day3(query: str, payload: Dict[str, Any]) -> str:
    items = payload.get("items", [])
    lines = [f"# 공고 탐색 결과", f"- 질의: {query}", ""]
    if items:
        lines.append("| 출처 | 제목 | 기관 | 접수 마감 | 예산 | URL |")
        lines.append("|---|---|---|---:|---:|---|")
        for it in items[:10]:
            src = it.get('source','-')
            title = it.get('title','-')
            agency = it.get('agency','-')
            close = it.get('close_date','-')
            budget = it.get('budget','-')
            url = it.get('url','-')
            lines.append(f"| {src} | {title} | {agency} | {close or '-'} | {budget or '-'} | {url} |")
    else:
        lines.append("관련 공고를 찾지 못했습니다.")
        
    has_atts = any(it.get("attachments") for it in items)
    if has_atts:
        lines.append("\n## 첨부파일 요약")
        for i, it in enumerate(items[:10], 1):
            atts = it.get("attachments") or []
            if not atts: 
                continue
            lines.append(f"- **{i}. {it.get('title','(제목)')}**")
            for a in atts[:5]:
                lines.append(f"  - {a}")
    return "\n".join(lines)

# --------- Envelope(머리말/푸터) ---------
def _compose_envelope(kind: str, query: str, body_md: str, saved_path: str) -> str:
    header = dedent(f"""\
    ---
    output_schema: v1
    type: markdown
    route: {kind}
    saved: {saved_path}
    query: "{query.replace('"','\\\"')}"
    ---

    """)
    footer = dedent(f"""\n\n---\n> 저장 위치: `{saved_path}`\n""")
    return header + body_md.strip() + footer

def render_enveloped(kind: str, query: str, payload: Dict[str, Any], saved_path: str) -> str:
    if kind == "day1":
        body = render_day1(query, payload)
    elif kind == "day2":
        body = render_day2(query, payload)
    elif kind == "day3":
        body = render_day3(query, payload)
    else:
        body = f"### 결과\n\n(알 수 없는 kind: {kind})"
    return _compose_envelope(kind, query, body, saved_path)
