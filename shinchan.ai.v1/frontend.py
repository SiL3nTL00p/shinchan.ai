"""
frontend.py - Streamlit UI for Shinchan AI

Responsibility: Provide an Apple Notes-inspired conversational interface
for querying transaction data and viewing insights.

Run: streamlit run frontend.py
"""

import streamlit as st
import time
import os
import sys
from dotenv import load_dotenv

# Load .env before importing engine modules
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import InsightXEngine
from loguru import logger


# ─────────────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Shinchan AI",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────
# Custom CSS - Apple Notes Style (EXACT MATCH)
# ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Black Background ── */
    .stApp {
        background: #000000 !important;
        overflow: hidden !important;
    }
    
    /* Hide main scrollbar */
    .main {
        overflow: hidden !important;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── White Box (Apple Notes Style) ── */
    .block-container {
        background: #ffffff !important;
        border-radius: 12px !important;
        max-width: 900px !important;
        width: 90vw !important;
        min-height: 82vh !important;
        margin: 30px auto 0 auto !important;
        padding: 0 !important;
        overflow: hidden !important;
        display: flex !important;
        flex-direction: column !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5) !important;
        position: relative !important;
    }
    
    /* ── Header with Traffic Lights (Full Width, Fixed, Not Scrollable) ── */
    .notes-header {
        background: #f5f5f5 !important;
        border-bottom: 1px solid #d1d1d6 !important;
        padding: 14px 20px !important;
        flex-shrink: 0 !important;
        width: 100% !important;
        margin: 0 !important;
        position: sticky !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 1000 !important;
    }
    
    .traffic-lights {
        display: flex;
        gap: 8px;
    }
    
    .dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
    }
    
    .dot-red { background: #ff5f56; }
    .dot-yellow { background: #ffbd2e; }
    .dot-green { background: #27c93f; }

    /* ── HIDE AVATARS (all possible selectors) ── */
    [data-testid="stChatMessageAvatarUser"],
    [data-testid="stChatMessageAvatarAssistant"],
    .stChatMessage [data-testid*="avatar"],
    .stChatMessage [data-testid*="Avatar"],
    .stChatMessage img[data-testid],
    .stChatMessage svg,
    [data-testid="stChatMessage"] > div:first-child > img,
    [data-testid="stChatMessage"] [class*="avatar"],
    [data-testid="stChatMessage"] [class*="Avatar"],
    .st-emotion-cache-janbn0,
    .st-emotion-cache-4oy321 {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
        visibility: hidden !important;
        position: absolute !important;
    }

    /* ── Scrollable Content Area ── */
    .block-container > div:first-child {
        flex: 1 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding: 30px 50px !important;
        background: #ffffff !important;
    }

    /* ── Chat Messages ── */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 6px 0 !important;
        margin-bottom: 16px !important;
        gap: 0 !important;
    }

    /* Remove gap between avatar slot and content */
    [data-testid="stChatMessage"] > div {
        gap: 0 !important;
    }

    /* USER (Blue, Right) */
    [data-testid="stChatMessage"][data-testid*="user"] {
        display: flex !important;
        justify-content: flex-end !important;
        padding-left: 20% !important;
    }
    
    [data-testid="stChatMessage"][data-testid*="user"] > div {
        max-width: 100% !important;
        width: fit-content !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-end !important;
    }

    [data-testid="stChatMessage"][data-testid*="user"] .stMarkdown {
        background: #007AFF !important;
        color: #ffffff !important;
        border-radius: 20px 20px 6px 20px !important;
        padding: 12px 18px !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important;
        font-size: 15px !important;
        line-height: 1.5 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        display: inline-block !important;
        text-align: left !important;
        width: fit-content !important;
        max-width: 100% !important;
        word-wrap: break-word !important;
    }

    [data-testid="stChatMessage"][data-testid*="user"] .stMarkdown p {
        margin: 0 !important;
        color: #ffffff !important;
    }

    /* AI (Gray, Left) */
    [data-testid="stChatMessage"]:not([data-testid*="user"]) {
        display: flex !important;
        justify-content: flex-start !important;
        padding-right: 10% !important;
    }

    [data-testid="stChatMessage"]:not([data-testid*="user"]) > div {
        max-width: 100% !important;
        width: fit-content !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
    }

    [data-testid="stChatMessage"]:not([data-testid*="user"]) .stMarkdown {
        background: #E9E9EB !important;
        color: #000000 !important;
        border-radius: 20px 20px 20px 6px !important;
        padding: 12px 18px !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important;
        font-size: 15px !important;
        line-height: 1.5 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06) !important;
        display: inline-block !important;
        width: fit-content !important;
        max-width: 100% !important;
        word-wrap: break-word !important;
    }

    [data-testid="stChatMessage"]:not([data-testid*="user"]) .stMarkdown p {
        margin: 0 !important;
        color: #000000 !important;
    }

    /* ── Message Status ── */
    .message-status {
        font-size: 11px;
        color: #86868b;
        text-align: right;
        margin-top: 4px !important;
        padding-top: 0 !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
    }

    /* ── Fixed Input Bar ── */
    .stChatFloatingInputContainer {
        flex-shrink: 0 !important;
        background: #ffffff !important;
        border-top: 1px solid #e5e5e5 !important;
        padding: 16px 40px 20px 40px !important;
        margin: 0 auto !important;
        max-width: 900px !important;
        border-radius: 0 0 12px 12px !important;
    }

    [data-testid="stChatInput"] {
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    [data-testid="stChatInput"] textarea {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important;
        font-size: 15px !important;
        color: #1c1c1e !important;
        border: 1px solid #d1d1d6 !important;
        border-radius: 22px !important;
        background: #f5f5f7 !important;
        padding: 11px 20px !important;
        min-height: 42px !important;
        max-height: 120px !important;
        resize: none !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #8e8e93 !important;
    }

    [data-testid="stChatInput"] button {
        color: #007AFF !important;
        background: transparent !important;
        border: none !important;
        font-size: 24px !important;
    }

    [data-testid="stChatInput"] button:hover {
        background: rgba(0, 122, 255, 0.08) !important;
        border-radius: 50% !important;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        font-size: 13px !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important;
        color: #007AFF !important;
        background: transparent !important;
        border: none !important;
        padding: 6px 0 !important;
        margin-top: 6px !important;
    }

    .streamlit-expanderContent {
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
    }

    /* ── Caption / Stats ── */
    .stCaption {
        color: #86868b !important;
        font-size: 11px !important;
        margin-top: 6px !important;
        margin-bottom: 0 !important;
        padding: 0 !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important;
        background: transparent !important;
    }

    /* ── Code Blocks ── */
    code {
        font-family: 'SF Mono', Monaco, monospace !important;
        font-size: 13px !important;
        background: rgba(0, 0, 0, 0.05) !important;
        border-radius: 4px !important;
        padding: 2px 5px !important;
    }

    pre code {
        display: block !important;
        padding: 14px !important;
        background: #f5f5f7 !important;
        border-radius: 8px !important;
        overflow-x: auto !important;
    }

    /* ── Welcome Screen ── */
    .welcome-area {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 100px 30px 30px 30px;
        text-align: center;
    }
    
    .welcome-area h1 {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
        font-size: 38px;
        font-weight: 600;
        color: #1c1c1e;
        margin-bottom: 10px;
    }
    
    .welcome-area p {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
        font-size: 17px;
        color: #86868b;
        line-height: 1.5;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: #f9f9f9; }
    ::-webkit-scrollbar-thumb { background: #d1d1d6; border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: #b1b1b6; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #1c1c1e !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #e5e5e7 !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important;
    }
    
    [data-testid="stSidebar"] hr {
        border-color: #38383a !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #007AFF !important;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Header Bar
# ─────────────────────────────────────────────────────────
st.markdown("""
<div class="notes-header">
    <div class="traffic-lights">
        <div class="dot dot-red"></div>
        <div class="dot dot-yellow"></div>
        <div class="dot dot-green"></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Initialize Engine
# ─────────────────────────────────────────────────────────
@st.cache_resource
def init_engine():
    """Initialize the engine (cached across reruns)."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config = {
            'data_path': os.path.join(base_dir, '250k_transactions.csv'),
            'hypothesis_path': os.path.join(base_dir, 'hypotheses.json'),
        }
        engine = InsightXEngine(config)
        return engine
    except Exception as e:
        st.error(f"Failed to initialize engine: {e}")
        return None


# ─────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []

engine = init_engine()

if engine is None:
    st.error(
        "Could not initialize the analytics engine. "
        "Please ensure the dataset file (250k_transactions.csv) exists "
        "and the GROQ_API_KEY environment variable is set."
    )
    st.stop()


# ─────────────────────────────────────────────────────────
# Welcome Screen
# ─────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-area">
        <h1>💬</h1>
        <h1>Shinchan AI</h1>
        <p>What would you like to know?</p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Display Messages
# ─────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "user":
            st.markdown('<div class="message-status">Delivered</div>', unsafe_allow_html=True)

        if msg["role"] == "assistant" and "metadata" in msg:
            meta = msg["metadata"]

            stats_parts = []
            if meta.get('execution_time_ms'):
                stats_parts.append(f"⏱ {meta['execution_time_ms']:.0f}ms")
            if meta.get('rows_returned'):
                stats_parts.append(f"📊 {meta['rows_returned']} rows")
            if meta.get('top_hypothesis'):
                stats_parts.append(
                    f"🧠 {meta['top_hypothesis']['name']} "
                    f"({meta['top_hypothesis']['score']:.0%})"
                )
            if stats_parts:
                st.caption(" · ".join(stats_parts))

            if meta.get('sql'):
                with st.expander("📋 View SQL"):
                    st.code(meta['sql'], language='sql')

            if meta.get('signals'):
                with st.expander("🔍 Signals"):
                    st.write(", ".join(meta['signals']))


# ─────────────────────────────────────────────────────────
# Chat Input
# ─────────────────────────────────────────────────────────
user_input = st.chat_input("iMessage")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)
        st.markdown('<div class="message-status">Delivered</div>', unsafe_allow_html=True)

    with st.chat_message("assistant"):
        with st.spinner("💭"):
            result = engine.process_query(user_input)

        st.markdown(result['insight'])

        metadata = {
            'sql': result.get('sql'),
            'execution_time_ms': result.get('execution_time_ms', 0),
            'rows_returned': len(result.get('data', [])),
            'signals': result.get('signals', []),
            'top_hypothesis': (
                result['hypotheses'][0] if result.get('hypotheses') else None
            ),
        }

        stats_parts = []
        if metadata['execution_time_ms']:
            stats_parts.append(f"⏱ {metadata['execution_time_ms']:.0f}ms")
        if metadata['rows_returned']:
            stats_parts.append(f"📊 {metadata['rows_returned']} rows")
        if metadata['top_hypothesis']:
            stats_parts.append(
                f"🧠 {metadata['top_hypothesis']['name']} "
                f"({metadata['top_hypothesis']['score']:.0%})"
            )
        if stats_parts:
            st.caption(" · ".join(stats_parts))

        if result.get('sql'):
            with st.expander("📋 View SQL"):
                st.code(result['sql'], language='sql')

        if result.get('signals'):
            with st.expander("🔍 Signals"):
                st.write(", ".join(result['signals']))

    st.session_state.messages.append({
        "role": "assistant",
        "content": result['insight'],
        "metadata": metadata,
    })


# ─────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ System Info")

    if engine:
        try:
            stats = engine.get_system_stats()
            st.metric("📊 Rows", f"{stats['database']['row_count']:,}")
            st.metric("📋 Columns", stats['database']['column_count'])
            st.metric("🧠 Hypotheses", stats['hypotheses_loaded'])
            st.metric("💬 Queries", stats['history_length'])
            st.metric("⚡ Cache", stats['executor']['cache_size'])
        except Exception:
            st.write("Stats unavailable")

    st.markdown("---")
    st.markdown(
        "**Shinchan AI** v1.0  \n"
        "Llama 3.3 70B (Groq)  \n"
        "DuckDB + Streamlit"
    )

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()