"""Regression tests for unsupported CUSB programme abstention."""

from __future__ import annotations

import unittest

from backend.middleware.programme_guard import classify_programme_query, unsupported_programme_answer


class ProgrammeGuardTests(unittest.TestCase):
    def test_blocks_unsupported_programmes_without_keyword_allowlisting(self) -> None:
        queries = (
            "Does CUSB offer MBBS?",
            "Does CUSB operate a medical college offering MBBS?",
            "Does CUSB offer an astronaut training programme?",
            "CUSB astronaut training programme offer karta hai kya?",
        )
        for query in queries:
            with self.subTest(query=query):
                decision = classify_programme_query(query)
                self.assertTrue(decision.applicable)
                self.assertFalse(decision.supported)

    def test_allows_programmes_present_in_official_department_data(self) -> None:
        queries = (
            "Does CUSB offer MSc Computer Science?",
            "Is BA LLB available at CUSB?",
            "CUSB MSc Artificial Intelligence offer karta hai kya?",
        )
        for query in queries:
            with self.subTest(query=query):
                decision = classify_programme_query(query)
                self.assertTrue(decision.applicable)
                self.assertTrue(decision.supported)

    def test_does_not_interfere_with_non_availability_questions(self) -> None:
        queries = (
            "What is the hostel fee at CUSB?",
            "MSc Computer Science syllabus kaha milega?",
            "What programmes are available in Computer Science department?",
        )
        for query in queries:
            with self.subTest(query=query):
                self.assertFalse(classify_programme_query(query).applicable)

    def test_response_language_matches_query(self) -> None:
        self.assertIn("could not verify", unsupported_programme_answer("Does CUSB offer MBBS?"))
        self.assertIn("verify nahi hua", unsupported_programme_answer("CUSB MBBS offer karta hai kya?"))


if __name__ == "__main__":
    unittest.main()
