"""
Core RAG retrieval and generation engine.

This module can be used by the CLI chatbot or imported into a web/API app.
"""

import os
import pickle
import re
from typing import Optional

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
)


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
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:
                continue
            chunk = self.chunks[idx].copy()
            haystack = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
            heading = chunk.get("heading", "").lower()
            matched_terms = {term for term in query_terms if term in haystack}
            heading_matches = {term for term in query_terms if term in heading}
            lexical_bonus = min(0.20, 0.025 * len(matched_terms) + 0.025 * len(heading_matches))
            quality_bonus = self._domain_quality_bonus(retrieval_query, chunk)
            chunk["vector_score"] = float(score)
            chunk["lexical_bonus"] = float(lexical_bonus)
            chunk["quality_bonus"] = float(quality_bonus)
            chunk["score"] = float(score + lexical_bonus + quality_bonus)
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
        return self._rerank(query, results[:candidate_k], top_k=top_k)

    def _rerank(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        """Optionally rerank candidates with a cross-encoder."""
        if not self.reranker or not chunks:
            return chunks[:top_k]

        pairs = [[query, chunk["text"][:1200]] for chunk in chunks]
        rerank_scores = self.reranker.predict(pairs)
        reranked = []
        for chunk, rerank_score in zip(chunks, rerank_scores):
            updated = chunk.copy()
            updated["pre_rerank_score"] = updated["score"]
            updated["rerank_score"] = float(rerank_score)
            updated["score"] = float(rerank_score)
            reranked.append(updated)

        reranked.sort(key=lambda item: item["score"], reverse=True)
        return reranked[:top_k]

    def _domain_quality_bonus(self, query: str, chunk: dict) -> float:
        """Prefer concrete CUSB fee/facility facts over vague QA snippets."""
        query_lower = query.lower()
        text = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
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

        asks_fee = any(term in query_lower for term in ("fee", "fees", "फीस", "शुल्क"))
        if asks_fee and "₹" in text:
            bonus += 0.05

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

- For syllabus questions, include:
  - Subject names and course codes if available
  - Brief overview of topics covered
  - Any credit information or semester details from context
  - Then the download link for full PDF

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
        prompt = f"""{SYSTEM_PROMPT}\n\n=== CONTEXT (from CUSB knowledge base) ===\n{context}\n===========================================\n\nUser Question: {query}\nRequired Output Language: {output_language}\n\nAnswer:"""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}\nAnswer in {output_language}:"},
            ],
            max_tokens=1024,
            temperature=0.3,
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
        self.retriever = Retriever()
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

        return {
            "answer": answer,
            "language": output_language,
            "sources": [
                {
                    "id": chunk.get("id"),
                    "heading": chunk["heading"],
                    "score": chunk["score"],
                    "char_count": chunk.get("char_count"),
                }
                for chunk in chunks
            ],
            "context": context,
        }
