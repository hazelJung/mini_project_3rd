# -*- coding: utf-8 -*-
"""
KOBIS에서 감독 정보 수집
- 감독 검색 및 상세 정보 수집
- 수상내역 개수 또는 필모그래피 정보 수집
"""

from __future__ import annotations
import time
import re
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright, expect, Page
import csv
from pathlib import Path

KOBIS_BASE_URL = "https://kobis.or.kr"
KOBIS_SEARCH_URL = "https://kobis.or.kr/kobis/business/mast/peop/searchPeopleList.do"

def search_director(page: Page, director_name: str, max_wait: int = 10000) -> List[Dict[str, Any]]:
    """감독 이름으로 검색하여 결과 리스트 반환"""
    results = []
    
    try:
        # 검색 페이지로 이동
        page.goto(KOBIS_SEARCH_URL, wait_until="domcontentloaded", timeout=max_wait)
        page.wait_for_load_state("networkidle", timeout=max_wait)
        
        # 검색어 입력 필드 찾기
        # KOBIS 사이트 구조에 따라 선택자 조정 필요
        search_input = page.locator('input[name="sPeopleNm"], input[id="sPeopleNm"], input[placeholder*="영화인명"]').first
        if search_input.count() == 0:
            # 다른 선택자 시도
            search_input = page.locator('input[type="text"]').filter(has_text=re.compile("영화인", re.I)).first
            if search_input.count() == 0:
                search_input = page.locator('input[type="text"]').nth(0)
        
        if search_input.count() > 0:
            search_input.fill(director_name)
            time.sleep(0.5)
            
            # 검색 버튼 클릭
            search_button = page.locator('button[type="submit"], input[type="submit"], button:has-text("검색"), a:has-text("검색")').first
            if search_button.count() == 0:
                # Enter 키로 검색
                search_input.press("Enter")
            else:
                search_button.click()
            
            page.wait_for_load_state("networkidle", timeout=max_wait)
            time.sleep(1)
            
            # 검색 결과 테이블에서 감독 정보 추출
            # 테이블 구조에 따라 선택자 조정
            rows = page.locator('table tbody tr, .search-result tr, .list-table tr').all()
            
            for row in rows[:10]:  # 최대 10개 결과만
                try:
                    # 감독명 추출
                    name_elem = row.locator('td:first-child a, .name a, a[href*="people"]').first
                    if name_elem.count() > 0:
                        name = name_elem.inner_text().strip()
                        link = name_elem.get_attribute("href") or ""
                        
                        # 필모그래피 개수 추출 (예: "외 3편")
                        filmography = row.locator('td').last.inner_text().strip()
                        film_count_match = re.search(r'(\d+)편', filmography)
                        film_count = int(film_count_match.group(1)) if film_count_match else 0
                        
                        # 분야 확인 (감독인지)
                        field_elem = row.locator('td').nth(-2) if row.locator('td').count() > 2 else None
                        field = field_elem.inner_text().strip() if field_elem and field_elem.count() > 0 else ""
                        
                        if "감독" in field or film_count > 0:
                            results.append({
                                "name": name,
                                "link": link,
                                "film_count": film_count,
                                "field": field,
                            })
                except Exception as e:
                    print(f"  [WARN] 행 파싱 실패: {e}")
                    continue
    except Exception as e:
        print(f"  [WARN] 검색 실패 ({director_name}): {e}")
    
    return results

def get_director_detail(page: Page, director_link: str, max_wait: int = 10000) -> Dict[str, Any]:
    """감독 상세 페이지에서 정보 수집"""
    detail = {
        "award_count": 0,
        "film_count": 0,
        "details": {},
    }
    
    try:
        # 링크가 상대 경로인 경우 절대 경로로 변환
        if director_link.startswith("/"):
            director_link = KOBIS_BASE_URL + director_link
        elif not director_link.startswith("http"):
            director_link = KOBIS_BASE_URL + "/" + director_link
        
        page.goto(director_link, wait_until="domcontentloaded", timeout=max_wait)
        page.wait_for_load_state("networkidle", timeout=max_wait)
        time.sleep(1)
        
        # 수상내역 섹션 찾기
        award_section = page.locator('h3:has-text("수상"), h4:has-text("수상"), .award, .awards, div:has-text("수상")').first
        if award_section.count() > 0:
            # 수상내역 목록 개수 세기
            award_items = page.locator('ul li, .award-list li, .award-item').filter(has_text=re.compile("수상|상|시상", re.I)).all()
            detail["award_count"] = len(award_items)
        
        # 필모그래피 개수
        film_section = page.locator('h3:has-text("필모"), h4:has-text("필모"), .filmography').first
        if film_section.count() > 0:
            film_items = page.locator('ul li, .film-list li, .film-item').all()
            detail["film_count"] = len(film_items)
        
        # 페이지 전체 텍스트에서 수상 관련 키워드 찾기
        page_text = page.inner_text("body")
        award_keywords = ["수상", "시상", "영화제", "대상", "상"]
        award_matches = sum(1 for keyword in award_keywords if keyword in page_text)
        if award_matches > 0 and detail["award_count"] == 0:
            # 키워드 개수로 추정 (정확하지 않을 수 있음)
            detail["award_count"] = award_matches
        
    except Exception as e:
        print(f"  [WARN] 상세 정보 수집 실패: {e}")
    
    return detail

def scrape_directors_from_kobis(director_names: List[str], output_csv: str, headless: bool = True) -> None:
    """KOBIS에서 감독 정보 수집하여 CSV 파일로 저장"""
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        
        for i, director_name in enumerate(director_names, 1):
            print(f"[{i}/{len(director_names)}] 감독 검색: {director_name}")
            
            # 검색
            search_results = search_director(page, director_name)
            
            if not search_results:
                print(f"  [WARN] 검색 결과 없음: {director_name}")
                results.append({
                    "director": director_name,
                    "rank1_count": 0,
                    "film_count": 0,
                    "award_count": 0,
                    "status": "not_found",
                })
                continue
            
            # 첫 번째 결과 사용 (가장 관련성 높은 결과)
            best_match = search_results[0]
            print(f"  [OK] 찾음: {best_match['name']} (필모: {best_match.get('film_count', 0)}편)")
            
            # 상세 정보 수집
            if best_match.get("link"):
                detail = get_director_detail(page, best_match["link"])
                award_count = detail.get("award_count", 0)
                film_count = detail.get("film_count", 0) or best_match.get("film_count", 0)
            else:
                award_count = 0
                film_count = best_match.get("film_count", 0)
            
            # rank1_count는 수상내역 개수 또는 필모그래피 개수로 사용
            # (실제 1위 횟수는 KOBIS에서 직접 제공하지 않을 수 있음)
            rank1_count = award_count if award_count > 0 else film_count
            
            results.append({
                "director": best_match["name"],
                "rank1_count": rank1_count,
                "film_count": film_count,
                "award_count": award_count,
                "status": "found",
            })
            
            # 요청 간 딜레이
            time.sleep(1)
        
        browser.close()
    
    # CSV 파일로 저장
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["director", "rank1_count", "film_count", "award_count", "status"])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n[OK] CSV 파일 저장: {output_path}")
    print(f"  - 총 {len(results)}개 감독 정보 수집")
    print(f"  - 찾은 감독: {sum(1 for r in results if r['status'] == 'found')}개")

def load_director_names_from_existing_csv(csv_path: str) -> List[str]:
    """기존 CSV 파일에서 감독 이름 목록 로드"""
    director_names = []
    
    if not Path(csv_path).exists():
        return director_names
    
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for line in lines[1:]:  # 헤더 제외
                line = line.strip().strip('"')
                if not line:
                    continue
                if line.startswith(","):
                    line = line[1:]
                parts = [p.strip().strip('"') for p in line.split(",")]
                if len(parts) >= 2:
                    director = parts[1]
                    if director:
                        director_names.append(director)
    except Exception as e:
        print(f"[WARN] CSV 로드 실패: {e}")
    
    return director_names

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="KOBIS에서 감독 정보 수집")
    parser.add_argument("--input_csv", default="data/raw/director_ranking.csv", help="기존 CSV 파일 (감독 이름 목록)")
    parser.add_argument("--output_csv", default="data/raw/director_ranking_kobis.csv", help="출력 CSV 파일")
    parser.add_argument("--directors", nargs="+", help="직접 감독 이름 지정")
    parser.add_argument("--headless", action="store_true", default=True, help="헤드리스 모드")
    parser.add_argument("--limit", type=int, default=None, help="처리할 감독 수 제한")
    
    args = parser.parse_args()
    
    # 감독 이름 목록 가져오기
    if args.directors:
        director_names = args.directors
    else:
        director_names = load_director_names_from_existing_csv(args.input_csv)
    
    if args.limit:
        director_names = director_names[:args.limit]
    
    if not director_names:
        print("[ERROR] 감독 이름 목록이 비어있습니다.")
        exit(1)
    
    print(f"[INFO] {len(director_names)}개 감독 정보 수집 시작")
    print(f"[INFO] 출력 파일: {args.output_csv}")
    print()
    
    scrape_directors_from_kobis(director_names, args.output_csv, headless=args.headless)

