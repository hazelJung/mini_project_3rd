# -*- coding: utf-8 -*-
"""
CSV 파일 파싱 테스트
"""

import os
import csv

csv_path = os.path.join("data", "raw", "director_ranking.csv")

print(f"CSV 경로: {csv_path}")
print(f"파일 존재: {os.path.exists(csv_path)}")
print()

director_map = {}

if os.path.exists(csv_path):
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        print("CSV 헤더:", reader.fieldnames)
        print()
        
        for i, row in enumerate(reader, 1):
            print(f"Row {i}: {row}")
            if i >= 5:
                break
        
        # 다시 읽기
        f.seek(0)
        next(reader)  # 헤더 스킵
        
        for row in reader:
            director = None
            rank1_count = None
            
            for key in row.keys():
                if "director" in key.lower():
                    director = row[key].strip().strip('"')
                elif "rank1" in key.lower():
                    rank1_count = row[key].strip().strip('"')
            
            if not director:
                director = row.get("director", "").strip().strip('"')
            if not rank1_count:
                rank1_count = row.get("rank1_count", "").strip().strip('"')
            
            if director and rank1_count:
                try:
                    rank1_count = rank1_count.replace(",", "").strip()
                    director_map[director] = int(rank1_count)
                except ValueError as e:
                    print(f"Error parsing {director}: {e}")

print()
print(f"로드된 감독 수: {len(director_map)}")
print()
print("감독 목록 (처음 10개):")
for i, (director, count) in enumerate(list(director_map.items())[:10], 1):
    print(f"  {i}. {director}: {count}회")

