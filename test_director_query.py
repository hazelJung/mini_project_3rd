# -*- coding: utf-8 -*-
"""
감독 조회 기능 테스트
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from student.day2.agent import _load_director_csv, _find_director_in_query, _handle_director_query

def test_load_csv():
    """CSV 파일 로드 테스트"""
    csv_path = os.path.join(project_root, "data", "raw", "director_ranking.csv")
    print(f"CSV 경로: {csv_path}")
    print(f"파일 존재: {os.path.exists(csv_path)}")
    print()
    
    director_map = _load_director_csv(csv_path)
    print(f"로드된 감독 수: {len(director_map)}")
    print()
    
    # 처음 10개 감독 출력
    print("감독 목록 (처음 10개):")
    for i, (director, count) in enumerate(list(director_map.items())[:10], 1):
        print(f"  {i}. {director}: {count}회")
    print()
    
    return director_map

def test_find_director():
    """감독 찾기 테스트"""
    csv_path = os.path.join(project_root, "data", "raw", "director_ranking.csv")
    director_map = _load_director_csv(csv_path)
    
    test_queries = [
        "봉준호",
        "봉준호 감독",
        "김한민 감독 1위 횟수",
        "최동훈",
        "브래드 버드",
        "존 도우",
    ]
    
    print("감독 찾기 테스트:")
    print("-" * 80)
    for query in test_queries:
        result = _find_director_in_query(query, director_map)
        if result:
            director, count = result
            print(f"✓ '{query}' -> {director} ({count}회)")
        else:
            print(f"✗ '{query}' -> 찾을 수 없음")
    print()

def test_handle_director_query():
    """감독 조회 처리 테스트"""
    csv_path = os.path.join(project_root, "data", "raw", "director_ranking.csv")
    
    test_queries = [
        "봉준호 감독",
        "김한민 감독 1위 횟수",
        "최동훈",
        "존 도우 감독",
    ]
    
    print("감독 조회 처리 테스트:")
    print("-" * 80)
    for query in test_queries:
        result = _handle_director_query(query, csv_path)
        print(f"\n질의: {query}")
        print(f"결과: {result}")
        if result.get("found"):
            print(f"  ✓ {result.get('message')}")
        else:
            print(f"  ✗ {result.get('error')}")
    print()

if __name__ == "__main__":
    print("=" * 80)
    print("감독 조회 기능 테스트")
    print("=" * 80)
    print()
    
    # CSV 로드 테스트
    director_map = test_load_csv()
    
    # 감독 찾기 테스트
    test_find_director()
    
    # 감독 조회 처리 테스트
    test_handle_director_query()
    
    print("=" * 80)
    print("테스트 완료")
    print("=" * 80)

