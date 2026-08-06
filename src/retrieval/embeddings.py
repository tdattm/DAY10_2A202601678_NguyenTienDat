from __future__ import annotations

from openai import OpenAI
from langchain_core.embeddings import Embeddings


class OpenAITextEmbeddings(Embeddings):
    """OpenAI embedding adapter for Chroma and Ragas."""

    def __init__(self, model_name: str = "text-embedding-3-small", api_key: str | None = None):
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model_name,
            input=[text.replace("\n", " ") for text in texts],
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text.replace("\n", " "),
        )
        return response.data[0].embedding


# Backwards-compatible name for modules or notebooks using the starter API.
MiniLMEmbeddings = OpenAITextEmbeddings
