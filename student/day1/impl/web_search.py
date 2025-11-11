# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Tuple, Callable, Set
import re, os
from .tavily_client import search_tavily, extract_url, extract_text

# (기존) -------------------------
PROFILE_DOMAINS = [
    "wikipedia.org", "en.wikipedia.org", "ko.wikipedia.org",
    "finance.google.com", "google.com/finance",
    "invest.deepsearch.com", "m.invest.zum.com",
    "companiesmarketcap.com", "marketscreener.com",
    "alphasquare.co.kr",
]

def looks_like_ticker(q: str) -> bool:
    return bool(re.search(r"\b([A-Z]{1,5}(?:\.[A-Z]{2,4})?|\d{6}(?:\.[A-Z]{2,4})?)\b", q))

def search_company_profile(query: str, api_key: str, topk: int = 6, timeout: int = 20) -> List[Dict[str, Any]]:
    q = f"{query} company profile overview 기업 개요 회사 소개 무엇을 하는 회사"
    results = search_tavily(q, api_key, top_k=topk, timeout=timeout, include_raw_content=True)
    def score(r: Dict[str, Any]) -> Tuple[int, float]:
        dom = (r.get("source") or r.get("url") or "").lower()
        prio = 0
        for i, d in enumerate(PROFILE_DOMAINS):
            if d in dom:
                prio = 100 - i
                break
        return (-prio, -float(r.get("score", 0.0)))
    return sorted(results, key=score)

def extract_and_summarize_profile(
    urls: List[str],
    api_key: str,
    summarizer: Callable[[str], str],
    max_chars: int = 6000
) -> str:
    texts: List[str] = []
    for u in urls[:2]:
        try:
            clean = extract_url(u)
            t = extract_text(clean, api_key)[:max_chars]
            if len(t) > 500:
                texts.append(f"[{clean}]\n{t}")
        except Exception:
            continue
    if not texts:
        return ""
    joined = "\n\n---\n\n".join(texts)
    prompt = (
        "다음 자료를 근거로 '기업 개요'를 한국어 5~7줄로 요약하세요.\n"
        "- 핵심 사업/제품, 수익원, 주요 시장/고객, 차별점, 최근 이슈(있으면)\n"
        "- 과도한 재무 디테일은 피하고, 문장당 20~30자 이내로 간결하게.\n\n"
        f"{joined}\n"
    )
    return summarizer(prompt)

# (신규) -------------------------
# 1) 부정 키워드 사전 (KO/EN)
RISK_NEG_KO: List[str] = [
    "논란","의혹","혐의","수사","체포","구속","기소","유죄","징역","벌금","송치",
    "소송","고소","고발","분쟁","법적 대응","합의금",
    "횡령","배임","탈세","분식회계","뇌물","로비","부패","갑질","블랙리스트",
    "성폭력","성추행","성희롱","성범죄","#미투","미투","학폭","학교폭력","폭행","가정폭력",
    "마약","약물","음주운전","도박",
    "표절","사기","사문서위조","허위","비리",
    "파산","부도","리콜","보이콧","하차","제작 중단","촬영 중단","방영 중단"
]
RISK_NEG_EN: List[str] = [
    "scandal","controversy","allegation","accusation","investigation","arrest","indicted","lawsuit","legal dispute",
    "fraud","embezzlement","breach of trust","tax evasion","bribery","corruption",
    "sexual assault","harassment","#metoo","bullying","violence","assault",
    "drug","narcotics","dui","gambling",
    "plagiarism","defamation","fabrication","misconduct",
    "bankruptcy","insolvency","recall","boycott","drop out","production halted","suspended"
]

# 2) 신뢰 뉴스 도메인 (필요 시 자유롭게 확장)
TRUSTED_NEWS_DOMAINS: List[str] = [
    # KR
    "yna.co.kr","yonhapnews","kbs.co.kr","mbc.co.kr","sbs.co.kr",
    "jtbc.co.kr","newsis.com","hankyung.com","edaily.co.kr","chosun.com","joongang.co.kr","hani.co.kr",
    "mk.co.kr","donga.com","khan.co.kr","biz.chosun.com","news.naver.com",
    # Global/industry
    "reuters.com","apnews.com","bbc.com","bloomberg.com","ft.com","wsj.com","nytimes.com","theguardian.com",
    "variety.com","hollywoodreporter.com","deadline.com","thewrap.com"
]

def _kwset(extra: List[str]) -> Set[str]:
    base = [*RISK_NEG_KO, *RISK_NEG_EN]
    if extra:
        base += [e for e in extra if isinstance(e, str) and e.strip()]
    return {k.lower().strip() for k in base}

def build_risk_query(entity: str, extra: List[str] | None = None) -> str:
    """
    Tavily용 리스크 검색 쿼리 생성.
    예: "배우A (논란 OR 소송 OR scandal OR lawsuit ...)"
    """
    kws = _kwset(extra or [])
    # 너무 길어지지 않도록 상위 키워드만 일부 사용(원하는 경우 확장 가능)
    ko = [k for k in RISK_NEG_KO][:15]
    en = [k for k in RISK_NEG_EN][:15]
    joined = " OR ".join([*ko, *en])
    return f'{entity} ({joined})'

def search_risk_issues(
    entity: str,
    api_key: str,
    topk: int = 8,
    timeout: int = 20,
    trust_only: bool = True,
    time_range: str = "y",      # 'd'|'w'|'m'|'y'|'all'
    extra_keywords: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    문화·콘텐츠 투자 리스크(부정 뉴스/이슈) 수집:
      - 부정 키워드 기반 고급 검색
      - 신뢰 도메인 제한(옵션)
      - 기간 필터(time_range)
      - 부정 키워드 매칭 스코어(risk_score)와 매칭 리스트 포함
    """
    q = build_risk_query(entity, extra=extra_keywords or [])
    include_domains = TRUSTED_NEWS_DOMAINS if trust_only else None

    # topk의 2~3배 검색 후 필터/재정렬
    raw = search_tavily(
        q, api_key, top_k=max(12, topk * 2), timeout=timeout,
        include_domains=include_domains, search_depth="advanced",
        time_range=time_range, include_raw_content=False
    )

    # 키워드 매칭/정규화/중복 제거
    kws = _kwset(extra_keywords or [])
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for r in raw or []:
        url = extract_url(r.get("url") or r.get("source") or "")
        if not url or url in seen:
            continue
        text = " ".join([
            str(r.get("title") or ""),
            str(r.get("content") or ""),
            str(r.get("snippet") or "")
        ]).lower()
        matched = sorted({kw for kw in kws if kw in text})
        if not matched:
            # 부정 키워드가 본문/타이틀에 전혀 없으면 제외 (정밀도 ↑)
            continue
        score_base = float(r.get("score", 0.0) or 0.0)
        risk_score = len(matched) + score_base  # 간단 가중치
        item = dict(r)
        item["url"] = url
        item["risk_score"] = float(f"{risk_score:.4f}")
        item["matched_keywords"] = matched
        seen.add(url)
        out.append(item)

    # 신뢰 도메인 우선 정렬 → 매칭 강도 → 검색엔진 score
    def rank_key(x: Dict[str, Any]) -> Tuple[int, float, float]:
        dom = (x.get("source") or x.get("url") or "").lower()
        prio = 0
        for i, d in enumerate(TRUSTED_NEWS_DOMAINS):
            if d in dom:
                prio = 100 - i
                break
        return (-prio, -float(x.get("risk_score", 0.0)), -float(x.get("score", 0.0)))

    out.sort(key=rank_key)
    return out[:topk]
