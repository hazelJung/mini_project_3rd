# -*- coding: utf-8 -*-
"""
인덱싱 입력 데이터 로딩/정제/청크
"""

import re, json
from typing import List, Dict, Any
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

TOP10_URL = "https://www.netflix.com/tudum/top10/"

COUNTRY_ALIASES = {
    "united state": "United States",
    "usa": "United States",
    "us": "United States",
    "south korea": "South Korea",
    "republic of korea": "South Korea",
    "turkiye": "Türkiye",        # 악센트 보정
    "korea, south": "South Korea",
}
def _normalize_country(name: str) -> str:
    key = (name or "").strip().lower()
    return COUNTRY_ALIASES.get(key, name)

def load_netflix_top10(country: str, category: str, headless: bool = True) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    # ✅ 입력 정규화
    country = _normalize_country(country)
    cat_raw = (category or "").strip().lower()
    cat_text = "Shows" if cat_raw.startswith("show") else "Movies"  # shows/movies 어떤 식으로 와도 처리

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(TOP10_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        # 오버레이/포커스 해제
        try:
            page.keyboard.press("Escape")
            page.mouse.click(10, 10)
        except Exception:
            pass

        def safe_select(uia_select: str, option_text: str):
            box = page.locator(uia_select).first
            expect(box).to_be_visible()
            box.scroll_into_view_if_needed()
            box.click()

            listbox = page.get_by_role("listbox")
            expect(listbox.first).to_be_visible()

            opt = listbox.get_by_role("option", name=re.compile(rf"^{re.escape(option_text)}$", re.I))
            if opt.count() == 0:
                opt = page.locator(
                    f"//li[normalize-space()='{option_text}'] | //div[@role='option' and normalize-space()='{option_text}']"
                )

            expect(opt.first).to_be_visible()
            opt.first.scroll_into_view_if_needed()
            try:
                opt.first.click(timeout=5000, force=True, trial=True)
            except Exception:
                pass
            opt.first.click(timeout=15000, force=True)

            # 드롭다운 닫힘 보장
            try:
                page.keyboard.press("Enter")
                page.keyboard.press("Escape")
            except Exception:
                pass
            page.wait_for_timeout(200)

        try:
            # 1) 나라
            safe_select('[data-uia="top10-country-select"]', country)
            # 2) 카테고리
            safe_select('[data-uia="top10-category-select"]', cat_text)

        except Exception:
            page.screenshot(path="netflix_select_error.png", full_page=True)
            Path("netflix_select_dump.html").write_text(page.content(), encoding="utf-8")
            browser.close()
            raise

        # 3) Top10 텍스트 수집
        texts: List[str] = []

        rows = page.locator("table tr")
        if rows.count():
            for i in range(rows.count()):
                row_text = rows.nth(i).inner_text().strip()
                if row_text:
                    texts.append(row_text)

        if not texts:
            cards = page.locator('[data-uia*="top10-card"], [data-uia*="Top10Card"], section[data-guid*="top10-card"]')
            if cards.count():
                for i in range(cards.count()):
                    t = cards.nth(i).inner_text().strip()
                    if t:
                        texts.append(t)

        if not texts:
            whole = page.locator("main").inner_text() if page.locator("main").count() else page.locator("body").inner_text()
            texts = [t.strip() for t in re.split(r"\n{2,}", whole) if len(t.strip()) > 10][:50]

        for i, t in enumerate(texts):
            items.append({
                "path": f"netflix://{country}/{cat_text}/item_{i:02d}",
                "text": t,
            })

        browser.close()
    return items

def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def read_pdf_file(path: str) -> str:
    """
    pypdf 로 PDF 모든 페이지 텍스트 추출
    """
    from pypdf import PdfReader
    reader = PdfReader(path)
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)

def clean_text(s: str) -> str:
    s = s or ""
    s = re.sub(r"\r", "\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def chunk_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 200) -> List[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: List[str] = []
    start = 0
    step = chunk_size - chunk_overlap
    if step <= 0:
        step = chunk_size
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += step
    return chunks

def load_documents(paths_or_dir: List[str]) -> List[Dict[str, Any]]:
    files: List[str] = []
    for p in paths_or_dir:
        pp = Path(p)
        if pp.is_dir():
            for ext in ("*.txt", "*.md", "*.pdf"):
                files.extend([str(x) for x in pp.rglob(ext)])
        else:
            files.append(str(pp))

    docs: List[Dict[str, Any]] = []
    for fp in files:
        ext = fp.lower().split(".")[-1]
        if ext in ("txt", "md"):
            raw = read_text_file(fp)
        elif ext == "pdf":
            raw = read_pdf_file(fp)
        else:
            continue
        txt = clean_text(raw)
        docs.append({"path": fp, "text": txt})
    return docs

def build_corpus_netflix(country: str, category: str) -> List[Dict[str, Any]]:
    raw_docs = load_netflix_top10(country, category)
    normalized_category = category.capitalize()
    corpus: List[Dict[str, Any]] = []

    for d in raw_docs:
        raw = (d["text"] or "").strip()
        if raw.upper() == "RANKING":
            continue  # ✅ "RANKING" 항목은 제외

        # 개행을 공백으로 정리
        one_line = re.sub(r"\s+", " ", raw).strip()
        # 패턴: "<순위> <제목> <숫자>"  (마지막 숫자는 보통 주차/지표)
        m = re.match(r"^(?P<rank>\d{1,2})\s+(?P<title>.+?)\s+(?P<tailnum>\d+)$", one_line)
        rank = None
        title = one_line
        weeks = None

        if m:
            rank = int(m.group("rank"))
            title = m.group("title").strip()
            weeks = int(m.group("tailnum"))

        # 최종 청크 텍스트는 '제목'만
        chunks = chunk_text(clean_text(title))
        for i, ch in enumerate(chunks):
            cid = f"{d['path']}::chunk_{i:04d}"
            meta = {
                "path": d["path"],
                "chunk": i,
                "country": country,
                "category": normalized_category,
            }
            if rank is not None:
                meta["rank"] = rank
            if weeks is not None:
                meta["weeks_in_top"] = weeks

            corpus.append({
                "id": cid,
                "text": ch,          # ✅ 제목만 저장
                "meta": meta,
            })
    return corpus

def build_corpus(paths_or_dir: List[str]) -> List[Dict[str, Any]]:
    docs = load_documents(paths_or_dir)
    corpus: List[Dict[str, Any]] = []
    for d in docs:
        chunks = chunk_text(d["text"])
        for i, ch in enumerate(chunks):
            cid = f"{d['path']}::chunk_{i:04d}"
            corpus.append({"id": cid, "text": ch, "meta": {"path": d["path"], "chunk": i}})
    return corpus

def save_docs_jsonl(items: List[Dict[str, Any]], out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
