"""
CUSB AI Assistant - Streamlit Deployment
Run: streamlit run streamlit_app.py
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows Unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

# Page config
st.set_page_config(
    page_title="CUSB AI Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage { border-radius: 12px; }
    .stChatMessage[data-testid="stChatMessageUser"] { background-color: #2563eb !important; }
    .stChatMessage[data-testid="stChatMessageAssistant"] { background-color: #f1f5f9 !important; }
    .main-header { text-align: center; padding: 1rem 0; }
    .suggestion-btn { 
        border: 1px solid #e2e8f0; 
        border-radius: 20px; 
        padding: 6px 14px; 
        margin: 4px; 
        cursor: pointer;
        background: white;
        font-size: 13px;
        transition: all 0.3s;
    }
    .suggestion-btn:hover { 
        background: #2563eb; 
        color: white; 
        border-color: #2563eb;
    }
    .footer { 
        text-align: center; 
        font-size: 11px; 
        color: #64748b; 
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎓 CUSB AI Assistant</h1>
    <p style="color: #64748b;">Central University of South Bihar — Ask anything about courses, fees, admissions & more!</p>
</div>
""", unsafe_allow_html=True)

# Initialize RAG pipeline
@st.cache_resource
def get_rag_pipeline():
    from rag_engine import RAGPipeline
    return RAGPipeline()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Suggestion buttons
st.markdown("**Quick Questions:**")
cols = st.columns(3)
quick_questions = [
    "CUSB kya hai?",
    "Hostel fee kitni hai?",
    "M.Sc Statistics ki fees?",
    "Admission process?",
    "NAAC grade?",
    "Placement hota hai?",
]

for i, q in enumerate(quick_questions):
    with cols[i % 3]:
        if st.button(q, key=f"q_{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": q})

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
if prompt := st.chat_input("Type your question here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            try:
                rag = get_rag_pipeline()
                start = time.time()
                result = rag.query(prompt)
                elapsed = time.time() - start

                answer = result.get("answer", "Sorry, I couldn't find an answer.")
                sources = result.get("sources", [])

                st.write(answer)

                # Show sources in expander
                if sources:
                    with st.expander("📚 Sources"):
                        for src in sources:
                            heading = src.get("heading", "Unknown")
                            score = src.get("score", 0)
                            st.markdown(f"- **{heading}** (score: {score:.3f})")

                # Processing time
                st.caption(f"⏱️ {elapsed:.2f}s | Powered by RAG + LLM")

                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Please make sure the vector database is built. Run: `python src/1_build_chunks.py` and `python src/2_build_vectordb.py`")

# Footer
st.markdown("""
<div class="footer">
    CUSB Knowledge Base v2.0 | Built with Streamlit + RAG
</div>
""", unsafe_allow_html=True)
