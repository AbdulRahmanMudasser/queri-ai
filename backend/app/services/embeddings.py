import asyncio
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings


class EmbeddingsProvider(ABC):
    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        pass


class LocalEmbeddings(EmbeddingsProvider):
    def __init__(self) -> None:
        self._model: Any = None

    def _init_model(self) -> None:
        if self._model is None:
            # Lazy import to avoid slowing down API startup time
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

    async def get_embedding(self, text: str) -> list[float]:
        self._init_model()

        # TextEmbedding.embed is CPU-bound and synchronous, run in thread pool
        def run() -> list[float]:
            return [float(x) for x in list(self._model.embed([text]))[0]]

        return await asyncio.to_thread(run)


class GeminiEmbeddings(EmbeddingsProvider):
    async def get_embedding(self, text: str) -> list[float]:
        import google.generativeai as genai

        # Ensure genai is configured before making async call
        genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
        response = await genai.embed_content_async(  # type: ignore[attr-defined]
            model="models/gemini-embedding-2",
            content=text,
        )
        return [float(x) for x in response["embedding"]]


def get_embeddings_provider() -> EmbeddingsProvider:
    if settings.EMBEDDING_PROVIDER == "gemini":
        return GeminiEmbeddings()
    return LocalEmbeddings()
