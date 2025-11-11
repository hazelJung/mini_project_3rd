# -*- coding: utf-8 -*-
"""
Day2 인덱싱 엔트리포인트
- 목표: 코퍼스 생성 → 임베딩 → FAISS 저장 + docs.jsonl 저장
- 지원:
  1) 일반 경로 색인 (--paths ...)
  2) 단일 넷플릭스 국가/카테고리 (--netflix_country, --netflix_category)
  3) 복수 넷플릭스 국가/카테고리 (--netflix_countries, --netflix_categories) → 하나의 인덱스에 통합
"""

import os, argparse
from typing import List
from itertools import product

from ..impl.ingest import build_corpus, save_docs_jsonl, build_corpus_netflix
from ..impl.embeddings import Embeddings
from ..impl.store import FaissStore  # 제공됨

def _attach_embed_model(corpus: List[dict], model: str | None) -> List[dict]:
    """각 item.meta에 embedding_model을 주입(추후 스모크에서 자동 판별/검증 용이)."""
    if not model:
        return corpus
    out = []
    for it in corpus:
        meta = dict(it.get("meta", {}))
        meta["embedding_model"] = model
        out.append({**it, "meta": meta})
    return out

def build_index(paths: List[str], index_dir: str, model: str | None = None, batch_size: int = 128):
    # 1) 코퍼스 생성
    corpus = build_corpus(paths)
    if not corpus:
        raise ValueError("build_index: 주어진 경로들에서 문서를 찾지 못했습니다.")

    corpus = _attach_embed_model(corpus, model)

    # 2) 텍스트 추출
    texts = [item["text"] for item in corpus]
    if not texts:
        raise ValueError("build_index: 코퍼스에 text 필드가 비어있습니다.")

    # 3) 임베딩 생성
    emb = Embeddings(model=model, batch_size=batch_size)
    vecs = emb.encode(texts)
    if vecs is None or getattr(vecs, "shape", None) is None or vecs.shape[0] != len(texts):
        raise RuntimeError("build_index: 임베딩 결과가 유효하지 않습니다.")

    # 4) 경로 준비
    os.makedirs(index_dir, exist_ok=True)
    index_path = os.path.join(index_dir, "faiss.index")
    docs_path = os.path.join(index_dir, "docs.jsonl")

    # 5) 저장
    store = FaissStore(dim=vecs.shape[1], index_path=index_path, docs_path=docs_path)
    store.add(vecs, corpus)
    store.save()
    save_docs_jsonl(corpus, docs_path)
    print(f"[OK] Index saved → {index_dir} (N={len(corpus)})")

def build_index_from_netflix(country: str, category: str, index_dir: str,
                             model: str | None = None, batch_size: int = 128):
    corpus = build_corpus_netflix(country, category)
    if not corpus:
        raise ValueError("build_index_from_netflix: 수집된 문서가 없습니다.")

    corpus = _attach_embed_model(corpus, model)
    texts = [it["text"] for it in corpus]

    emb = Embeddings(model=model, batch_size=batch_size)
    vecs = emb.encode(texts)

    os.makedirs(index_dir, exist_ok=True)
    index_path = os.path.join(index_dir, "faiss.index")
    docs_path  = os.path.join(index_dir, "docs.jsonl")

    store = FaissStore(dim=vecs.shape[1], index_path=index_path, docs_path=docs_path)
    store.add(vecs, corpus)
    store.save()
    save_docs_jsonl(corpus, docs_path)
    print(f"[OK] Netflix index saved → {index_dir} (N={len(corpus)})")

def build_index_from_netflix_bulk(countries: List[str], categories: List[str], index_dir: str,
                                  model: str | None = None, batch_size: int = 128):
    """여러 나라×카테고리를 수집해 하나의 인덱스에 저장."""
    all_corpus: List[dict] = []
    for country, category in product(countries, categories):
        cor = build_corpus_netflix(country, category)
        if not cor:
            print(f"[WARN] 빈 코퍼스: {country} / {category}")
            continue
        all_corpus.extend(cor)

    if not all_corpus:
        raise ValueError("build_index_from_netflix_bulk: 수집된 문서가 없습니다.")

    all_corpus = _attach_embed_model(all_corpus, model)
    texts = [it["text"] for it in all_corpus]

    emb = Embeddings(model=model, batch_size=batch_size)
    vecs = emb.encode(texts)

    os.makedirs(index_dir, exist_ok=True)
    index_path = os.path.join(index_dir, "faiss.index")
    docs_path  = os.path.join(index_dir, "docs.jsonl")

    store = FaissStore(dim=vecs.shape[1], index_path=index_path, docs_path=docs_path)
    store.add(vecs, all_corpus)
    store.save()
    save_docs_jsonl(all_corpus, docs_path)
    print(f"[OK] Bulk index saved → {index_dir} (N={len(all_corpus)})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="+", help="일반 문서 경로들")
    ap.add_argument("--index_dir", required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--batch_size", type=int, default=128)

    # 단일
    ap.add_argument("--netflix_country", default=None)
    ap.add_argument("--netflix_category", choices=["Shows", "Movies", "shows", "movies"], default=None)
    # 복수(콤마)
    ap.add_argument("--netflix_countries", default=None, help='예: "South Korea,United States,France,Turkiye,Japan"')
    ap.add_argument("--netflix_categories",  default=None, help='예: "Movies,Shows"')

    args = ap.parse_args()
    os.makedirs(args.index_dir, exist_ok=True)

    if args.netflix_countries and args.netflix_categories:
        countries = [c.strip() for c in args.netflix_countries.split(",") if c.strip()]
        categories = [c.strip() for c in args.netflix_categories.split(",") if c.strip()]
        build_index_from_netflix_bulk(countries, categories, args.index_dir, args.model, args.batch_size)

    elif args.netflix_country and args.netflix_category:
        build_index_from_netflix(
            country=args.netflix_country,
            category=args.netflix_category,
            index_dir=args.index_dir,
            model=args.model,
            batch_size=args.batch_size,
        )

    elif args.paths:
        build_index(args.paths, args.index_dir, args.model, args.batch_size)

    else:
        raise SystemExit("사용법: --paths ... | --netflix_country + --netflix_category | --netflix_countries + --netflix_categories")

    print(f"[DAY2] Index built at: {args.index_dir}")
