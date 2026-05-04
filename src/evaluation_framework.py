"""
Comprehensive Evaluation Framework for CUSB RAG System
Research + Production Quality Metrics
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
import numpy as np


@dataclass
class EvaluationResult:
    """Single query evaluation result."""
    query: str
    expected_answer: str
    generated_answer: str
    context_used: List[str]
    
    # Retrieval Metrics
    context_precision: float  # Relevant chunks / Total retrieved
    context_recall: float     # Relevant chunks retrieved / Total relevant
    
    # Generation Metrics
    answer_relevance: float   # Answer matches query intent
    faithfulness: float       # Answer supported by context
    
    # Performance Metrics
    retrieval_time: float
    generation_time: float
    total_tokens: int
    
    # Additional metadata
    sources_cited: List[str]
    confidence_score: float


class RAGEvaluator:
    """Evaluates RAG system performance."""
    
    def __init__(self, retriever, generator):
        self.retriever = retriever
        self.generator = generator
        self.results: List[EvaluationResult] = []
    
    def evaluate_query(self, query: str, expected_answer: str) -> EvaluationResult:
        """Evaluate single query."""
        # Time retrieval
        start = time.time()
        contexts = self.retriever.search(query, k=5)
        retrieval_time = time.time() - start
        
        # Time generation
        start = time.time()
        response = self.generator.generate(query, contexts)
        generation_time = time.time() - start
        
        # Calculate metrics (simplified versions)
        context_precision = self._calculate_context_precision(
            contexts, expected_answer
        )
        context_recall = self._calculate_context_recall(
            contexts, expected_answer
        )
        answer_relevance = self._calculate_answer_relevance(
            query, response['text']
        )
        faithfulness = self._calculate_faithfulness(
            response['text'], contexts
        )
        
        return EvaluationResult(
            query=query,
            expected_answer=expected_answer,
            generated_answer=response['text'],
            context_used=[c['text'][:200] for c in contexts],
            context_precision=context_precision,
            context_recall=context_recall,
            answer_relevance=answer_relevance,
            faithfulness=faithfulness,
            retrieval_time=retrieval_time,
            generation_time=generation_time,
            total_tokens=response.get('tokens', 0),
            sources_cited=response.get('sources', []),
            confidence_score=response.get('confidence', 0.0)
        )
    
    def _calculate_context_precision(self, contexts, expected) -> float:
        """Calculate precision of retrieved contexts."""
        if not contexts:
            return 0.0
        
        # Simple keyword overlap
        expected_words = set(expected.lower().split())
        relevant = 0
        
        for ctx in contexts:
            ctx_words = set(ctx['text'].lower().split())
            overlap = len(expected_words & ctx_words)
            if overlap > 2:  # Threshold
                relevant += 1
        
        return relevant / len(contexts)
    
    def _calculate_context_recall(self, contexts, expected) -> float:
        """Calculate recall of retrieved contexts."""
        # Simplified: Assume at least 1 relevant context should be retrieved
        precision = self._calculate_context_precision(contexts, expected)
        return min(1.0, precision * 2)  # Scale up
    
    def _calculate_answer_relevance(self, query, answer) -> float:
        """Calculate answer relevance to query."""
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & answer_words)
        return min(1.0, overlap / len(query_words))
    
    def _calculate_faithfulness(self, answer, contexts) -> float:
        """Calculate if answer is faithful to contexts."""
        if not contexts:
            return 0.0
        
        # Check if answer content appears in contexts
        answer_words = set(answer.lower().split())
        context_text = " ".join([c['text'].lower() for c in contexts])
        context_words = set(context_text.split())
        
        if not answer_words:
            return 0.0
        
        overlap = len(answer_words & context_words)
        return min(1.0, overlap / len(answer_words))
    
    def run_evaluation(self, test_cases: List[Dict[str, str]]) -> Dict[str, Any]:
        """Run evaluation on test set."""
        print(f"\n{'='*60}")
        print("🧪 RUNNING RAG EVALUATION")
        print(f"{'='*60}")
        print(f"Test cases: {len(test_cases)}\n")
        
        for i, test in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] {test['query'][:50]}...")
            result = self.evaluate_query(test['query'], test['expected'])
            self.results.append(result)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report."""
        if not self.results:
            return {}
        
        # Aggregate metrics
        metrics = {
            'context_precision': np.mean([r.context_precision for r in self.results]),
            'context_recall': np.mean([r.context_recall for r in self.results]),
            'answer_relevance': np.mean([r.answer_relevance for r in self.results]),
            'faithfulness': np.mean([r.faithfulness for r in self.results]),
            'avg_retrieval_time': np.mean([r.retrieval_time for r in self.results]),
            'avg_generation_time': np.mean([r.generation_time for r in self.results]),
            'total_tokens': sum([r.total_tokens for r in self.results]),
        }
        
        # RAGAS-like combined score
        metrics['ragas_score'] = (
            metrics['faithfulness'] * 0.3 +
            metrics['answer_relevance'] * 0.3 +
            metrics['context_precision'] * 0.2 +
            metrics['context_recall'] * 0.2
        )
        
        report = {
            'summary': metrics,
            'total_queries': len(self.results),
            'detailed_results': [
                {
                    'query': r.query,
                    'generated_answer': r.generated_answer[:200],
                    'context_precision': r.context_precision,
                    'context_recall': r.context_recall,
                    'answer_relevance': r.answer_relevance,
                    'faithfulness': r.faithfulness,
                }
                for r in self.results
            ]
        }
        
        return report
    
    def save_report(self, output_path: Path):
        """Save evaluation report to file."""
        report = self.generate_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Report saved: {output_path}")
        return report


# Test Cases for CUSB RAG
def get_cusb_test_cases() -> List[Dict[str, str]]:
    """Get test cases for CUSB RAG evaluation."""
    return [
        {
            "query": "CUSB kya hai?",
            "expected": "Central University of South Bihar is a central university located in Gaya, Bihar established in 2009."
        },
        {
            "query": "M.Sc Statistics ki fees kitni hai?",
            "expected": "M.Sc Statistics fees is Rs. 26,072 for 2 years."
        },
        {
            "query": "Hostel fee kitni hai?",
            "expected": "Hostel fee is Rs. 9,000 per semester and mess charges are Rs. 3,000 per month."
        },
        {
            "query": "Statistics department ke faculty kaun hain?",
            "expected": "Prof. Sunit Kumar is the Head of Statistics department."
        },
        {
            "query": "Admission process kya hai?",
            "expected": "Admission is through CUET entrance exam. Students apply online, appear for exam, and selected candidates get admission offers."
        },
        {
            "query": "CUSB ka NAAC grade kya hai?",
            "expected": "CUSB has NAAC A++ grade."
        },
        {
            "query": "M.Sc kitne courses hain CUSB mein?",
            "expected": "CUSB offers 25+ M.Sc programs including Mathematics, Statistics, Computer Science, Biotechnology, Chemistry, Physics, and more."
        },
        {
            "query": "Environmental Sciences ke HOD kaun hai?",
            "expected": "Dr. Pradeep Kumar is the Head of Environmental Sciences department."
        },
        {
            "query": "CUET kya hai?",
            "expected": "CUET is Common University Entrance Test, a national level entrance exam for UG and PG admissions."
        },
        {
            "query": "PhD ki fees kitni hai?",
            "expected": "PhD fees are approximately Rs. 7,600 per semester including tuition, exam, and other fees."
        },
    ]


if __name__ == "__main__":
    print("=" * 70)
    print("🔬 CUSB RAG EVALUATION FRAMEWORK")
    print("=" * 70)
    print("\nThis framework provides:")
    print("  • Retrieval metrics (Precision, Recall)")
    print("  • Generation metrics (Relevance, Faithfulness)")
    print("  • Performance metrics (Latency, Token usage)")
    print("  • RAGAS-like combined scoring")
    print("\nUsage:")
    print("  from evaluation_framework import RAGEvaluator, get_cusb_test_cases")
    print("  evaluator = RAGEvaluator(retriever, generator)")
    print("  report = evaluator.run_evaluation(get_cusb_test_cases())")
    print("  evaluator.save_report(Path('reports/evaluation_report.json'))")
    print("\n" + "=" * 70)
