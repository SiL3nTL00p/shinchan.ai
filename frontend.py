"""
frontend.py - Streamlit UI for InsightX Analytics

Responsibility: Provide an Apple-inspired conversational interface
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
    page_title="InsightX Analytics",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────
# Custom CSS - Apple-inspired dark theme
# ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark gradient background */
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main chat container */
    .chat-window {
        background: #ffffff;
        border-radius: 16px;
        padding: 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 2px 8px rgba(0, 0, 0, 0.2);
        margin: 0 auto;
        max-width: 800px;
        overflow: hidden;
    }

    /* Window title bar */
    .title-bar {
        background: linear-gradient(180deg, #e8e8e8 0%, #d4d4d4 100%);
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid #c0c0c0;
    }

    /* Traffic light dots */
    .window-controls {
        display: flex;
        gap: 8px;
        align-items: center;
    }
    .dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-red { background: #ff5f56; border: 1px solid #e0443e; }
    .dot-yellow { background: #ffbd2e; border: 1px solid #dea123; }
    .dot-green { background: #27c93f; border: 1px solid #1aab29; }

    /* Window title */
    .window-title {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
        font-size: 13px;
        font-weight: 500;
        color: #4a4a4a;
        flex: 1;
        text-align: center;
    }

    /* Chat messages */
    .chat-body {
        padding: 24px;
        min-height: 400px;
        max-height: 600px;
        overflow-y: auto;
        background: #fafafa;
    }

    .message {
        margin-bottom: 16px;
        display: flex;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        line-height: 1.5;
    }

    .message-user {
        justify-content: flex-end;
    }

    .message-assistant {
        justify-content: flex-start;
    }

    .bubble {
        max-width: 85%;
        padding: 10px 16px;
        border-radius: 18px;
        word-wrap: break-word;
    }

    .bubble-user {
        background: #007AFF;
        color: white;
        border-bottom-right-radius: 4px;
    }

    .bubble-assistant {
        background: #e9e9eb;
        color: #1c1c1e;
        border-bottom-left-radius: 4px;
    }

    .timestamp {
        font-size: 11px;
        color: #8e8e93;
        margin-top: 4px;
        text-align: center;
    }

    /* Stats badges */
    .stats-row {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        flex-wrap: wrap;
    }
    .stat-badge {
        background: #f0f0f5;
        border-radius: 12px;
        padding: 4px 10px;
        font-size: 11px;
        color: #636366;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
    }

    /* Override Streamlit chat styling */
    .stChatMessage {
        background: transparent !important;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 13px !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important;
    }

    /* Welcome message */
    .welcome-msg {
        text-align: center;
        padding: 40px 20px;
        color: #8e8e93;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
    }
    .welcome-msg h2 {
        color: #1c1c1e;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .welcome-msg p {
        font-size: 14px;
        line-height: 1.6;
    }

    /* Sample queries */
    .sample-queries {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 16px;
        align-items: center;
    }
    .sample-query {
        background: #f0f0f5;
        border: 1px solid #e0e0e5;
        border-radius: 12px;
        padding: 8px 16px;
        font-size: 13px;
        color: #007AFF;
        cursor: pointer;
        text-align: center;
        max-width: 400px;
    }

    /* Loading animation */
    .thinking {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 8px 16px;
    }
    .thinking-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #8e8e93;
        animation: thinking 1.4s infinite ease-in-out both;
    }
    .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
    .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
    @keyframes thinking {
        0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Initialize Engine (cached)
# ─────────────────────────────────────────────────────────
@st.cache_resource
def init_engine():
    """Initialize the InsightX engine (cached across reruns)."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config = {
            'data_path': os.path.join(base_dir, '250k_transactions.csv'),
            'hypothesis_path': os.path.join(base_dir, 'hypotheses.json'),
        }
        engine = InsightXEngine(config)
        return engine
    except Exception as e:
        st.error(f"Failed to initialize InsightX: {e}")
        return None


# ─────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []


# ─────────────────────────────────────────────────────────
# UI Layout
# ─────────────────────────────────────────────────────────

# Window title bar with traffic light dots
st.markdown("""
<div class="chat-window">
    <div class="title-bar">
        <div class="window-controls">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
        </div>
        <div class="window-title">InsightX Analytics</div>
        <div style="width: 52px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize engine
engine = init_engine()

if engine is None:
    st.error(
        "Could not initialize the analytics engine. "
        "Please ensure the dataset file (250k_transactions.csv) exists "
        "and the GROQ_API_KEY environment variable is set."
    )
    st.stop()

# Welcome message if no conversation yet
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-msg">
        <h2>📊 InsightX Analytics</h2>
        <p>Ask me anything about your transaction data.<br>
        I'll analyze patterns, identify root causes, and provide actionable insights.</p>
    </div>
    """, unsafe_allow_html=True)

    # Sample queries as buttons
    sample_queries = [
        "What's the overall failure rate by transaction type?",
        "How do failure rates compare between Android and iOS?",
        "Show me weekend vs weekday failure rates",
        "Which banks have the highest fraud flag rates?",
        "What are the peak transaction hours?",
    ]

    cols = st.columns(1)
    for sq in sample_queries:
        if st.button(f"💡 {sq}", key=f"sample_{sq}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": sq})
            st.rerun()

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show SQL and metadata for assistant messages
        if msg["role"] == "assistant" and "metadata" in msg:
            meta = msg["metadata"]

            # Stats row
            stats_parts = []
            if meta.get('execution_time_ms'):
                stats_parts.append(f"⏱ {meta['execution_time_ms']:.0f}ms")
            if meta.get('rows_returned'):
                stats_parts.append(f"📋 {meta['rows_returned']} rows")
            if meta.get('top_hypothesis'):
                stats_parts.append(
                    f"🧠 {meta['top_hypothesis']['name']} "
                    f"({meta['top_hypothesis']['score']:.0%})"
                )
            if stats_parts:
                st.caption(" · ".join(stats_parts))

            # SQL expander
            if meta.get('sql'):
                with st.expander("📋 View Generated SQL"):
                    st.code(meta['sql'], language='sql')

            # Signals expander
            if meta.get('signals'):
                with st.expander("📡 Detected Signals"):
                    st.write(", ".join(meta['signals']))


# ─────────────────────────────────────────────────────────
# Chat Input
# ─────────────────────────────────────────────────────────
user_input = st.chat_input("Ask about transaction patterns...")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    # Process query
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):
            result = engine.process_query(user_input)

        # Display insight
        st.markdown(result['insight'])

        # Build metadata
        metadata = {
            'sql': result.get('sql'),
            'execution_time_ms': result.get('execution_time_ms', 0),
            'rows_returned': len(result.get('data', [])),
            'signals': result.get('signals', []),
            'top_hypothesis': (
                result['hypotheses'][0] if result.get('hypotheses') else None
            ),
        }

        # Stats
        stats_parts = []
        if metadata['execution_time_ms']:
            stats_parts.append(f"⏱ {metadata['execution_time_ms']:.0f}ms")
        if metadata['rows_returned']:
            stats_parts.append(f"📋 {metadata['rows_returned']} rows")
        if metadata['top_hypothesis']:
            stats_parts.append(
                f"🧠 {metadata['top_hypothesis']['name']} "
                f"({metadata['top_hypothesis']['score']:.0%})"
            )
        if stats_parts:
            st.caption(" · ".join(stats_parts))

        # SQL expander
        if result.get('sql'):
            with st.expander("📋 View Generated SQL"):
                st.code(result['sql'], language='sql')

        # Signals expander
        if result.get('signals'):
            with st.expander("📡 Detected Signals"):
                st.write(", ".join(result['signals']))

    # Save assistant message with metadata
    st.session_state.messages.append({
        "role": "assistant",
        "content": result['insight'],
        "metadata": metadata,
    })


# ─────────────────────────────────────────────────────────
# Sidebar - System Info
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ System Info")

    if engine:
        try:
            stats = engine.get_system_stats()
            st.metric("Rows Loaded", f"{stats['database']['row_count']:,}")
            st.metric("Columns", stats['database']['column_count'])
            st.metric("Hypotheses", stats['hypotheses_loaded'])
            st.metric("Queries This Session", stats['history_length'])
            st.metric("Cache Size", stats['executor']['cache_size'])
        except Exception:
            st.write("Stats unavailable")

    st.markdown("---")
    st.markdown(
        "**InsightX Analytics** v1.0  \n"
        "Powered by Llama 3.1 70B via Groq  \n"
        "Built with DuckDB + Streamlit"
    )

    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.rerun()
