"""Download/load the configured BGE reranker and run a tiny smoke test."""

from __future__ import annotations

from reranker.bge_reranker import BGEReranker


def main() -> None:
    reranker = BGEReranker()
    docs = [
        {"id": 1, "text": "CUSB hostel facility includes mess and accommodation details."},
        {"id": 2, "text": "Central University of South Bihar is located in Gaya."},
    ]
    results = reranker.rerank("hostel mess facility", docs, top_k=2)
    print(results)


if __name__ == "__main__":
    main()

