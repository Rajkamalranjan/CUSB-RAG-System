"""Qdrant collection manager and loader."""

from __future__ import annotations

import os
from typing import Any


class QdrantVectorStore:
    def __init__(self, collection_name: str | None = None, url: str | None = None, path: str | None = None):
        from qdrant_client import QdrantClient

        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "cusb_chunks")
        local_path = path or os.getenv("QDRANT_PATH")
        if local_path:
            self.client = QdrantClient(path=local_path)
        else:
            self.client = QdrantClient(url=url or os.getenv("QDRANT_URL", "http://localhost:6333"))

    def ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        existing = {collection.name for collection in self.client.get_collections().collections}
        if self.collection_name in existing:
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert(self, ids: list[int], vectors: list[list[float]], payloads: list[dict[str, Any]]) -> None:
        from qdrant_client.models import PointStruct

        if vectors:
            self.ensure_collection(len(vectors[0]))
        points = [
            PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            close()

    def delete_by_source(self, source_file: str) -> dict[str, Any]:
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        query_filter = Filter(
            must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]
        )
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(filter=query_filter),
        )
        return {"collection": self.collection_name, "source_file": source_file}

    def search(self, vector: list[float], top_k: int = 20, filters: dict[str, Any] | None = None) -> list[dict]:
        query_filter = None
        if filters:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_filter = Filter(
                must=[FieldCondition(key=key, match=MatchValue(value=value)) for key, value in filters.items()]
            )
        if hasattr(self.client, "search"):
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        else:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
            hits = response.points
        return [
            {
                "id": hit.id,
                "score": float(hit.score),
                **(hit.payload or {}),
            }
            for hit in hits
        ]
