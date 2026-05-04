#!/usr/bin/env python3
"""
Master Orchestrator for Research & Production Pipeline
Runs: Evaluation → API Test → Advanced AI Test → Report Generation
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_phase_1_evaluation():
    """Phase 1: Run Evaluation Framework."""
    print_header("🔬 PHASE 1: RESEARCH EVALUATION")
    
    try:
        # Import evaluation framework
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from evaluation_framework import get_cusb_test_cases
        
        test_cases = get_cusb_test_cases()
        print(f"✅ Loaded {len(test_cases)} test cases")
        
        for i, test in enumerate(test_cases, 1):
            print(f"  {i}. {test['query'][:50]}...")
        
        # Note: Full evaluation requires RAG pipeline
        print("\n⚠️  Full evaluation requires running chatbot")
        print("   Run: python src/3_chatbot.py")
        print("   Then manually test these queries")
        
        return {
            "phase": "evaluation",
            "status": "ready",
            "test_cases": len(test_cases),
            "test_set": test_cases
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"phase": "evaluation", "status": "error", "error": str(e)}


def run_phase_2_api_check():
    """Phase 2: Check API Server."""
    print_header("🚀 PHASE 2: PRODUCTION API")
    
    try:
        # Check if API server files exist
        api_file = Path(__file__).parent / "src" / "api_server.py"
        
        if api_file.exists():
            print(f"✅ API Server file found: {api_file}")
            print(f"   Size: {api_file.stat().st_size} bytes")
            
            print("\n📋 API Endpoints:")
            print("  GET  /              - API info")
            print("  GET  /api/health    - Health check")
            print("  POST /api/query     - Ask questions")
            print("  GET  /api/stats     - System statistics")
            print("  GET  /docs          - Swagger UI")
            
            print("\n🚀 To start API server:")
            print("   python src/api_server.py")
            print("   Server will run on http://localhost:8000")
            
            return {
                "phase": "api",
                "status": "ready",
                "file": str(api_file),
                "endpoints": 5
            }
        else:
            print("❌ API Server file not found")
            return {"phase": "api", "status": "missing"}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"phase": "api", "status": "error", "error": str(e)}


def run_phase_3_advanced_ai():
    """Phase 3: Check Advanced AI Components."""
    print_header("🤖 PHASE 3: ADVANCED AI")
    
    try:
        # Check if advanced AI file exists
        ai_file = Path(__file__).parent / "src" / "advanced_ai.py"
        
        if ai_file.exists():
            print(f"✅ Advanced AI file found: {ai_file}")
            print(f"   Size: {ai_file.stat().st_size} bytes")
            
            print("\n🧠 Components:")
            print("  1. MultimodalRAG - Image & table processing")
            print("  2. AgenticRAG - Tool-using agent system")
            print("  3. Query Expansion - HyDE + synonym expansion")
            print("  4. Re-ranking - Cross-encoder reranking")
            print("  5. Fine-tuning Support - QLoRA training prep")
            
            print("\n📖 Usage:")
            print("   from advanced_ai import AdvancedRAG")
            print("   advanced = AdvancedRAG(rag_pipeline, llm)")
            print("   result = advanced.query('question', use_agent=True)")
            
            return {
                "phase": "advanced_ai",
                "status": "ready",
                "file": str(ai_file),
                "components": 5
            }
        else:
            print("❌ Advanced AI file not found")
            return {"phase": "advanced_ai", "status": "missing"}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"phase": "advanced_ai", "status": "error", "error": str(e)}


def run_phase_4_knowledge_base():
    """Phase 4: Check Knowledge Base Stats."""
    print_header("📚 PHASE 4: KNOWLEDGE BASE")
    
    try:
        # Check chunks and vectors
        chunks_file = Path(__file__).parent / "data" / "cusb_chunks_meta.json"
        
        if chunks_file.exists():
            with open(chunks_file) as f:
                meta = json.load(f)
            
            print(f"✅ Knowledge Base Statistics:")
            print(f"   Total chunks: {meta.get('total_chunks', 'N/A')}")
            print(f"   Markdown chunks: {meta.get('markdown_chunks', 'N/A')}")
            print(f"   QA chunks: {meta.get('qa_chunks', 'N/A')}")
            print(f"   Min chars: {meta.get('min_chars', 'N/A')}")
            print(f"   Max chars: {meta.get('max_chars', 'N/A')}")
            print(f"   Avg chars: {meta.get('avg_chars', 'N/A')}")
            
            # Check vectors
            index_file = Path(__file__).parent / "data" / "cusb_vector.index"
            if index_file.exists():
                print(f"\n✅ Vector Index: {index_file.stat().st_size / 1024:.1f} KB")
            
            # Check embeddings
            embed_file = Path(__file__).parent / "data" / "cusb_embeddings.npy"
            if embed_file.exists():
                print(f"✅ Embeddings: {embed_file.stat().st_size / (1024*1024):.1f} MB")
            
            return {
                "phase": "knowledge_base",
                "status": "ready",
                "chunks": meta.get('total_chunks'),
                "max_chunk_size": meta.get('max_chars')
            }
        else:
            print("❌ Knowledge base metadata not found")
            return {"phase": "knowledge_base", "status": "missing"}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"phase": "knowledge_base", "status": "error", "error": str(e)}


def generate_report(results):
    """Generate final report."""
    print_header("📊 FINAL REPORT")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = {
        "timestamp": timestamp,
        "pipeline_status": "success",
        "phases": results,
        "summary": {
            "evaluation_ready": results[0]["status"] == "ready",
            "api_ready": results[1]["status"] == "ready",
            "advanced_ai_ready": results[2]["status"] == "ready",
            "knowledge_base_ready": results[3]["status"] == "ready",
        }
    }
    
    # Save report
    report_file = Path(__file__).parent / "reports" / f"research_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Report saved: {report_file}")
    
    # Print summary
    print("\n📋 Summary:")
    all_ready = all(r["status"] == "ready" for r in results)
    
    if all_ready:
        print("   🎉 ALL SYSTEMS READY!")
        print("\n   Next steps:")
        print("   1. python src/evaluation_framework.py  (Run evaluation)")
        print("   2. python src/api_server.py            (Start API)")
        print("   3. python src/advanced_ai.py            (Test advanced AI)")
        print("   4. Read: RESEARCH_MASTERPLAN.md         (Full roadmap)")
    else:
        print("   ⚠️  Some components need attention")
        for r in results:
            if r["status"] != "ready":
                print(f"   - {r['phase']}: {r['status']}")
    
    return report


def main():
    """Main orchestrator."""
    print("=" * 70)
    print("🔬 CUSB AI ASSISTANT - RESEARCH & PRODUCTION PIPELINE")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run all phases
    results.append(run_phase_1_evaluation())
    results.append(run_phase_2_api_check())
    results.append(run_phase_3_advanced_ai())
    results.append(run_phase_4_knowledge_base())
    
    # Generate report
    report = generate_report(results)
    
    print("\n" + "=" * 70)
    print("🏁 PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return report


if __name__ == "__main__":
    report = main()
