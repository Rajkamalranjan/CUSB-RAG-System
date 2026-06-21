"""Production hybrid retriever.

Uses the existing FAISS retriever as the dense path and adds BM25 + RRF. This
lets the project run now, while Qdrant can be switched in through the vectorstore
package once the collection is indexed.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rag_engine import QdrantRetriever, Retriever
from retriever.hybrid.rrf_fusion import reciprocal_rank_fusion
from retriever.sparse.bm25_retriever import BM25Retriever
from retriever.sparse.query_expander import expand_query


ABOUT_QUERY_TERMS = (
    "about cusb",
    "what is cusb",
    "cusb kya hai",
    "full information about cusb",
    "central university of south bihar",
)

DEPARTMENT_ALIASES = {
    "agriculture": ("agriculture", "agricultural"),
    "bioinformatics": ("bioinformatics", "bio informatics"),
    "biotechnology": ("biotechnology", "bio technology"),
    "chemistry": ("chemistry", "chemical science", "chemical sciences"),
    "commerce and business studies": (
        "commerce and business studies",
        "commerce & business studies",
        "commerce",
        "business studies",
        "m.com",
        "mcom",
    ),
    "statistics": ("statistics", "statistic", "statisitcs", "statstics", "stats"),
    "mathematics": ("mathematics", "maths", "math"),
    "computer science": ("computer science", "cs", "cse"),
    "development studies": ("development studies", "development"),
    "economic studies and policy": ("economic studies and policy", "economics", "economic studies", "economy"),
    "education": ("education", "teacher education", "b.ed", "bed", "m.ed", "med"),
    "english": ("english", "english and foreign languages", "foreign languages"),
    "environmental science": ("environmental science", "environmental sciences", "environment"),
    "geography": ("geography", "geographical"),
    "geology": ("geology", "geological"),
    "hindi": ("hindi", "indian languages", "bharatiya bhasha"),
    "historical studies and archaeology": (
        "historical studies and archaeology",
        "history",
        "historical studies",
        "archaeology",
        "archeology",
    ),
    "law and governance": ("law and governance", "law", "llb", "ll.m", "llm"),
    "library and information science": ("library and information science", "library science", "lis"),
    "life science": ("life science", "life sciences", "biological science", "biological sciences"),
    "mass communication and media": (
        "mass communication and media",
        "mass communication",
        "media",
        "journalism",
    ),
    "pharmacy": ("pharmacy", "pharmaceutical", "m.pharm", "mpharm"),
    "physical education": ("physical education", "sports science", "m.p.ed", "mped"),
    "physics": ("physics", "physical science", "physical sciences"),
    "political studies": ("political studies", "political science", "politics", "international relations"),
    "psychological sciences": ("psychological sciences", "psychology", "psychological"),
    "sociological studies": ("sociological studies", "sociology", "social work"),
}

DEPARTMENT_CODE_PREFIXES = {
    "mathematics": ("mth",),
    "computer science": ("mscsc", "csc"),
    "statistics": ("sts",),
    "biotechnology": ("btn",),
    "bioinformatics": ("bin",),
    "chemistry": ("che",),
    "physics": ("phy",),
    "geology": ("gel",),
    "geography": ("geo",),
    "education": ("edu",),
    "law and governance": ("law",),
    "commerce and business studies": ("com",),
    "pharmacy": ("pha",),
}


def _is_about_university_query(query: str) -> bool:
    normalized = " ".join(query.lower().split())
    return any(term in normalized for term in ABOUT_QUERY_TERMS)


def _is_faculty_chunk(chunk: dict) -> bool:
    text = f"{chunk.get('heading', '')} {chunk.get('source_file', '')} {chunk.get('record_type', '')}".lower()
    return any(term in text for term in ("faculty", "teacher", "professor", "hod"))


def _about_chunk_bonus(chunk: dict) -> float:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('source_file', '')}".lower()
    bonus = 0.0
    if "about cusb" in text or "about university" in text:
        bonus += 3.0
    if "central university of south bihar" in text:
        bonus += 1.5
    if "central universities act" in text or "established" in text:
        bonus += 1.0
    if _is_faculty_chunk(chunk):
        bonus -= 4.0
    return bonus


def _is_sports_query(query: str) -> bool:
    normalized = query.lower()
    return any(
        term in normalized
        for term in (
            "sports",
            "sport",
            "games",
            "playground",
            "indoor",
            "outdoor",
            "physical fitness",
            "sports complex",
        )
    )


def _is_sports_chunk(chunk: dict) -> bool:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('source_file', '')}".lower()
    return any(
        term in text
        for term in (
            "sports complex",
            "games & sports committee",
            "games and sports committee",
            "sports committee",
            "outdoor & indoor sports",
            "outdoor and indoor sports",
        )
    )


def _sports_chunk_bonus(chunk: dict) -> float:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('source_file', '')}".lower()
    bonus = 0.0
    if "sports complex" in text:
        bonus += 7.0
    if "games & sports committee" in text or "games and sports committee" in text:
        bonus += 5.0
    if "outdoor" in text and "indoor" in text and "sports" in text:
        bonus += 3.0
    if "prospectus" in text:
        bonus -= 1.5
    return bonus


def _is_syllabus_query(query: str) -> bool:
    normalized = query.lower()
    return any(
        term in normalized
        for term in ("syllabus", "course structure", "subjects", "papers", "curriculum", "pathyakram")
    )


def _academic_department(query: str) -> str | None:
    normalized = query.lower()
    matches = []
    for department, aliases in DEPARTMENT_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                matches.append((len(alias), department))
    if matches:
        return max(matches)[1]
    return None


def _is_syllabus_chunk(chunk: dict, department: str | None) -> bool:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('department', '')} {chunk.get('source_file', '')}".lower()
    heading = str(chunk.get("heading", "")).lower()
    if _is_result_like_chunk(chunk):
        return False
    if department:
        aliases = DEPARTMENT_ALIASES.get(department, (department,))
        code_prefixes = DEPARTMENT_CODE_PREFIXES.get(department, ())
        department_match = any(alias in heading for alias in aliases)
        department_match = department_match or any(f"department of {alias}" in text for alias in aliases)
        department_match = department_match or any(re.search(rf"\b{prefix}\d", text) for prefix in code_prefixes)
        if not department_match:
            return False
    has_syllabus_signal = any(
        term in text
        for term in (
            "syllabus",
            "course structure",
            "course code",
            "course title",
            "semester",
            "credits",
            "mscsc",
            "phd computer science",
            "m.sc. in computer science",
        )
    )
    if not has_syllabus_signal:
        return False
    if "faculty full info" in text:
        return False
    return True


def _syllabus_chunk_bonus(chunk: dict, department: str | None) -> float:
    heading = str(chunk.get("heading", "")).lower()
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('source_file', '')}".lower()
    bonus = 0.0
    if _is_result_like_chunk(chunk):
        return -20.0
    if _is_generic_course_policy_chunk(chunk):
        bonus -= 12.0
    if "manual_syllabus" in text:
        bonus += 14.0
    if department and any(alias in heading for alias in DEPARTMENT_ALIASES.get(department, (department,))):
        bonus += 10.0
    if department and any(f"department of {alias}" in text for alias in DEPARTMENT_ALIASES.get(department, (department,))):
        bonus += 6.0
    if "course structure" in text:
        bonus += 5.0
    if "syllabus" in text:
        bonus += 4.0
    if "course code" in text or "course title" in text or "credits" in text:
        bonus += 3.0
    if department == "computer science":
        if any(term in text for term in ("msc computer science course structure", "m.sc. computer science", "m.sc. in computer science")):
            bonus += 22.0
        if "department of computer science" in text:
            bonus += 12.0
        if "phd computer science syllabus" in text or "ph.d. in computer science" in text:
            bonus += 14.0
        if "mscsc" in text:
            bonus += 8.0
    if department:
        for prefix in DEPARTMENT_CODE_PREFIXES.get(department, ()):
            if re.search(rf"\b{prefix}\d", text):
                bonus += 8.0
                break
    if "department of" in text:
        bonus += 1.0
    if "about university" in str(chunk.get("heading", "")).lower() and len(text) < 1500:
        bonus -= 3.0
    if "prospectus" in text:
        bonus -= 0.5
    if department and "prospectus_25" in text and not any(alias in heading for alias in DEPARTMENT_ALIASES.get(department, ())):
        bonus -= 6.0
    return bonus


def _is_generic_course_policy_chunk(chunk: dict) -> bool:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')}".lower()
    return any(
        term in text
        for term in (
            "course offered by the department of <name of the department>",
            "discipline/subject (next three letters",
            "course coding",
            "<name of the programme>",
        )
    )


def _is_result_like_chunk(chunk: dict) -> bool:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('source_file', '')}".lower()
    return any(
        term in text
        for term in (
            "semester result",
            "result of",
            "promoted",
            "provisionally",
            "backlog examination",
            "supplementary examination",
            "end-term examination",
            "end term examination",
            "time-table",
            "timetable",
            "exam schedule",
            "examination schedule",
            "enrolment no",
            "name of the student",
        )
    )


def _is_fee_query(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in ("fee", "fees", "फीस", "शुल्क"))


def _fee_chunk_bonus(query: str, chunk: dict) -> float:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('source_file', '')}".lower()
    department = _academic_department(query)
    bonus = 0.0
    if "complete fee structure" in text or "course-wise fee structure" in text:
        bonus += 8.0
    if "cusb complete fee structure" in text:
        bonus += 8.0
    if "total fees (approx.)" in text or "per semester" in text:
        bonus += 4.0
    if department and any(alias in text for alias in DEPARTMENT_ALIASES.get(department, (department,))):
        bonus += 5.0
    if "prospectus_2015" in text or "prospectus_2016" in text:
        bonus -= 4.0
    return bonus


def _faculty_query_name(query: str) -> str | None:
    normalized = " ".join(query.lower().split())
    match = re.search(r"\bdr\.?\s+([a-z]+(?:\s+[a-z]+){0,3})", normalized)
    if match:
        return f"dr. {match.group(1).strip()}"
    return None


def _is_faculty_query(query: str) -> bool:
    normalized = query.lower()
    return bool(_faculty_query_name(query)) or any(
        term in normalized
        for term in ("faculty", "professor", "teacher", "hod", "assistant professor", "associate professor")
    )


def _faculty_department(query: str) -> str | None:
    return _academic_department(query)


def _faculty_chunk_bonus(query: str, chunk: dict) -> float:
    text = f"{chunk.get('heading', '')} {chunk.get('text', '')} {chunk.get('source_file', '')}".lower()
    bonus = 0.0
    faculty_name = _faculty_query_name(query)
    faculty_department = _faculty_department(query)
    if faculty_name and faculty_name in text:
        bonus += 5.0
    if faculty_department and any(
        alias in str(chunk.get("department", "")).lower()
        for alias in DEPARTMENT_ALIASES.get(faculty_department, (faculty_department,))
    ):
        bonus += 5.0
    if faculty_department and any(
        f"faculty full info - {alias}" in text
        for alias in DEPARTMENT_ALIASES.get(faculty_department, (faculty_department,))
    ):
        bonus += 5.0
    if _is_faculty_chunk(chunk):
        bonus += 2.0
    if "faculty full info" in text or "profile/user/index" in text:
        bonus += 2.0
    if "complete knowledge base" in text:
        bonus -= 1.5
    if "prospectus" in text:
        bonus -= 1.0
    return bonus


def _dedupe_chunks(chunks: list[dict]) -> list[dict]:
    unique = []
    seen = set()
    for chunk in chunks:
        key = chunk.get("id")
        if key is None:
            key = (chunk.get("heading"), chunk.get("source_file"), chunk.get("url"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


class ProductionHybridRetriever:
    def __init__(self, use_reranker: bool = True):
        vector_backend = os.getenv("VECTOR_BACKEND", "qdrant").lower()
        self.dense = QdrantRetriever() if vector_backend == "qdrant" else Retriever()
        self.bm25 = BM25Retriever(self.dense.chunks)
        self.use_reranker = use_reranker
        self.reranker = None
        if use_reranker:
            from reranker.bge_reranker import BGEReranker

            self.reranker = BGEReranker()

    def retrieve(self, query: str, filters: dict | None = None, top_k: int | None = None) -> list[dict]:
        filters = filters or {}
        top_k = top_k or int(os.getenv("FINAL_TOP_K", "5"))
        dense_top_k = int(os.getenv("DENSE_TOP_K", "20"))
        bm25_top_k = int(os.getenv("BM25_TOP_K", "20"))
        fused_top_k = int(os.getenv("FUSED_TOP_K", "30"))
        expanded = expand_query(query)

        dense_results = self.dense.retrieve(expanded, top_k=dense_top_k)
        bm25_results = self.bm25.retrieve(expanded, top_k=bm25_top_k)
        fused = reciprocal_rank_fusion([dense_results, bm25_results])[:fused_top_k]
        if _is_about_university_query(query):
            boosted = []
            for chunk in fused:
                item = chunk.copy()
                item["score"] = float(item.get("score", 0.0)) + _about_chunk_bonus(item)
                boosted.append(item)
            boosted.sort(key=lambda item: item.get("score", 0.0), reverse=True)
            non_faculty = [chunk for chunk in boosted if not _is_faculty_chunk(chunk)]
            fused = non_faculty if len(non_faculty) >= top_k else boosted
        elif _is_sports_query(query):
            direct_matches = []
            for chunk in self.dense.chunks:
                if not _is_sports_chunk(chunk):
                    continue
                item = chunk.copy()
                item["score"] = 20.0 + _sports_chunk_bonus(item)
                direct_matches.append(item)
            boosted = []
            for chunk in fused:
                item = chunk.copy()
                item["score"] = float(item.get("score", 0.0)) + _sports_chunk_bonus(item)
                boosted.append(item)
            boosted = _dedupe_chunks([*direct_matches, *boosted])
            boosted.sort(key=lambda item: item.get("score", 0.0), reverse=True)
            if direct_matches:
                top_k = max(top_k, min(len(direct_matches), 5))
            fused = boosted
        elif _is_fee_query(query):
            direct_matches = []
            for chunk in self.dense.chunks:
                item_score = _fee_chunk_bonus(query, chunk)
                if item_score < 8.0:
                    continue
                item = chunk.copy()
                item["score"] = 20.0 + item_score
                direct_matches.append(item)
                if len(direct_matches) >= 20:
                    break
            boosted = []
            for chunk in fused:
                item = chunk.copy()
                item["score"] = float(item.get("score", 0.0)) + _fee_chunk_bonus(query, item)
                boosted.append(item)
            boosted = _dedupe_chunks([*direct_matches, *boosted])
            boosted.sort(key=lambda item: item.get("score", 0.0), reverse=True)
            if direct_matches:
                top_k = max(top_k, min(len(direct_matches), 5))
            fused = boosted
        elif _is_syllabus_query(query):
            department = _academic_department(query)
            direct_matches = []
            for chunk in self.dense.chunks:
                if not _is_syllabus_chunk(chunk, department):
                    continue
                item = chunk.copy()
                item["score"] = 20.0 + _syllabus_chunk_bonus(item, department)
                direct_matches.append(item)
                if len(direct_matches) >= 80:
                    break
            boosted = []
            for chunk in fused:
                item = chunk.copy()
                item["score"] = float(item.get("score", 0.0)) + _syllabus_chunk_bonus(item, department)
                boosted.append(item)
            boosted = _dedupe_chunks([*direct_matches, *boosted])
            boosted.sort(key=lambda item: item.get("score", 0.0), reverse=True)
            if direct_matches:
                top_k = max(top_k, min(len(direct_matches), 8))
            fused = boosted
        elif _is_faculty_query(query):
            department = _faculty_department(query)
            direct_matches = []
            if department:
                for chunk in self.dense.chunks:
                    if str(chunk.get("record_type", "")).lower() != "faculty_department_full":
                        continue
                    if not any(
                        alias in str(chunk.get("department", "")).lower()
                        for alias in DEPARTMENT_ALIASES.get(department, (department,))
                    ):
                        continue
                    item = chunk.copy()
                    item["score"] = 20.0 + _faculty_chunk_bonus(query, item)
                    direct_matches.append(item)
            boosted = []
            for chunk in fused:
                item = chunk.copy()
                item["score"] = float(item.get("score", 0.0)) + _faculty_chunk_bonus(query, item)
                boosted.append(item)
            boosted = _dedupe_chunks([*direct_matches, *boosted])
            boosted.sort(key=lambda item: item.get("score", 0.0), reverse=True)
            if department:
                top_k = max(top_k, len(direct_matches), 8)
            fused = boosted
        if filters:
            fused = [chunk for chunk in fused if all(chunk.get(key) == value for key, value in filters.items())]
        if self.reranker:
            return self.reranker.rerank(query, fused, top_k=top_k)
        return fused[:top_k]

    def build_context(self, chunks: list[dict], max_chars: int = 3000) -> str:
        return self.dense.build_context(chunks, max_chars=max_chars)
