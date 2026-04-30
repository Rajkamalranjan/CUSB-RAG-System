"""
Advanced RAG Features

Implements advanced techniques:
- Query expansion strategies
- Reranking with cross-encoders
- Semantic caching
- Hybrid retrieval (lexical + semantic)
"""

import sys
from typing import Any

from sentence_transformers import CrossEncoder

from config import (
    ENABLE_QUERY_EXPANSION,
    RERANK_MODEL,
    USE_RERANKER,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class QueryExpander:
    """Expand queries for better retrieval."""

    # Expansion dictionaries for different languages
    HINDI_EXPANSIONS = {
        "सीयूएसबी": "CUSB Central University of South Bihar",
        "प्रवेश": "admission dakhila",
        "दाखिला": "admission entrance",
        "प्रक्रिया": "process steps admission",
        "शुल्क": "fee fees charges",
        "फीस": "fee fees charges",
        "छात्रावास": "hostel accommodation",
        "होस्टल": "hostel accommodation",
        "सुविधा": "facility amenities",
        "सुविधाएं": "facilities amenities",
        "कोर्स": "course degree",
        "पाठ्यक्रम": "course curriculum",
        "योग्यता": "eligibility requirement",
        "परीक्षा": "exam entrance entrance exam",
        "सीयूईटी": "CUET entrance exam national",
    }

    HINGLISH_EXPANSIONS = {
        "kya": "what is",
        "hai": "is",
        "kaise": "how",
        "kitna": "how much",
        "admission": "dakhila entrance",
        "hostel": "छात्रावास accommodation",
        "fee": "शुल्क charges",
    }

    def expand_query(self, query: str, language: str = "auto") -> str:
        """
        Expand query with related terms.

        Args:
            query: Original query
            language: Language type (auto/english/hindi/hinglish)

        Returns:
            Expanded query
        """
        if not ENABLE_QUERY_EXPANSION:
            return query

        # Detect language if auto
        if language == "auto":
            hindi_chars = sum(1 for c in query if "\u0900" <= c <= "\u097f")
            if hindi_chars > 0:
                language = "hinglish" if any(c.isascii() for c in query) else "hindi"
            else:
                language = "english"

        expansions = []

        if language == "hindi":
            for hindi_term, expansion in self.HINDI_EXPANSIONS.items():
                if hindi_term.lower() in query.lower():
                    expansions.append(expansion)

        elif language == "hinglish":
            for hinglish_term, expansion in self.HINGLISH_EXPANSIONS.items():
                if hinglish_term.lower() in query.lower():
                    expansions.append(expansion)

        if expansions:
            return f"{query}\n{' '.join(expansions)}"

        return query

    def generate_related_queries(self, query: str) -> list[str]:
        """
        Generate related query variations.

        Args:
            query: Original query

        Returns:
            List of related queries
        """
        variations = [query]

        # Add related queries
        related_map = {
            "What is CUSB?": [
                "Tell me about CUSB",
                "Information about Central University of South Bihar",
                "CUSB details",
            ],
            "admission": [
                "How to apply?",
                "Application process",
                "How to get admitted?",
                "Admission steps",
            ],
            "fee": [
                "Cost of admission",
                "How much does it cost?",
                "Tuition fees",
                "Charges",
            ],
        }

        for key, related in related_map.items():
            if key.lower() in query.lower():
                variations.extend(related)

        return list(set(variations))


class Reranker:
    """Rerank retrieved documents using cross-encoder."""

    def __init__(self, model_name: str = RERANK_MODEL):
        if not USE_RERANKER:
            self.model = None
            return

        try:
            self.model = CrossEncoder(model_name)
            print(f"✅ Reranker initialized: {model_name}")
        except Exception as e:
            print(f"⚠️  Failed to load reranker: {e}")
            self.model = None

    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Rerank documents using cross-encoder.

        Args:
            query: Query string
            documents: List of documents with 'text' field
            top_k: Number of top documents to return

        Returns:
            Reranked documents
        """
        if self.model is None or not USE_RERANKER:
            return documents[:top_k]

        try:
            # Extract texts
            texts = [doc.get("text", "") for doc in documents]

            # Score documents
            scores = self.model.predict([[query, text] for text in texts])

            # Sort by score
            ranked = sorted(
                zip(documents, scores),
                key=lambda x: x[1],
                reverse=True
            )

            # Update document scores and return top-k
            result = []
            for doc, score in ranked[:top_k]:
                doc["rerank_score"] = float(score)
                result.append(doc)

            return result

        except Exception as e:
            print(f"⚠️  Reranking error: {e}")
            return documents[:top_k]


class SemanticCache:
    """Simple semantic caching for repeated queries."""

    def __init__(self, max_cache_size: int = 1000):
        self.cache = {}
        self.max_cache_size = max_cache_size

    def get(self, query: str) -> Any | None:
        """Get cached result."""
        return self.cache.get(query.lower(), None)

    def set(self, query: str, result: Any) -> None:
        """Set cache entry."""
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry
            self.cache.pop(next(iter(self.cache)))

        self.cache[query.lower()] = result

    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()


class HybridRetriever:
    """Hybrid retrieval combining lexical and semantic search."""

    def __init__(self, semantic_weight: float = 0.7):
        """
        Initialize hybrid retriever.

        Args:
            semantic_weight: Weight for semantic score (0-1)
        """
        self.semantic_weight = semantic_weight
        self.lexical_weight = 1.0 - semantic_weight

    def combine_scores(
        self,
        semantic_scores: list[float],
        lexical_scores: list[float]
    ) -> list[float]:
        """
        Combine semantic and lexical scores.

        Args:
            semantic_scores: Semantic similarity scores
            lexical_scores: Lexical (BM25) scores

        Returns:
            Combined scores
        """
        # Normalize scores to 0-1 range
        if semantic_scores:
            sem_min, sem_max = min(semantic_scores), max(semantic_scores)
            sem_range = sem_max - sem_min if sem_max > sem_min else 1
            sem_normalized = [
                (s - sem_min) / sem_range for s in semantic_scores
            ]
        else:
            sem_normalized = [0] * len(lexical_scores)

        if lexical_scores:
            lex_min, lex_max = min(lexical_scores), max(lexical_scores)
            lex_range = lex_max - lex_min if lex_max > lex_min else 1
            lex_normalized = [
                (s - lex_min) / lex_range for s in lexical_scores
            ]
        else:
            lex_normalized = [0] * len(semantic_scores)

        # Combine
        combined = [
            s * self.semantic_weight + l * self.lexical_weight
            for s, l in zip(sem_normalized, lex_normalized)
        ]

        return combined


def main():
    """Test advanced features."""
    print("\n📚 Advanced RAG Features")
    print("=" * 80)

    # Test query expander
    print("\n🔍 Query Expansion:")
    expander = QueryExpander()

    test_queries = [
        "सीयूएसबी क्या है?",
        "What is the admission process?",
        "CUSB me hostel fee kya hai?",
    ]

    for query in test_queries:
        expanded = expander.expand_query(query)
        if expanded != query:
            print(f"  Original:  {query}")
            print(f"  Expanded:  {expanded}")
            print()

    # Test reranker
    if USE_RERANKER:
        print("\n🎯 Reranking:")
        reranker = Reranker()
        sample_docs = [
            {"id": 1, "text": "CUSB is a central university in Bihar"},
            {"id": 2, "text": "The admission process involves CUET entrance exam"},
            {"id": 3, "text": "The hostel fee is ₹9,000 per semester"},
        ]
        reranked = reranker.rerank("What is CUSB?", sample_docs, top_k=2)
        for doc in reranked:
            print(f"  {doc['id']}: {doc['text'][:50]}... (score: {doc.get('rerank_score', 'N/A')})")

    # Test cache
    print("\n💾 Semantic Cache:")
    cache = SemanticCache()
    cache.set("What is CUSB?", "CUSB is a central university...")
    print(f"  Cached: {cache.get('What is CUSB?')[:30]}...")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
