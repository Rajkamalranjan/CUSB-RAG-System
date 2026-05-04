"""
Step 3: Run the CUSB AI Chatbot (RAG).

Usage: python src/3_chatbot.py
       python src/3_chatbot.py --no-llm        # run without Gemini (offline mode)
       python src/3_chatbot.py --verbose        # show retrieved chunks per query
"""

import sys
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

# Make sure src/ is on the path when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

# ─── Load .env file (GEMINI_API_KEY lives here) ───────────────────────────────
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
# ──────────────────────────────────────────────────────────────────────────────

from rag_engine import RAGPipeline
from config import CHATBOT_MODEL

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLOR = True
except ImportError:
    COLOR = False


def c(text: str, color: str = "") -> str:
    if not COLOR:
        return text
    colors = {
        "cyan":   Fore.CYAN,
        "green":  Fore.GREEN,
        "yellow": Fore.YELLOW,
        "red":    Fore.RED,
        "bold":   Style.BRIGHT,
        "dim":    Style.DIM,
    }
    return colors.get(color, "") + text + Style.RESET_ALL


BANNER = """
╔══════════════════════════════════════════════════════╗
║      🎓  CUSB AI CHATBOT  (RAG System)               ║
║      Central University of South Bihar               ║
╚══════════════════════════════════════════════════════╝
  Type your question in Hindi, English, or Hinglish.
  Commands:
    /sources  — show retrieved chunks for last answer
    /verbose  — toggle verbose mode (on/off)
    /quit     — exit
"""

EXAMPLES = [
    "CUSB kya hai?",
    "Hostel fee kitni hai?",
    "Admission process kya hai?",
    "M.Sc Biotechnology ki fees kya hai?",
    "NAAC grade kya hai CUSB ka?",
]


def print_sources(sources: list[dict]):
    print(c("\n📚 Sources retrieved:", "dim"))
    for i, s in enumerate(sources, 1):
        bar = "█" * int(s["score"] * 20)
        print(c(f"  {i}. [{s['score']:.3f}] {bar}  {s['heading']}", "dim"))


def main():
    use_llm = "--no-llm" not in sys.argv
    verbose  = "--verbose" in sys.argv

    print(c(BANNER, "cyan"))

    print(c("💡 Example questions:", "yellow"))
    for ex in EXAMPLES:
        print(f"   • {ex}")
    print()

    # Initialize pipeline
    print(c("⏳ Loading RAG pipeline...", "yellow"))
    try:
        rag = RAGPipeline(use_llm=use_llm, model=CHATBOT_MODEL)
    except FileNotFoundError as e:
        print(c(str(e), "red"))
        sys.exit(1)

    print(c("\n✅ Ready! Ask your question.\n", "green"))

    last_result = None

    while True:
        try:
            query = input(c("You: ", "cyan")).strip()
        except (KeyboardInterrupt, EOFError):
            print(c("\n\n👋 Goodbye! CUSB website: https://www.cusb.ac.in", "yellow"))
            break

        if not query:
            continue

        # ── Commands ──────────────────────────────────────────
        if query.lower() in ("/quit", "/exit", "quit", "exit", "bye"):
            print(c("👋 Goodbye! CUSB website: https://www.cusb.ac.in", "yellow"))
            break

        if query.lower() == "/sources":
            if last_result:
                print_sources(last_result["sources"])
            else:
                print(c("⚠️  No previous answer yet.", "yellow"))
            continue

        if query.lower() == "/verbose":
            verbose = not verbose
            state = "ON" if verbose else "OFF"
            print(c(f"ℹ️  Verbose mode: {state}", "yellow"))
            continue

        # ── RAG Answer ────────────────────────────────────────
        print(c("🤔 Thinking...", "dim"))
        result = rag.answer(query, verbose=verbose)
        last_result = result

        print(c("\n🤖 CUSB Bot:", "green"))
        print(result["answer"])

        if verbose:
            print_sources(result["sources"])

        print()   # blank line between turns


if __name__ == "__main__":
    main()
