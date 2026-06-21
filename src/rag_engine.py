"""
Core RAG retrieval and generation engine.

This module can be used by the CLI chatbot or imported into a web/API app.
"""

import os
import pickle
import re
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (
    CHUNKS_PATH,
    EMBED_MODEL,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    INDEX_PATH,
    LLM_PROVIDER,
    MAX_CONTEXT,
    RERANK_MODEL,
    RETRIEVAL_CANDIDATES,
    USE_RERANKER,
    TOP_K,
    CHATBOT_MODEL,
    BENCHMARK_MODEL,
    VECTOR_BACKEND,
    QDRANT_URL,
    QDRANT_PATH,
    QDRANT_COLLECTION,
)


TOKEN_PATTERN = re.compile(r"[\w]+", flags=re.UNICODE)


def tokenize_for_sparse(text: str) -> list[str]:
    """Small shared tokenizer for BM25 sparse retrieval."""
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


def detect_query_language(query: str) -> str:
    """Detect whether the user asked in English, Hindi, or Hinglish."""
    hindi_chars = sum(1 for char in query if "\u0900" <= char <= "\u097f")
    latin_chars = sum(1 for char in query if char.isascii() and char.isalpha())

    if hindi_chars and hindi_chars >= latin_chars:
        return "Hindi"

    hinglish_markers = {
        "kya", "hai", "hain", "ka", "ki", "ke", "mein", "kaha", "kitna",
        "kitni", "kaise", "batao", "chahiye", "hota", "hoti", "karo", "mujhe",
    }
    words = {word.strip(".,?!:;()[]{}").lower() for word in query.split()}
    matched_markers = words & hinglish_markers

    if hindi_chars and latin_chars:
        return "Hinglish"
    if matched_markers:
        return "Hinglish"
    return "English"


def expand_query_for_retrieval(query: str) -> str:
    """Add English/Hinglish hints for common Hindi university query terms."""
    expansions = {
        "सीयूएसबी": "CUSB Central University of South Bihar",
        "प्रवेश": "admission",
        "दाखिला": "admission",
        "प्रक्रिया": "process steps admission steps merit list document verification provisional admission",
        "शुल्क": "fee fees",
        "फीस": "fee fees",
        "छात्रावास": "hostel",
        "होस्टल": "hostel",
        "सुविधा": "facility facilities",
        "सुविधाएं": "facility facilities",
        "कोर्स": "course courses",
        "पाठ्यक्रम": "course courses",
        "योग्यता": "eligibility",
        "परीक्षा": "exam entrance CUET",
        "सीयूईटी": "CUET entrance exam",
    }

    extra_terms = [value for key, value in expansions.items() if key in query]
    if not extra_terms:
        return query
    return f"{query}\n{' '.join(extra_terms)}"


class Retriever:
    """Loads the FAISS index and retrieves relevant chunks for a query."""

    def __init__(self):
        self._check_files()
        import faiss
        from sentence_transformers import SentenceTransformer

        with open(CHUNKS_PATH, "rb") as f:
            self.chunks: list[dict] = pickle.load(f)

        self.index = faiss.read_index(str(INDEX_PATH))
        self.model = SentenceTransformer(EMBED_MODEL)
        self.bm25 = None
        self.use_bm25 = os.getenv("USE_BM25_HYBRID", "true").lower() in {"1", "true", "yes"}
        if self.use_bm25:
            try:
                from rank_bm25 import BM25Okapi

                corpus_tokens = [
                    tokenize_for_sparse(f"{chunk.get('heading', '')} {chunk.get('text', '')}")
                    for chunk in self.chunks
                ]
                self.bm25 = BM25Okapi(corpus_tokens)
            except Exception as exc:
                print(f"BM25 disabled: {str(exc).splitlines()[0]}")
                self.use_bm25 = False
        self.reranker = None
        if USE_RERANKER:
            from sentence_transformers import CrossEncoder

            self.reranker = CrossEncoder(RERANK_MODEL)

        if len(self.chunks) != self.index.ntotal:
            raise ValueError(
                f"Chunk/vector mismatch: {len(self.chunks)} chunks but "
                f"{self.index.ntotal} vectors. Rebuild Step 1 and Step 2."
            )

        rerank_status = f", reranker={RERANK_MODEL}" if self.reranker else ""
        print(f"✅  Retriever ready — {len(self.chunks)} chunks, {self.index.ntotal} vectors{rerank_status}")

    def _check_files(self):
        missing = []
        if not CHUNKS_PATH.exists():
            missing.append(str(CHUNKS_PATH))
        if not INDEX_PATH.exists():
            missing.append(str(INDEX_PATH))
        if missing:
            raise FileNotFoundError(
                "❌  Required files missing:\n"
                + "\n".join(f"   • {p}" for p in missing)
                + "\n\nRun steps 1 and 2 first:\n"
                "   python src/1_build_chunks.py\n"
                "   python src/2_build_vectordb.py"
            )

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Return top_k most relevant chunks for the query."""
        retrieval_query = expand_query_for_retrieval(query)
        q_vec = self.model.encode(
            [retrieval_query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        candidate_k = min(max(top_k * 5, RETRIEVAL_CANDIDATES), self.index.ntotal)
        scores, indices = self.index.search(q_vec, k=candidate_k)

        query_terms = {
            token
            for token in re.findall(r"[\w]+", retrieval_query.lower(), flags=re.UNICODE)
            if len(token) > 2
        }

        results_by_id = {}
        for dense_rank, (idx, score) in enumerate(zip(indices[0], scores[0]), 1):
            if idx == -1:
                continue
            chunk = self.chunks[idx].copy()
            haystack = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
            heading = chunk.get("heading", "").lower()
            matched_terms = {term for term in query_terms if term in haystack}
            heading_matches = {term for term in query_terms if term in heading}
            lexical_bonus = min(0.20, 0.025 * len(matched_terms) + 0.025 * len(heading_matches))
            quality_bonus = self._domain_quality_bonus(retrieval_query, chunk)
            rrf_bonus = 1.0 / (60 + dense_rank)
            chunk["vector_score"] = float(score)
            chunk["dense_rank"] = int(dense_rank)
            chunk["rrf_bonus"] = float(rrf_bonus)
            chunk["lexical_bonus"] = float(lexical_bonus)
            chunk["quality_bonus"] = float(quality_bonus)
            chunk["score"] = float(score + lexical_bonus + quality_bonus + rrf_bonus)
            results_by_id[idx] = chunk

        if self.bm25:
            bm25_scores = self.bm25.get_scores(tokenize_for_sparse(retrieval_query))
            bm25_top_k = min(max(candidate_k, 50), len(self.chunks))
            bm25_ranked = sorted(enumerate(bm25_scores), key=lambda pair: pair[1], reverse=True)[:bm25_top_k]
            max_bm25 = max((score for _, score in bm25_ranked), default=0.0) or 1.0
            for bm25_rank, (idx, bm25_score) in enumerate(bm25_ranked, 1):
                if bm25_score <= 0:
                    continue
                bm25_bonus = 0.35 * (float(bm25_score) / float(max_bm25))
                rrf_bonus = 1.0 / (60 + bm25_rank)
                if idx in results_by_id:
                    results_by_id[idx]["bm25_score"] = float(bm25_score)
                    results_by_id[idx]["bm25_rank"] = int(bm25_rank)
                    results_by_id[idx]["bm25_bonus"] = max(
                        float(results_by_id[idx].get("bm25_bonus", 0.0)),
                        float(bm25_bonus),
                    )
                    results_by_id[idx]["rrf_bonus"] = float(results_by_id[idx].get("rrf_bonus", 0.0)) + rrf_bonus
                    results_by_id[idx]["score"] = (
                        results_by_id[idx].get("vector_score", 0.0)
                        + results_by_id[idx].get("lexical_bonus", 0.0)
                        + results_by_id[idx].get("quality_bonus", 0.0)
                        + results_by_id[idx].get("bm25_bonus", 0.0)
                        + results_by_id[idx].get("rrf_bonus", 0.0)
                    )
                    continue

                chunk = self.chunks[idx].copy()
                haystack = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
                heading = chunk.get("heading", "").lower()
                matched_terms = {term for term in query_terms if term in haystack}
                heading_matches = {term for term in query_terms if term in heading}
                lexical_bonus = min(0.45, 0.05 * len(matched_terms) + 0.05 * len(heading_matches))
                quality_bonus = self._domain_quality_bonus(retrieval_query, chunk)
                chunk["vector_score"] = 0.0
                chunk["bm25_score"] = float(bm25_score)
                chunk["bm25_rank"] = int(bm25_rank)
                chunk["bm25_bonus"] = float(bm25_bonus)
                chunk["rrf_bonus"] = float(rrf_bonus)
                chunk["lexical_bonus"] = float(lexical_bonus)
                chunk["quality_bonus"] = float(quality_bonus)
                chunk["score"] = float(lexical_bonus + quality_bonus + bm25_bonus + rrf_bonus)
                results_by_id[idx] = chunk

        for idx, original_chunk in enumerate(self.chunks):
            haystack = f"{original_chunk.get('heading', '')} {original_chunk.get('text', '')}".lower()
            heading = original_chunk.get("heading", "").lower()
            matched_terms = {term for term in query_terms if term in haystack}
            heading_matches = {term for term in query_terms if term in heading}
            if not matched_terms:
                continue

            lexical_bonus = min(0.45, 0.05 * len(matched_terms) + 0.05 * len(heading_matches))
            if idx in results_by_id:
                results_by_id[idx]["lexical_bonus"] = max(
                    results_by_id[idx]["lexical_bonus"],
                    float(lexical_bonus),
                )
                results_by_id[idx]["quality_bonus"] = self._domain_quality_bonus(
                    retrieval_query,
                    results_by_id[idx],
                )
                results_by_id[idx]["score"] = (
                    results_by_id[idx]["vector_score"]
                    + results_by_id[idx]["lexical_bonus"]
                    + results_by_id[idx]["quality_bonus"]
                    + results_by_id[idx].get("bm25_bonus", 0.0)
                    + results_by_id[idx].get("rrf_bonus", 0.0)
                )
                continue

            chunk = original_chunk.copy()
            quality_bonus = self._domain_quality_bonus(retrieval_query, chunk)
            chunk["vector_score"] = 0.0
            chunk["lexical_bonus"] = float(lexical_bonus)
            chunk["quality_bonus"] = float(quality_bonus)
            chunk["score"] = float(lexical_bonus + quality_bonus)
            results_by_id[idx] = chunk

        results = list(results_by_id.values())
        results.sort(key=lambda item: item["score"], reverse=True)
        candidates = self._diversify_by_heading(results, top_k=candidate_k)
        return self._rerank(query, candidates, top_k=top_k)

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        """Compatibility alias used by research/advanced modules."""
        return self.retrieve(query, top_k=k)

    def _rerank(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        """Optionally rerank candidates with a cross-encoder."""
        if not self.reranker or not chunks:
            return self._diversify_by_heading(chunks, top_k=top_k)

        pairs = [[query, chunk["text"][:1200]] for chunk in chunks]
        rerank_scores = self.reranker.predict(pairs)
        reranked = []
        for chunk, rerank_score in zip(chunks, rerank_scores):
            updated = chunk.copy()
            updated["pre_rerank_score"] = updated["score"]
            updated["rerank_score"] = float(rerank_score)
            updated["score"] = float(
                rerank_score
                + updated.get("quality_bonus", 0.0)
                + (0.25 * updated.get("lexical_bonus", 0.0))
            )
            reranked.append(updated)

        reranked.sort(key=lambda item: item["score"], reverse=True)
        return self._diversify_by_heading(reranked, top_k=top_k)

    def _diversify_by_heading(self, chunks: list[dict], top_k: int) -> list[dict]:
        """Keep repeated chunk headings useful without letting one document fill all slots."""
        selected = []
        heading_counts = {}
        max_per_heading = 3

        for chunk in chunks:
            heading = str(chunk.get("heading", "Untitled")).strip().lower()
            count = heading_counts.get(heading, 0)
            if count >= max_per_heading:
                continue
            selected.append(chunk)
            heading_counts[heading] = count + 1
            if len(selected) >= top_k:
                return selected

        return selected

    def _meaningful_words(self, value: str) -> set[str]:
        """Words useful for matching a user query to a department/program chunk."""
        value = (
            value.lower()
            .replace("m.sc.", "msc")
            .replace("m.sc", "msc")
            .replace("b.sc.", "bsc")
            .replace("b.sc", "bsc")
            .replace("m.a.", "ma")
            .replace("m.a", "ma")
            .replace("b.a.", "ba")
            .replace("b.a", "ba")
            .replace("ph.d.", "phd")
            .replace("ph.d", "phd")
        )
        stopwords = {
            "cusb", "central", "university", "south", "bihar", "department", "dept",
            "school", "faculty", "course", "courses", "programme", "programmes",
            "program", "programs", "syllabus", "structure", "about", "baare",
            "batao", "kya", "hai", "hain", "mein", "me", "ke", "ka", "ki", "aur",
            "and", "or", "of", "the", "in", "for", "with", "master", "bachelor",
            "tell", "give", "full", "please", "show", "provide",
            "information", "details", "detail",
            "what", "which", "who", "where", "when", "how", "is", "are", "does", "do",
            "available", "list",
        }
        words = set()
        for word in re.findall(r"[\w]+", value, flags=re.UNICODE):
            if len(word) <= 2 or word in stopwords:
                continue
            words.add(word)
        return words

    def _matches_department(self, query_lower: str, department: str) -> bool:
        if not department:
            return False
        department_lower = department.lower().replace("department of ", "")
        if department_lower and department_lower in query_lower:
            return True
        dept_words = self._meaningful_words(department_lower)
        query_words = self._meaningful_words(query_lower)
        return bool(dept_words and dept_words.issubset(query_words))

    def _specific_query_overlap(self, query_lower: str, haystack: str) -> int:
        query_words = self._meaningful_words(query_lower)
        haystack_words = self._meaningful_words(haystack)
        return len(query_words & haystack_words)

    def _focus_words(self, query_lower: str) -> set[str]:
        """Subject/program words that should stay present for a specific query."""
        degree_words = {
            "msc", "bsc", "phd", "mpharm", "mcom", "med", "mped", "llb",
            "integrated", "honours", "hons", "semester", "year", "years",
        }
        return self._meaningful_words(query_lower) - degree_words

    def _domain_quality_bonus(self, query: str, chunk: dict) -> float:
        """Prefer concrete CUSB fee/facility facts over vague QA snippets."""
        query_lower = query.lower()
        text = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
        heading = str(chunk.get("heading", "")).lower()
        normalized_query = (
            query_lower.replace("m.sc.", "msc").replace("m.sc", "msc")
            .replace("b.sc.", "bsc").replace("b.sc", "bsc")
            .replace("m.a.", "ma").replace("m.a", "ma")
            .replace("b.a.", "ba").replace("b.a", "ba")
            .replace("ph.d.", "phd").replace("ph.d", "phd")
        )
        normalized_text = (
            text.replace("m.sc.", "msc").replace("m.sc", "msc")
            .replace("b.sc.", "bsc").replace("b.sc", "bsc")
            .replace("m.a.", "ma").replace("m.a", "ma")
            .replace("b.a.", "ba").replace("b.a", "ba")
            .replace("ph.d.", "phd").replace("ph.d", "phd")
        )
        normalized_heading = (
            heading.replace("m.sc.", "msc").replace("m.sc", "msc")
            .replace("b.sc.", "bsc").replace("b.sc", "bsc")
            .replace("m.a.", "ma").replace("m.a", "ma")
            .replace("b.a.", "ba").replace("b.a", "ba")
            .replace("ph.d.", "phd").replace("ph.d", "phd")
        )
        record_type = str(chunk.get("record_type", "")).lower()
        chunk_kind = str(chunk.get("chunk_kind", "")).lower()
        department = str(chunk.get("department", "")).lower()
        source_file = str(chunk.get("source_file", "")).lower()
        department_match = self._matches_department(normalized_query, department)
        content_overlap = self._specific_query_overlap(normalized_query, normalized_text)
        focus_words = self._focus_words(normalized_query)
        text_words = self._meaningful_words(normalized_text)
        heading_words = self._meaningful_words(normalized_heading)
        focus_in_text = len(focus_words & text_words)
        focus_in_heading = len(focus_words & heading_words)
        focus_complete_in_heading = bool(focus_words and focus_words.issubset(heading_words))
        focus_complete_in_text = bool(focus_words and focus_words.issubset(text_words))
        generic_heading_words = {
            "msc", "bsc", "phd", "ma", "ba", "ug", "pg", "integrated",
            "manual", "complete", "content", "extracted", "current", "pdfs",
            "pdf", "course", "structure", "department",
        }
        heading_specific_words = heading_words - generic_heading_words
        wrong_specific_syllabus_heading = bool(
            focus_words
            and "syllabus" in heading
            and focus_in_heading == 0
            and heading_specific_words
        )
        bonus = 0.0

        asks_hostel_fee = "hostel" in query_lower and any(
            term in query_lower for term in ("fee", "fees", "फीस", "शुल्क")
        )
        if asks_hostel_fee:
            if "hostel fee |" in text or "hostel ka fee per semester" in text:
                bonus += 0.45
            if "₹ 9,000" in text or "₹9,000" in text:
                bonus += 0.35
            if "estimated annual hostel expense" in text or "annual hostel expense" in text:
                bonus += 0.15
            if "mess charges" in text and "₹ 3,000" in text:
                bonus += 0.10
            if "fees vary" in text and "₹" not in text:
                bonus -= 0.35

        asks_about_cusb = any(
            phrase in query_lower
            for phrase in ("what is cusb", "cusb kya hai", "about cusb")
        )
        if asks_about_cusb:
            if "complete knowledge base" in heading or "central university of south bihar" in heading:
                bonus += 0.35
            if "established" in text and "central universities act" in text:
                bonus += 0.30
            if "ordinance" in heading or "ph.d" in heading or "phd" in heading:
                bonus -= 0.35

        asks_fee = any(term in query_lower for term in ("fee", "fees", "फीस", "शुल्क"))
        if asks_fee and "₹" in text:
            bonus += 0.05
        asks_general_programme_fee = asks_fee and not any(
            term in query_lower for term in ("semester", "sem", "3rd", "5th", "7th", "9th")
        )
        if asks_general_programme_fee:
            if "complete fee structure" in heading or "course-wise fee structure" in text:
                bonus += 0.55
            if "total fees (approx.)" in text and "per semester" in text:
                bonus += 0.35
            if "vidyarthi mediclaim premium optional" in text or "3rd / 5th / 7th / 9th semester" in text:
                bonus -= 0.35
        asks_admission_total_fee = "admission" in query_lower and asks_fee and any(
            term in query_lower for term in ("total", "kitni", "कितनी")
        )
        if asks_admission_total_fee:
            if "complete fee structure" in heading or "admission_fee_department" in heading:
                bonus += 0.45
            if "educational/adventure/leadership" in text or "m.p.ed" in text:
                bonus -= 0.75
            if "research pdf corpus" in heading:
                bonus -= 0.65

        asks_admission_process = "admission" in query_lower and any(
            term in query_lower for term in ("process", "steps", "प्रवेश", "प्रक्रिया")
        )
        if asks_admission_process:
            if "admission steps" in text:
                bonus += 0.45
            if "apply for cuet" in text and "document verification" in text:
                bonus += 0.35
            if "merit list" in text and "cut-off" in text:
                bonus += 0.20
            if "mode of admission" in text and len(text) < 80:
                bonus -= 0.15
            if "प्रवेश प्रक्रिया (admission process)" in text and len(text) < 120:
                bonus -= 0.35

        asks_ug_eligibility = "ug" in query_lower and any(
            term in query_lower for term in ("eligibility", "योग्यता")
        )
        if asks_ug_eligibility:
            if "admission notification (ug" in heading or "ug 2026" in heading or (
                "ug" in heading and ("admission" in heading or "bulletin" in heading or "cuet" in heading)
            ):
                bonus += 0.70
            if "admission notification (pg" in heading or "pg 2026" in heading:
                bonus -= 0.55
            if "undergraduate" in text or "ug programme" in text:
                bonus += 0.25
            if "syllabus" in heading:
                bonus -= 0.45

        asks_pg_eligibility = "pg" in query_lower and any(
            term in query_lower for term in ("eligibility", "योग्यता")
        )
        if asks_pg_eligibility:
            if "admission notification (pg" in heading or "pg 2026" in heading or (
                "pg" in heading and ("admission" in heading or "bulletin" in heading or "cuet" in heading)
            ):
                bonus += 0.60
            if "admission notification (ug" in heading or "ug 2026" in heading:
                bonus -= 0.45
            if "postgraduate" in text or "pg programme" in text:
                bonus += 0.25
            if "syllabus" in heading:
                bonus -= 0.45

        asks_result = "result" in query_lower or "semester result" in query_lower
        if asks_result:
            if "result" in heading or "semester result" in text:
                bonus += 0.55
            if "data science" in query_lower and (
                "data science" in heading or "data science" in text
            ):
                bonus += 0.35
            if "syllabus" in heading or "syllabus" in text:
                bonus -= 0.85

        asks_syllabus = any(
            term in query_lower
            for term in ("syllabus", "course structure", "subjects", "paper", "papers")
        )
        if asks_syllabus:
            asks_msc = "msc" in self._meaningful_words(normalized_query)
            asks_phd = "phd" in self._meaningful_words(normalized_query)
            if "syllabus" in heading:
                bonus += 0.35
            if focus_complete_in_heading and "syllabus" in heading:
                bonus += 0.90
            elif focus_words and focus_in_heading == 0 and "syllabus" in heading:
                bonus -= 1.35
            if wrong_specific_syllabus_heading:
                bonus -= 1.65
            if focus_words and focus_complete_in_text and (
                "syllabus" in heading
                or "syllabus" in text
                or "manual_syllabus" in source_file
                or "syllabus_content" in source_file
            ):
                bonus += 0.75
            elif focus_words and focus_in_text == 0 and (
                "syllabus" in heading or "manual_syllabus" in source_file
            ):
                bonus -= 1.10
            if content_overlap >= 2 and (
                "syllabus" in heading
                or "course structure" in heading
                or "manual_syllabus" in source_file
                or "syllabus_complete" in source_file
                or "syllabus_content" in source_file
            ):
                bonus += 0.65
            if department_match and ("syllabus" in text or "course structure" in text):
                bonus += 0.45
            if asks_msc and "msc" in normalized_heading:
                bonus += 0.55
            if asks_msc and "phd" in normalized_heading:
                bonus -= 0.85
            if asks_phd and "phd" in normalized_heading:
                bonus += 0.55
            if asks_phd and "msc" in normalized_heading:
                bonus -= 0.55
            if "result of" in heading or "semester result" in text:
                bonus -= 0.45

        asks_course_program = any(
            term in query_lower
            for term in (
                "course",
                "courses",
                "programme",
                "programmes",
                "program",
                "programs",
                "available",
                "baare",
                "about",
                "information",
                "details",
                "detail",
            )
        )
        if asks_course_program:
            broad_course_query = any(
                term in query_lower
                for term in ("kaun kaun", "available", "list", "all courses", "all programmes")
            )
            if broad_course_query and "cusb complete courses and programmes list" in heading:
                bonus += 0.65
            if broad_course_query and "complete courses and programmes list" in text:
                bonus += 0.45
            if not broad_course_query and content_overlap >= 2:
                if "syllabus" in heading or "course structure" in heading:
                    bonus += 0.85
                if "prospectus" in heading or "complete courses and programmes list" in heading:
                    bonus += 0.45
                if "programme" in text or "program" in text or "eligibility" in text:
                    bonus += 0.35
            if not broad_course_query and focus_words:
                if focus_complete_in_heading:
                    bonus += 0.85
                elif focus_complete_in_text:
                    bonus += 0.45
                elif "manual syllabus - department" in heading or "faculty roster -" in heading:
                    bonus -= 0.60
                elif focus_in_text == 0:
                    bonus -= 0.75
                elif len(focus_words) >= 2 and focus_in_text < len(focus_words):
                    bonus -= 0.25
            if not broad_course_query and content_overlap >= 2 and (
                "complete courses and programmes list" in heading or "complete knowledge base" in heading
            ):
                bonus += 0.50
            if "msc" in self._meaningful_words(normalized_query) and "msc" in normalized_text:
                bonus += 0.20
            if department_match and any(term in text for term in ("programme", "program", "eligibility", "course")):
                bonus += 0.35
            if "result of" in heading or "semester result" in text:
                bonus -= 0.55

        faculty_keyword_hit = any(
            term in query_lower
            for term in (
                "faculty",
                "faculties",
                "professor",
                "teacher",
                "teachers",
                "hod",
                "head",
                "name",
                "names",
            )
        )
        asks_who_faculty = "kaun" in query_lower and not asks_course_program
        asks_faculty = faculty_keyword_hit or asks_who_faculty
        if asks_faculty:
            if record_type == "faculty_department_full":
                bonus += 0.35
            if chunk_kind == "department_roster" or "faculty roster -" in heading:
                bonus += 0.60
            if any(term in query_lower for term in ("hod", "head")) and (
                "head/hod:" in text or "professor & head" in text or "professor and head" in text
            ):
                bonus += 0.65
            if department_match:
                bonus += 0.75
            if "department:" in text and any(word in text for word in re.findall(r"[\w]+", query_lower)):
                bonus += 0.10
            if "syllabus" in text and record_type != "faculty_department_full":
                bonus -= 0.45

        asks_library_facility = "library" in query_lower and any(
            term in query_lower
            for term in ("facility", "facilities", "service", "services", "kya", "hai", "about")
        )
        if asks_library_facility:
            if "central library" in text or "library facility" in text or "library services" in text:
                bonus += 0.55
            if "library" in heading:
                bonus += 0.35
            if "facility" in record_type or "facility" in source_file or "infra" in source_file:
                bonus += 0.25
            if "faculty information" in text:
                bonus -= 0.35

        asks_placement = "placement" in query_lower or "career counselling" in query_lower
        if asks_placement:
            if "career counselling and placement cell" in text:
                bonus += 0.75
            if "training and placement coordinator" in text:
                bonus += 0.45
            if "placement training" in text or "job fairs" in text:
                bonus += 0.25

        asks_hostel_admission = "hostel" in query_lower and any(
            term in query_lower for term in ("admission", "process", "apply", "application")
        )
        if asks_hostel_admission:
            if "hostel accommodation applications" in heading or "hostel accommodation applications" in text:
                bonus += 0.75
            if "invitation for hostel" in heading:
                bonus += 0.45
            if "admission steps" in text and "hostel" not in heading:
                bonus -= 0.35

        asks_boys_hostel = "hostel" in query_lower and any(term in query_lower for term in ("boys", "boy"))
        if asks_boys_hostel:
            if "boys hostel" in heading or "boys hostel" in text:
                bonus += 0.45
            if "allotment list" in heading and "boys" in heading:
                bonus += 0.55
            if "construction" in heading or "tender" in heading or "visitor shed" in heading:
                bonus -= 0.80

        asks_girls_hostel = "hostel" in query_lower and any(term in query_lower for term in ("girls", "girl"))
        if asks_girls_hostel:
            if "girls hostel" in heading or "girls hostel" in text:
                bonus += 0.45
            if "allotment list" in heading and "girls" in heading:
                bonus += 0.55
            if "construction" in heading or "tender" in heading or "visitor shed" in heading:
                bonus -= 0.80

        return bonus

    def build_context(self, chunks: list[dict], max_chars: int = MAX_CONTEXT) -> str:
        """Concatenate retrieved chunks into context."""
        parts = []
        total = 0

        for rank, chunk in enumerate(chunks, 1):
            # Filter out Source: lines and QA Batch headings from chunk text
            text = chunk['text']
            text_lines = text.split('\n')
            filtered_lines = [
                line for line in text_lines
                if not line.strip().startswith('Source:')
                and not line.strip().startswith('**Source:**')
                and 'QA Batch' not in line
            ]
            clean_text = '\n'.join(filtered_lines)

            # Skip QA Batch headings
            heading = chunk.get('heading', 'Untitled')
            if 'QA Batch' in heading:
                heading = 'Information'

            context_part = f"[Section: {heading}]\n{clean_text}"

            if total + len(context_part) > max_chars:
                remaining = max_chars - total
                if remaining > 100:
                    parts.append(context_part[:remaining].rstrip())
                break

            parts.append(context_part)
            total += len(context_part)

        return "\n\n---\n\n".join(parts)


class QdrantRetriever(Retriever):
    """Qdrant-backed retriever with the same ranking rules as the FAISS retriever."""

    def __init__(self):
        if not CHUNKS_PATH.exists():
            raise FileNotFoundError(
                f"Required chunks file missing: {CHUNKS_PATH}\n"
                "Run: python src/1_build_chunks.py"
            )

        from sentence_transformers import SentenceTransformer
        from vectorstore.qdrant_client import QdrantVectorStore

        with open(CHUNKS_PATH, "rb") as f:
            self.chunks = pickle.load(f)

        self.id_to_pos = {
            int(chunk.get("id", pos)): pos
            for pos, chunk in enumerate(self.chunks)
        }
        self.model = SentenceTransformer(EMBED_MODEL)
        self.store = QdrantVectorStore(collection_name=QDRANT_COLLECTION, url=QDRANT_URL, path=QDRANT_PATH)
        self.index = type("QdrantIndexInfo", (), {"ntotal": len(self.chunks)})()
        self.reranker = None

        self.bm25 = None
        self.use_bm25 = os.getenv("USE_BM25_HYBRID", "true").lower() in {"1", "true", "yes"}
        if self.use_bm25:
            try:
                from rank_bm25 import BM25Okapi

                corpus_tokens = [
                    tokenize_for_sparse(f"{chunk.get('heading', '')} {chunk.get('text', '')}")
                    for chunk in self.chunks
                ]
                self.bm25 = BM25Okapi(corpus_tokens)
            except Exception as exc:
                print(f"BM25 disabled: {str(exc).splitlines()[0]}")
                self.use_bm25 = False

        if USE_RERANKER:
            try:
                from sentence_transformers import CrossEncoder

                self.reranker = CrossEncoder(RERANK_MODEL)
            except Exception as exc:
                print(f"Reranker disabled: {str(exc).splitlines()[0]}")

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[dict]:
        retrieval_query = expand_query_for_retrieval(query)
        q_vec = self.model.encode(
            [retrieval_query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        candidate_k = min(max(top_k * 5, RETRIEVAL_CANDIDATES), len(self.chunks))
        try:
            dense_hits = self.store.search(q_vec[0].tolist(), top_k=candidate_k)
        except Exception as exc:
            raise RuntimeError(
                "Qdrant backend is selected, but Qdrant search failed. "
                "Index local Qdrant storage first:\n"
                "  $env:QDRANT_PATH='data\\qdrant_local'\n"
                "  python scripts\\index_qdrant.py"
            ) from exc

        query_terms = {
            token
            for token in re.findall(r"[\w]+", retrieval_query.lower(), flags=re.UNICODE)
            if len(token) > 2
        }

        results_by_id = {}
        for dense_rank, hit in enumerate(dense_hits, 1):
            chunk_id = hit.get("id")
            pos = self.id_to_pos.get(int(chunk_id)) if chunk_id is not None else None
            if pos is None:
                continue
            chunk = self.chunks[pos].copy()
            haystack = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
            heading = chunk.get("heading", "").lower()
            matched_terms = {term for term in query_terms if term in haystack}
            heading_matches = {term for term in query_terms if term in heading}
            lexical_bonus = min(0.20, 0.025 * len(matched_terms) + 0.025 * len(heading_matches))
            quality_bonus = self._domain_quality_bonus(retrieval_query, chunk)
            rrf_bonus = 1.0 / (60 + dense_rank)
            chunk["vector_score"] = float(hit.get("score", 0.0))
            chunk["dense_rank"] = int(dense_rank)
            chunk["rrf_bonus"] = float(rrf_bonus)
            chunk["lexical_bonus"] = float(lexical_bonus)
            chunk["quality_bonus"] = float(quality_bonus)
            chunk["score"] = float(hit.get("score", 0.0) + lexical_bonus + quality_bonus + rrf_bonus)
            results_by_id[pos] = chunk

        if self.bm25:
            bm25_scores = self.bm25.get_scores(tokenize_for_sparse(retrieval_query))
            bm25_top_k = min(max(candidate_k, 50), len(self.chunks))
            bm25_ranked = sorted(enumerate(bm25_scores), key=lambda pair: pair[1], reverse=True)[:bm25_top_k]
            max_bm25 = max((score for _, score in bm25_ranked), default=0.0) or 1.0
            for bm25_rank, (pos, bm25_score) in enumerate(bm25_ranked, 1):
                if bm25_score <= 0:
                    continue
                bm25_bonus = 0.35 * (float(bm25_score) / float(max_bm25))
                rrf_bonus = 1.0 / (60 + bm25_rank)
                if pos in results_by_id:
                    results_by_id[pos]["bm25_score"] = float(bm25_score)
                    results_by_id[pos]["bm25_rank"] = int(bm25_rank)
                    results_by_id[pos]["bm25_bonus"] = max(
                        float(results_by_id[pos].get("bm25_bonus", 0.0)),
                        float(bm25_bonus),
                    )
                    results_by_id[pos]["rrf_bonus"] = float(results_by_id[pos].get("rrf_bonus", 0.0)) + rrf_bonus
                    results_by_id[pos]["score"] = (
                        results_by_id[pos].get("vector_score", 0.0)
                        + results_by_id[pos].get("lexical_bonus", 0.0)
                        + results_by_id[pos].get("quality_bonus", 0.0)
                        + results_by_id[pos].get("bm25_bonus", 0.0)
                        + results_by_id[pos].get("rrf_bonus", 0.0)
                    )
                    continue

                chunk = self.chunks[pos].copy()
                haystack = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
                heading = chunk.get("heading", "").lower()
                matched_terms = {term for term in query_terms if term in haystack}
                heading_matches = {term for term in query_terms if term in heading}
                lexical_bonus = min(0.45, 0.05 * len(matched_terms) + 0.05 * len(heading_matches))
                quality_bonus = self._domain_quality_bonus(retrieval_query, chunk)
                chunk["vector_score"] = 0.0
                chunk["bm25_score"] = float(bm25_score)
                chunk["bm25_rank"] = int(bm25_rank)
                chunk["bm25_bonus"] = float(bm25_bonus)
                chunk["rrf_bonus"] = float(rrf_bonus)
                chunk["lexical_bonus"] = float(lexical_bonus)
                chunk["quality_bonus"] = float(quality_bonus)
                chunk["score"] = float(lexical_bonus + quality_bonus + bm25_bonus + rrf_bonus)
                results_by_id[pos] = chunk

        results = list(results_by_id.values())
        results.sort(key=lambda item: item["score"], reverse=True)
        candidates = self._diversify_by_heading(results, top_k=candidate_k)
        return self._rerank(query, candidates, top_k=top_k)


SYSTEM_PROMPT = """You are a helpful AI assistant for Central University of South Bihar (CUSB).
Answer questions about the university using ONLY the context provided below.
- You must answer in the requested output language exactly:
  - English question -> English answer.
  - Hindi question written in Devanagari -> Hindi answer in Devanagari.
  - Hinglish question -> Hinglish answer using simple Roman Hindi + English.

CRITICAL INSTRUCTIONS FOR SYLLABUS QUERIES:
- When user asks for "syllabus", "course structure", or subjects/courses:
  1. FIRST extract and present the actual syllabus content (subjects, topics, credits, courses) from the context
  2. THEN provide the PDF download link at the end
  3. Never just give the link without extracting the content first
  4. If the context contains course objectives, course outcomes, units, topics, credits, or course structure, NEVER say that the detailed syllabus is not included.
  5. Do NOT use phrases like "may cover", "might include", "probably", or guessed topic lists. Only state syllabus/topics that are explicitly present in the context.

- For syllabus questions, include:
  - Subject names and course codes if available
  - Brief overview of topics covered
  - Any credit information or semester details from context
  - Then the download link for full PDF

CRITICAL INSTRUCTIONS FOR PROGRAMME OVERVIEW QUERIES:
- When user asks "tell me about", "full information", "details", "ke baare me", or asks about a specific programme:
  1. Summarize only exact facts from context: department, collaboration, duration, semesters, credits, eligibility, objectives, outcomes, course structure, and exact links if present.
  2. If syllabus/course objectives/outcomes are present in context, use them directly. Do not say syllabus details are missing.
  3. If only partial information is present, say "The provided context has limited details" and list only the available facts.
  4. Never infer or invent modules, topics, specializations, eligibility, URLs, or career outcomes.

CRITICAL INSTRUCTIONS FOR FACULTY QUERIES:
- When user asks for "faculty", "professor", "teacher", "head", "coordinator", "HOD", or "kaun hai":
  1. FIRST check the context for Administration, Dean, Proctorial Board, or specific department faculty names
  2. If faculty names are found in context, LIST them clearly with their designations
  3. If specific faculty information is NOT in context, provide a helpful response indicating that detailed information is available on the official website
  4. NEVER say "information not found" without checking the context first

CRITICAL INSTRUCTIONS FOR COURSE/PROGRAM QUERIES:
- When user asks for "courses", "programmes", "kaun kaun se course hain", "list all", or "how many courses":
  1. FIRST check for "CUSB Complete Courses and Programmes List" section in context
  2. If course list is available, LIST them clearly by category (M.Sc, B.Sc, B.A., Integrated, etc.)
  3. For M.Sc queries, list ALL M.Sc programmes available (25+ programmes)
  4. For B.Sc queries, list ALL B.Sc programmes available
  5. Include department names and durations
  6. NEVER give internal course codes (like BTN 8 1 DE 011 04) when asked for programme list
  7. Course codes are ONLY for syllabus/subject queries, NOT for programme list queries

- IMPORTANT: If the context contains specific download links, PDF URLs, forms, faculty names, or course lists, you MUST include them in your answer.
- CRITICAL INSTRUCTIONS FOR FEE QUERIES:
  1. Quote only fee amounts explicitly present in context.
  2. Do not calculate or invent a grand total unless the context explicitly labels it as Total/Estimated Total.
  3. For hostel fee, list components separately: hostel fee per semester, mess charges, security deposit, maintenance fee, and any explicit estimated annual total. Do not add your own arithmetic total.
  4. For admission-time total fee, if the context is programme-specific or ambiguous, say that fee depends on programme/category and ask for the specific programme. Do not use an unrelated notice as a general admission fee.
  5. If multiple conflicting fee figures appear, present them as context variants with labels instead of choosing one silently.
- Never invent or guess URLs. Include a URL only when the exact full URL appears in the provided context. If only a general website is available, use only https://www.cusb.ac.in.
- Never invent syllabus topics, specializations, fees, dates, faculty names, or course outcomes. If exact details are not present in context, say that the provided context has limited details.
- Prefer direct, student-friendly answers over dumping raw context.
- Be concise but comprehensive for syllabus queries.
- CRITICAL: NEVER include "Source:", "Sources:", or any source references in your answer. Do NOT mention where the information came from. Just provide the answer directly.
- If the answer is not in the context, respond with: "The provided information does not include details regarding this query. For the most accurate and up-to-date information, please refer to the university's official website: https://www.cusb.ac.in."
- Never make up information.
"""


class GeminiGenerator:
    """Generates answers using Google Gemini."""

    def __init__(self, api_key: Optional[str] = None):
        import google.generativeai as genai

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "❌  GEMINI_API_KEY not set.\n"
                "    Get a free key at: https://aistudio.google.com/app/apikey\n"
                "    Then set it in your .env file: GEMINI_API_KEY=your_key_here"
            )

        genai.configure(api_key=key)
        self.genai = genai
        self.model_names = []
        for model_name in [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]:
            if model_name not in self.model_names:
                self.model_names.append(model_name)
        self.active_model_name = self.model_names[0]

    def generate(self, query: str, context: str, output_language: str = "English") -> str:
        prompt = f"""{SYSTEM_PROMPT}

=== CONTEXT (from CUSB knowledge base) ===
{context}
===========================================

User Question: {query}
Required Output Language: {output_language}

Answer:"""
        errors = []
        for model_name in self.model_names:
            try:
                model = self.genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                self.active_model_name = model_name
                return response.text.strip()
            except Exception as e:
                errors.append(f"{model_name}: {str(e).splitlines()[0]}")

        compact_errors = " | ".join(errors)
        raise RuntimeError(f"LLM unavailable after trying fallback models. {compact_errors}") from None


class GroqGenerator:
    """Generates answers using Groq API (free, fast alternative to Gemini)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from groq import Groq

        key = api_key or GROQ_API_KEY
        if not key:
            raise ValueError(
                "❌  GROQ_API_KEY not set.\n"
                "    Get a free key at: https://console.groq.com/keys\n"
                "    Then set it in your .env file: GROQ_API_KEY=your_key_here"
            )

        self.client = Groq(api_key=key)
        self.model_name = model or GROQ_MODEL

    def generate(self, query: str, context: str, output_language: str = "English") -> str:
        answer_guard = """Hard answer rules:
- Use only exact facts visible in the context above.
- Do not add course structure, eligibility, credits, duration, semester-wise subjects, or download links unless those exact facts appear in the context.
- For fee questions, do not calculate your own total. Quote explicit totals only, and keep components separate when no explicit total is given.
- For admission-time total fee, do not generalize from a programme-specific notice. If programme is not specified, say the fee depends on the programme/category.
- Do not write guessed phrases such as "may cover", "might include", "probably", or invented lists.
- If a detail is absent, omit that detail instead of guessing it."""

        prompt = f"""{SYSTEM_PROMPT}\n\n=== CONTEXT (from CUSB knowledge base) ===\n{context}\n===========================================\n\n{answer_guard}\n\nUser Question: {query}\nRequired Output Language: {output_language}\n\nAnswer:"""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\n{answer_guard}\n\nQuestion: {query}\nAnswer in {output_language}:"},
            ],
            max_tokens=1024,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()


class FallbackGenerator:
    """Readable offline fallback when no LLM is available."""

    def generate(self, query: str, context: str, output_language: str = "English") -> str:
        if not context.strip():
            if output_language == "Hindi":
                return "माफ कीजिए, इस बारे में जानकारी नहीं मिली। कृपया CUSB वेबसाइट देखें: https://www.cusb.ac.in"
            if output_language == "Hinglish":
                return "Maafi chahta/chahti hoon, is baare mein information nahi mili. Please CUSB website check karein: https://www.cusb.ac.in"
            return "Sorry, I could not find information about this. Please check the CUSB website: https://www.cusb.ac.in"

        sections = [section.strip() for section in context.split("\n\n---\n\n") if section.strip()]
        best_section = sections[0]
        for section in sections:
            body_lines = [
                line.strip()
                for line in section.splitlines()
                if line.strip() and not line.startswith("[Source ")
            ]
            body = "\n".join(body_lines)
            has_substantive_answer = (
                len(body) > 120
                and (
                    "\n1." in body
                    or "A:" in body
                    or "|" in body
                    or "₹" in body
                    or len(body_lines) >= 4
                )
            )
            if has_substantive_answer:
                best_section = section
                break

        if len(best_section) > 900:
            best_section = best_section[:900].rsplit("\n", 1)[0].strip()

        headings = {
            "English": "📚 Retrieved from CUSB knowledge base:",
            "Hindi": "📚 CUSB ज्ञान आधार से प्राप्त जानकारी:",
            "Hinglish": "📚 CUSB knowledge base se retrieved information:",
        }
        return f"{headings.get(output_language, headings['English'])}\n\n{best_section}"


class RAGPipeline:
    """Full RAG pipeline: query -> retrieve chunks -> build context -> answer."""

    def __init__(self, api_key: Optional[str] = None, use_llm: bool = True, model: Optional[str] = None):
        if VECTOR_BACKEND == "qdrant":
            self.retriever = QdrantRetriever()
            print(f"✅  Retriever backend: Qdrant ({QDRANT_COLLECTION})")
        elif VECTOR_BACKEND == "faiss":
            self.retriever = Retriever()
            print("✅  Retriever backend: FAISS")
        else:
            raise ValueError("VECTOR_BACKEND must be either 'faiss' or 'qdrant'")
        self.fallback_generator = FallbackGenerator()

        if use_llm:
            provider = LLM_PROVIDER.lower()
            if provider == "groq":
                try:
                    self.generator = GroqGenerator(api_key, model)
                    print(f"✅  Groq LLM connected ({self.generator.model_name})")
                except ValueError as e:
                    print(f"⚠️  {e}\n    Trying Gemini fallback...")
                    try:
                        self.generator = GeminiGenerator()
                        print(f"✅  Gemini LLM connected ({', '.join(self.generator.model_names)})")
                    except ValueError as e2:
                        print(f"⚠️  {e2}\n    Using fallback (no LLM).")
                        self.generator = self.fallback_generator
            else:
                try:
                    self.generator = GeminiGenerator(api_key)
                    print(f"✅  Gemini LLM connected ({', '.join(self.generator.model_names)})")
                except ValueError as e:
                    print(f"⚠️  {e}\n    Trying Groq fallback...")
                    try:
                        self.generator = GroqGenerator()
                        print(f"✅  Groq LLM connected ({self.generator.model_name})")
                    except ValueError:
                        print(f"⚠️  Using fallback (no LLM).")
                        self.generator = self.fallback_generator
        else:
            self.generator = self.fallback_generator
            print("ℹ️   Running in fallback mode (no LLM)")

    def answer(self, query: str, top_k: int = TOP_K, verbose: bool = False) -> dict:
        """Return answer, source metadata, and the exact context sent to the LLM."""
        output_language = detect_query_language(query)
        chunks = self.retriever.retrieve(query, top_k=top_k)
        context = self.retriever.build_context(chunks)

        if verbose:
            print(f"\n🔍 Retrieved {len(chunks)} chunks:")
            for chunk in chunks:
                print(f"   [{chunk['score']:.3f}] {chunk['heading']}")

        try:
            answer = self.generator.generate(query, context, output_language=output_language)
        except Exception as e:
            fallback = self.fallback_generator.generate(query, context, output_language=output_language)
            answer = f"⚠️  {e}\n\nUsing offline fallback:\n\n{fallback}"

        # Post-process: Remove any Source lines from answer
        answer_lines = answer.split('\n')
        cleaned_lines = []
        for line in answer_lines:
            # Skip lines that start with Source: or contain source references
            stripped = line.strip()
            if stripped.startswith('Source:'):
                continue
            if stripped.startswith('Sources:'):
                continue
            if stripped.startswith('The most relevant source'):
                continue
            cleaned_lines.append(line)

        answer = '\n'.join(cleaned_lines).strip()
        answer = self._remove_unsupported_urls(answer, context)

        return {
            "answer": answer,
            "language": output_language,
            "sources": [
                {
                    "id": chunk.get("id"),
                    "heading": chunk["heading"],
                    "score": chunk["score"],
                    "char_count": chunk.get("char_count"),
                    "source_file": chunk.get("source_file"),
                    "url": chunk.get("url") or chunk.get("source_url") or chunk.get("pdf_url"),
                    "page": chunk.get("page") or chunk.get("page_no") or chunk.get("page_number"),
                    "vector_score": chunk.get("vector_score"),
                    "bm25_score": chunk.get("bm25_score"),
                    "rerank_score": chunk.get("rerank_score"),
                }
                for chunk in chunks
            ],
            "context": context,
        }

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        """Expose retrieval-only search for evaluation and advanced modules."""
        return self.retriever.retrieve(query, top_k=k)

    def _remove_unsupported_urls(self, answer: str, context: str) -> str:
        """Strip URLs hallucinated by the LLM when they are not present in context."""
        context_urls = set(re.findall(r"https?://[^\s)\]>\"']+", context))
        answer_urls = set(re.findall(r"https?://[^\s)\]>\"']+", answer))
        for url in answer_urls:
            if url not in context_urls and url.rstrip(".") not in context_urls:
                answer = answer.replace(url, "https://www.cusb.ac.in")
        return answer
