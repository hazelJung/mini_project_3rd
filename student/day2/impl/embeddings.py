# -*- coding: utf-8 -*-
"""
OpenAI 임베딩 래퍼
- 배치 인코딩, 재시도(backoff), L2 정규화
- 퍼블릭 OpenAI / Azure OpenAI / 커스텀 base_url 자동 감지
"""

import os, time
from typing import List
import numpy as np
from dotenv import load_dotenv

from openai import OpenAI
try:
    from openai import AzureOpenAI
except Exception:
    AzureOpenAI = None

DEFAULT_DIM = 1536  # text-embedding-3-* 기본 차원

class Embeddings:
    def __init__(self, model: str | None = None, batch_size: int = 128, max_retries: int = 4):
        load_dotenv()
        # 모델명 방어적 정리 (공백/따옴표/백틱 제거)
        self.model = (model or "text-embedding-3-small").strip().strip('`"')
        self.batch_size = int(batch_size)
        self.max_retries = int(max_retries)

        api_key = os.getenv("OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or api_key
        azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")

        if azure_endpoint:
            if AzureOpenAI is None:
                raise RuntimeError("AzureOpenAI 사용 불가: `pip install -U openai`로 v1 SDK 업데이트 필요")
            if not azure_api_key:
                raise RuntimeError("AZURE_OPENAI_API_KEY 또는 OPENAI_API_KEY가 필요합니다.")
            self.client = AzureOpenAI(
                api_key=azure_api_key,
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint,
            )
            self.provider = "azure"
            # 주의: Azure에서는 self.model에 '배포이름(deployment name)'이 와야 함
        else:
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
            # 커스텀/프록시 엔드포인트 지원
            self.client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
            self.provider = f"openai{f'(base_url={base_url})' if base_url else ''}"

        print(f"[Embeddings] provider={self.provider}, model={self.model}, batch_size={self.batch_size}")

    def _embed_once(self, text: str) -> np.ndarray:
        try:
            resp = self.client.embeddings.create(model=self.model, input=text)
        except Exception as e:
            raise RuntimeError(f"Embeddings API 호출 실패 (provider={self.provider}, model={self.model}): {e}")
        vec = np.array(resp.data[0].embedding, dtype="float32")
        norm = np.linalg.norm(vec) + 1e-12
        return vec / norm

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, DEFAULT_DIM), dtype="float32")

        out: list[np.ndarray] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            for each in batch:
                for attempt in range(self.max_retries):
                    try:
                        out.append(self._embed_once(each))
                        break
                    except Exception:
                        time.sleep(0.5 * (2 ** attempt))  # 0.5s,1s,2s,4s
                        if attempt == self.max_retries - 1:
                            raise
        return np.vstack(out) if out else np.zeros((0, DEFAULT_DIM), dtype="float32")
