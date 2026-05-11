"""
CUSB AI Assistant - ChatGPT-like Interface
Run: streamlit run streamlit_app.py
"""

import sys
import time
from pathlib import Path

# Fix Windows Unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

# Page config
st.set_page_config(
    page_title="CUSB AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ChatGPT-like CSS
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container */
    .main {
        max-width: 800px;
        margin: 0 auto;
        padding: 0 !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        padding: 1.5rem 0;
        border-radius: 0;
        background: transparent !important;
    }
    
    /* User message */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: transparent !important;
    }
    .stChatMessage[data-testid="stChatMessageUser"] .stChatMessageContent {
        background-color: #f7f7f8;
        border-radius: 20px;
        padding: 12px 16px;
        max-width: 70%;
        margin-left: auto;
    }
    
    /* Assistant message */
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: transparent !important;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] .stChatMessageContent {
        background-color: transparent;
        padding: 0;
        max-width: 100%;
    }
    
    /* Chat input */
    .stChatInput {
        border-radius: 24px;
        border: 1px solid #d1d5db;
        padding: 12px 16px;
        max-width: 800px;
        margin: 0 auto;
    }
    .stChatInput textarea {
        border: none !important;
        background: transparent !important;
    }
    
    /* Title styling */
    .chat-title {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .chat-title h1 {
        font-size: 1.8rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .chat-title p {
        color: #6b7280;
        font-size: 0.95rem;
    }
    
    /* Welcome screen */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem 1rem;
        text-align: center;
    }
    .welcome-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .welcome-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .welcome-subtitle {
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }
    
    /* Suggestion cards */
    .suggestion-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        max-width: 600px;
        margin: 0 auto;
    }
    .suggestion-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.2s;
        text-align: left;
    }
    .suggestion-card:hover {
        background: #f3f4f6;
        border-color: #d1d5db;
    }
    .suggestion-title {
        font-weight: 600;
        color: #1f2937;
        font-size: 0.9rem;
        margin-bottom: 4px;
    }
    .suggestion-desc {
        color: #6b7280;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize RAG pipeline
@st.cache_resource
def get_rag_pipeline():
    import os
    # Debug: Show if API keys are loaded
    groq_key = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    provider = os.getenv("LLM_PROVIDER", "not set")

    if not groq_key and not gemini_key:
        st.error("❌ API keys not found! Add secrets in Streamlit Cloud Settings.")
        st.info("Go to: Settings → Secrets → Add your API keys")
        return None

    from rag_engine import RAGPipeline
    return RAGPipeline()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Suggestions for welcome screen
SUGGESTIONS = [
    ("🎓 CUSB kya hai?", "University ke baare mein jaano"),
    ("💰 Hostel fees kitni hai?", "Hostel charges ka details"),
    ("📝 Admission process kya hai?", "CUET se admission steps"),
    ("📚 M.Sc courses ki list do", "Available programmes dekho"),
    ("👨‍🏫 Faculty kaun hain?", "Professors ki jaankari"),
    ("🏆 NAAC grade kya hai?", "Accreditation status"),
]

# Welcome screen (only when no messages)
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-icon">🎓</div>
        <div class="welcome-title">CUSB AI Assistant</div>
        <div class="welcome-subtitle">Central University of South Bihar — Courses, Fees, Admissions & more</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Suggestion cards
    cols = st.columns(2)
    for i, (title, desc) in enumerate(SUGGESTIONS[:4]):
        with cols[i % 2]:
            if st.button(f"**{title}**\n{desc}", key=f"s_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": title})
                st.rerun()

# Chat history display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about CUSB..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner(""):
            try:
                rag = get_rag_pipeline()
                if rag is None:
                    st.error("❌ API keys not configured. Please add secrets in Settings.")
                else:
                    result = rag.answer(prompt)
                    answer = result.get("answer", "Sorry, I couldn't find an answer.")
                    st.write(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Please try again or contact support.")
