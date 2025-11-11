# -*- coding: utf-8 -*-
"""
넷플릭스 Top 리스트 뽑기 (docs.jsonl → meta.rank 기반)
- 나라/카테고리는 CLI 인자 또는 query 문장에서 자동 추출
- 출력 + (옵션) CSV 저장

사용 예:
python -m student.day2.tools.toplist --index_dir indices/netflix_multi --query "South Korea Movies Top 10" --top_n 10
python -m student.day2.tools.toplist --index_dir indices/netflix_multi --country "Türkiye" --category Shows --top_n 5 --out_csv out.csv
"""

import json, argparse, re, csv
from pathlib import Path
from typing import List, Dict, Any

# ---------------------------------------------------
# 0) 국가/카테고리 정규화(별칭 지원)
# ---------------------------------------------------
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
    "japan": "Japan",
    "france": "France",
}

def norm_country(s: str | None) -> str | None:
    if not s:
        return None
    key = s.strip().lower()
    return COUNTRY_ALIASES.get(key, s.strip())

def norm_category(s: str | None) -> str | None:
    if not s:
        return None
    key = s.strip().lower()
    if key.startswith("show"):
        return "Shows"
    if key.startswith("movie"):
        return "Movies"
    return s.strip().capitalize()

# ---------------------------------------------------
# 1) 데이터 로드/선택
# ---------------------------------------------------
def load_docs(docs_path: Path) -> List[Dict[str, Any]]:
    out = []
    for ln in docs_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out

def available_values(docs: List[Dict[str, Any]]):
    countries = set()
    categories = set()
    for r in docs:
        m = r.get("meta", {}) or {}
        if m.get("country"):
            countries.add(m["country"])
        if m.get("category"):
            categories.add(m["category"])
    return sorted(countries), sorted(categories)

def pick_top(docs: List[Dict[str, Any]], country: str | None, category: str | None, top_n: int | None):
    want_c = norm_country(country) if country else None
    want_cat = norm_category(category) if category else None

    rows = []
    for r in docs:
        meta = r.get("meta", {}) or {}
        title = (r.get("text") or "").strip()
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

# ---------------------------------------------------
# 2) query에서 나라/카테고리 자동 추출
#    - docs.jsonl에 존재하는 값들 기반으로 매칭 → 오탐 최소화
# ---------------------------------------------------
def parse_from_query(q: str, known_countries: List[str], known_categories: List[str]):
    """
    query 문장에서 country, category, top_n 자동 추출
    """
    if not q:
        return None, None, None

    qnorm = " " + re.sub(r"\s+", " ", q).strip() + " "
    cand_country = None
    cand_category = None
    cand_topn = None

    # (1) 카테고리 빠르게 추출
    if re.search(r"\bshow(s)?\b", qnorm, flags=re.I):
        cand_category = "Shows"
    elif re.search(r"\bmovie(s)?\b", qnorm, flags=re.I):
        cand_category = "Movies"

    # (2) 국가명은 known 목록을 길이순으로 탐색 (긴 이름 우선 매칭)
    for name in sorted(known_countries, key=len, reverse=True):
        pattern = r"\b" + re.escape(name) + r"\b"
        if re.search(pattern, qnorm, flags=re.I):
            cand_country = name
            break

    # (3) 별칭도 시도 (예: turkiye, usa 등)
    if not cand_country:
        for alias, canon in COUNTRY_ALIASES.items():
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, qnorm, flags=re.I):
                if canon in known_countries:
                    cand_country = canon
                    break

    # (4) Top N 숫자 추출
    # ex: "top 10", "Top5", "상위 3", "TOP-20", "top10 movies"
    m = re.search(r"(?:top|상위)\s*[-_#:]?\s*(\d{1,3})", qnorm, flags=re.I)
    if m:
        try:
            cand_topn = int(m.group(1))
        except Exception:
            pass

    return cand_country, cand_category, cand_topn


# ---------------------------------------------------
# 3) CLI
# ---------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="넷플릭스 TOP 리스트(랭크 기반) 조회기")
    p.add_argument("--index_dir", required=True, help="faiss.index + docs.jsonl가 있는 폴더")
    p.add_argument("--query", default=None, help='예: "South Korea Movies top 10"')
    p.add_argument("--country", default=None)
    p.add_argument("--category", default=None, choices=["Movies","Shows","movies","shows"])
    p.add_argument("--top_n", type=int, default=10)
    p.add_argument("--out_csv", default=None)
    return p.parse_args()

def main():
    args = parse_args()
    docs_path = Path(args.index_dir) / "docs.jsonl"
    if not docs_path.exists():
        raise SystemExit(f"docs.jsonl not found: {docs_path}")

    docs = load_docs(docs_path)
    countries, categories = available_values(docs)

    # 1) query에서 추출
    q_country, q_category, q_topn = parse_from_query(args.query or "", countries, categories)
 

    # 2) CLI 인자가 있으면 우선
    country = q_country or args.country
    category = q_category or args.category 
    top_n = q_topn or args.top_n 

    # 3) 최종 정규화
    country = norm_country(country) if country else country
    category = norm_category(category) if category else category

    # 4) 조회
    rows = pick_top(docs, country, category, top_n)

    # 5) 출력
    hdr = f"{country or 'ALL'} / {category or 'ALL'} / Top {top_n}"
    print(f"\n[TOP LIST] {hdr}")
    if not rows:
        print("  (비었습니다. country/category/top_n을 확인하세요)")
        # 힌트: 사용 가능한 값 프린트
        print("\n[HINT] Available countries:", ", ".join(countries))
        print("[HINT] Available categories:", ", ".join(categories))
        return

    for r in rows:
        wk = f" ({r['weeks_in_top']}w)" if r.get("weeks_in_top") is not None else ""
        print(f"  {r['rank']:02d}. {r['title']}{wk}")

    # 6) CSV 저장
    if args.out_csv:
        outp = Path(args.out_csv)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with open(outp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\n[OK] CSV saved: {outp}")

if __name__ == "__main__":
    main()
