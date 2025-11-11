# -*- coding: utf-8 -*-
"""
기존 CSV 파일 파싱 테스트 및 KOBIS 스크래핑 필요 여부 확인
"""

import os
import sys

# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_parse_csv():
    """CSV 파일 파싱 테스트"""
    csv_path = os.path.join(project_root, "data", "raw", "director_ranking.csv")
    
    print("=" * 80)
    print("CSV 파일 파싱 테스트")
    print("=" * 80)
    print()
    
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV 파일이 없습니다: {csv_path}")
        return False
    
    director_map = {}
    
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            if not lines:
                print("[ERROR] CSV 파일이 비어있습니다.")
                return False
            
            print(f"총 {len(lines)}줄 (헤더 포함)")
            print()
            
            # 첫 번째 줄은 헤더 (예: ",director,rank1_count")
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
                    director = parts[1] if len(parts) > 1 else None
                    rank1_count_str = parts[2] if len(parts) > 2 else None
                    
                    if director and rank1_count_str:
                        try:
                            rank1_count = int(rank1_count_str.replace(",", "").strip())
                            director_map[director] = rank1_count
                        except ValueError as e:
                            print(f"  [WARN] 줄 {line_num} 파싱 실패: {director} - {e}")
    except Exception as e:
        print(f"[ERROR] CSV 파싱 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"[OK] 파싱 성공: {len(director_map)}개 감독")
    print()
    print("감독 목록 (처음 10개):")
    for i, (director, count) in enumerate(list(director_map.items())[:10], 1):
        print(f"  {i}. {director}: {count}회")
    print()
    
    if len(director_map) > 0:
        print("[SUCCESS] CSV 파일 파싱이 정상적으로 작동합니다!")
        print("         KOBIS 스크래핑 없이 기존 CSV 파일을 사용할 수 있습니다.")
        return True
    else:
        print("[WARN] CSV 파일에서 데이터를 추출하지 못했습니다.")
        print("       KOBIS 스크래핑을 사용해야 합니다.")
        return False

if __name__ == "__main__":
    success = test_parse_csv()
    sys.exit(0 if success else 1)

