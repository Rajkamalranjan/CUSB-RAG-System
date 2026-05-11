"""
CUSB AI Assistant - Professional Interface
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
    page_title="CUSB AI Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Professional CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Global styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main container */
    .main {
        max-width: 900px;
        margin: 0 auto;
        padding: 0 1rem !important;
    }

    /* Header gradient */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem 1rem;
        margin: -1rem -1rem 2rem -1rem;
        text-align: center;
        border-radius: 0 0 24px 24px;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.25);
    }
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 400;
    }

    /* Chat messages */
    .stChatMessage {
        padding: 1rem 0;
        border-radius: 0;
        background: transparent !important;
    }

    /* User message - RIGHT side */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: transparent !important;
        text-align: right;
    }
    .stChatMessage[data-testid="stChatMessageUser"] .stChatMessageContent {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px 20px 4px 20px;
        padding: 14px 18px;
        max-width: 65%;
        margin-left: auto;
        display: inline-block;
        text-align: left;
        font-weight: 500;
        font-size: 0.95rem;
        box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3);
    }

    /* Assistant message - LEFT side */
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: transparent !important;
        text-align: left;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] .stChatMessageContent {
        background-color: #ffffff;
        color: #1f2937;
        border-radius: 20px 20px 20px 4px;
        padding: 18px;
        max-width: 80%;
        margin-right: auto;
        display: inline-block;
        text-align: left;
        font-size: 0.95rem;
        line-height: 1.6;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    /* Chat input */
    .stChatInput {
        border-radius: 28px;
        border: 2px solid #e5e7eb;
        padding: 16px 20px;
        max-width: 900px;
        margin: 0 auto;
        background: white;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
    }
    .stChatInput:focus-within {
        border-color: #667eea;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
    }
    .stChatInput textarea {
        border: none !important;
        background: transparent !important;
        font-size: 1rem;
    }

    /* Welcome screen */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 1rem 3rem 1rem;
        text-align: center;
    }
    .welcome-icon {
        font-size: 4rem;
        margin-bottom: 1.5rem;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    .welcome-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.75rem;
        letter-spacing: -0.5px;
    }
    .welcome-subtitle {
        color: #6b7280;
        font-size: 1.1rem;
        margin-bottom: 3rem;
        max-width: 500px;
        line-height: 1.6;
    }

    /* Suggestion cards */
    .suggestions-container {
        max-width: 700px;
        margin: 0 auto;
        width: 100%;
    }
    .suggestions-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1rem;
        text-align: center;
    }

    /* Buttons */
    .stButton button {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 16px 20px;
        font-weight: 500;
        color: #374151;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        width: 100%;
        text-align: left;
        white-space: pre-line;
        line-height: 1.5;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: transparent;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        transform: translateY(-2px);
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 1rem;
        margin-top: 2rem;
        border-top: 1px solid #f3f4f6;
    }
    .footer-text {
        font-size: 0.85rem;
        color: #9ca3af;
    }
    .footer-link {
        color: #667eea;
        text-decoration: none;
        font-weight: 500;
    }

    /* Spinner */
    .stSpinner > div {
        border-color: #667eea transparent transparent transparent;
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

# Header (always visible)
st.markdown("""
<div class="header-container">
    <div class="header-title">🎓 CUSB AI Assistant</div>
    <div class="header-subtitle">Central University of South Bihar — Ask anything about courses, fees, admissions & more</div>
</div>
""", unsafe_allow_html=True)

# Suggestions for welcome screen
SUGGESTIONS = [
    ("🎓 CUSB kya hai?", "University ke baare mein jaano"),
    ("💰 Hostel fees kitni hai?", "Hostel charges ka details"),
    ("📝 Admission process kya hai?", "CUET se admission steps"),
    ("📚 M.Sc courses ki list do", "Available programmes dekho"),
]

# Welcome screen (only when no messages)
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-icon">🎓</div>
        <div class="welcome-title">How can I help you today?</div>
        <div class="welcome-subtitle">Ask me anything about CUSB — courses, fees, admissions, faculty, placements & more</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="suggestions-title">Try asking</div>', unsafe_allow_html=True)

    # Suggestion cards
    cols = st.columns(2)
    for i, (title, desc) in enumerate(SUGGESTIONS):
        with cols[i % 2]:
            if st.button(f"{title}\n{desc}", key=f"s_{i}", use_container_width=True):
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

# Footer
st.markdown("""
<div class="footer">
    <div class="footer-text">
        Powered by RAG + LLM | <a href="https://www.cusb.ac.in" target="_blank" class="footer-link">CUSB Official</a>
    </div>
</div>
""", unsafe_allow_html=True)
