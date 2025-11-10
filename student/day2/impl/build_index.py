# -*- coding: utf-8 -*-
"""
Day2 인덱싱 엔트리포인트
- 목표: 코퍼스 생성 → 임베딩 → FAISS 저장 + docs.jsonl 저장
"""

import os, argparse, numpy as np
from typing import List

from student.day2.impl.ingest import build_corpus, save_docs_jsonl
from student.day2.impl.embeddings import Embeddings
from student.day2.impl.store import FaissStore  # 제공됨


def build_index(paths: List[str], index_dir: str, model: str | None = None, batch_size: int = 128):
    """
    절차:
      1) corpus = build_corpus(paths)
         - [{"id":..., "text":..., "meta":{...}}, ...]
      2) texts = [item["text"] for item in corpus]
      3) emb = Embeddings(model=model, batch_size=batch_size)
         vecs = emb.encode(texts)  # (N, D) L2 정규화된 np.ndarray
      4) index_path = os.path.join(index_dir, "faiss.index")
         docs_path  = os.path.join(index_dir, "docs.jsonl")
      5) store = FaissStore(dim=vecs.shape[1], index_path=index_path, docs_path=docs_path)
         store.add(vecs, corpus); store.save()
      6) save_docs_jsonl(corpus, docs_path)
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY2-I-01] 구현
    # ----------------------------------------------------------------------------
    # 1) 코퍼스 생성
    corpus = build_corpus(paths)
    if not corpus:
        raise ValueError("build_index: 비어있는 코퍼스입니다. 경로/파일을 확인하세요.")

    # 2) 텍스트 목록
    texts = [item.get("text", "") for item in corpus]
    if any(not isinstance(t, str) for t in texts):
        raise TypeError("build_index: corpus 항목의 'text'는 문자열이어야 합니다.")

    # 3) 임베딩
    emb = Embeddings(model=model, batch_size=batch_size)
    vecs = emb.encode(texts)  # (N, D)
    if vecs is None or not isinstance(vecs, np.ndarray) or vecs.ndim != 2:
        raise RuntimeError("build_index: 임베딩 결과가 유효한 2D ndarray가 아닙니다.")
    if vecs.shape[0] != len(corpus):
        raise RuntimeError(f"build_index: 임베딩 수({vecs.shape[0]})와 코퍼스 수({len(corpus)})가 다릅니다.")

    # 4) 경로
    # os.makedirs(index_dir, exist_ok=True)
    index_path = os.path.join(index_dir, "faiss.index")
    docs_path  = os.path.join(index_dir, "docs.jsonl")

    # 5) FAISS 저장
    store = FaissStore(dim=vecs.shape[1], index_path=index_path, docs_path=docs_path)
    store.add(vecs, corpus)
    store.save()

    # 6) 문서 메타 JSONL 저장
    save_docs_jsonl(corpus, docs_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="+", required=True, help="인덱싱할 파일/디렉터리 경로(여러 개 가능)")
    ap.add_argument("--index_dir", default="indices/day2", help="FAISS 인덱스 및 docs.jsonl 저장 경로")
    ap.add_argument("--model", default=None, help="임베딩 모델 (기본값: Embeddings 내부 기본값)")
    ap.add_argument("--batch_size", type=int, default=128, help="임베딩 배치 크기")
    args = ap.parse_args()

    # ----------------------------------------------------------------------------
    # TODO[DAY2-I-02] 구현
    # ----------------------------------------------------------------------------
    os.makedirs(args.index_dir, exist_ok=True)
    build_index(args.paths, args.index_dir, args.model, args.batch_size)
