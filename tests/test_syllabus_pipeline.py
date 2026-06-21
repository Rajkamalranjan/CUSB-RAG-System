"""Regression tests for generic syllabus answers backed by extracted chunks."""

from __future__ import annotations

import unittest

from backend.core.pipeline import ProductionRAGPipeline, RAGResult


class SyllabusPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = ProductionRAGPipeline.__new__(ProductionRAGPipeline)
        self.pipeline.fixed_answers = []
        self.pipeline._syllabus_catalog = [
            "msc chemistry syllabus",
            "msc mathematics course structure",
            "Msc mathematics syllabus",
            "msc statistics syllabus",
        ]

    def test_all_department_query_lists_extracted_syllabus_catalog(self) -> None:
        result = self.pipeline._syllabus_result("all department ka syllabus do", [])

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("Extracted CUSB syllabus PDFs (4 records)", result.answer)
        self.assertIn("msc chemistry syllabus", result.answer)
        self.assertIn("msc statistics syllabus", result.answer)

    def test_specific_department_query_uses_matching_extracted_chunks(self) -> None:
        chunks = [
            {
                "id": "chemistry-syllabus",
                "heading": "msc chemistry syllabus",
                "source_file": "data/cusb_manual_syllabus_pdfs.jsonl",
                "text": "Title: msc chemistry syllabus\n--- Page 1 [ocr] ---\nSemester I CHE81DC01004 Inorganic Chemistry 4",
                "score": 35.0,
            }
        ]

        result = self.pipeline._syllabus_result("M.Sc. Chemistry syllabus do", chunks)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("msc chemistry syllabus", result.answer)
        self.assertIn("CHE81DC01004 Inorganic Chemistry", result.answer)

    def test_mathematics_is_handled_by_the_same_generic_resolver(self) -> None:
        chunks = [
            {
                "id": "math-syllabus",
                "heading": "msc mathematics course structure",
                "source_file": "data/cusb_manual_syllabus_pdfs.jsonl",
                "text": "Semester I MTH81DC00104 Real Analysis 4",
                "score": 30.0,
            }
        ]

        result = self.pipeline._syllabus_result("M.Sc. Mathematics syllabus do", chunks)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("MTH81DC00104 Real Analysis", result.answer)

    def test_hinglish_localization_does_not_treat_syllabus_as_bus(self) -> None:
        generated = RAGResult(
            answer="Semester I: MTH81DC00104 Real Analysis 4 credits.",
            sources=[],
            confidence=30.0,
        )

        result = self.pipeline._localize_result("M.Sc. Mathematics syllabus do", generated)

        self.assertIn("MTH81DC00104 Real Analysis", result.answer)


if __name__ == "__main__":
    unittest.main()
