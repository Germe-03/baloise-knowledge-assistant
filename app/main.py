"""
Baloise Knowledge Assistant
Chatbot mit RAG und Schadensmeldung

Version 1.0 - Baloise Edition
"""

import streamlit as st
from pathlib import Path

# Pfad-Setup für relative Imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config


# Seiten-Konfiguration (MUSS zuerst kommen)
st.set_page_config(
    page_title="Baloise Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Imports nach set_page_config
from app.components.chat import render_chat_interface, render_chat_settings
from app.components.knowledge_manager import render_knowledge_manager
# Admin Panel entfernt
from app.components.schadensmeldung import render_schadensmeldung, render_schadensmeldungen_liste

# Auth entfernt - direkter Zugang
from app.components.icons import inject_icon_css


def apply_baloise_css():
    """Baloise Corporate Design"""
    st.markdown("""
    <style>
        /* === RESET & BASE === */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

        .stApp {
            background-color: #f5f7fa;
        }

        /* Header komplett weg */
        header[data-testid="stHeader"] {
            display: none !important;
        }

        footer {
            display: none !important;
        }

        /* === SIDEBAR === */
        button[data-testid="stSidebarCollapseButton"],
        button[data-testid="collapsedControl"] {
            display: none !important;
        }

        section[data-testid="stSidebar"] {
            background-color: #003366 !important;
            border-right: none;
            transform: none !important;
            width: 280px !important;
            min-width: 280px !important;
        }

        section[data-testid="stSidebar"] > div:first-child {
            background-color: #003366;
            padding-top: 0.5rem;
        }

        /* Sidebar Text weiss */
        section[data-testid="stSidebar"] * {
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] .stMarkdown span,
        section[data-testid="stSidebar"] label {
            color: rgba(255,255,255,0.7) !important;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        /* Sidebar Buttons */
        section[data-testid="stSidebar"] .stButton > button {
            background-color: transparent !important;
            border: none !important;
            border-radius: 8px;
            color: rgba(255,255,255,0.8) !important;
            text-align: left;
            padding: 0.75rem 1rem;
            font-size: 0.9rem;
            font-weight: 400;
            width: 100%;
            justify-content: flex-start;
            transition: all 0.15s ease;
        }

        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: rgba(255,255,255,0.1) !important;
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
            background-color: #e63312 !important;
            color: #ffffff !important;
            font-weight: 500;
        }

        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.1);
            margin: 1.5rem 0;
        }

        /* === MAIN CONTENT === */
        .main .block-container {
            padding: 2rem 3rem;
            max-width: 1000px;
            margin: 0 auto;
        }

        h1, h2, h3 {
            color: #003366;
            font-family: 'Inter', -apple-system, sans-serif;
            font-weight: 600;
        }

        /* === BUTTONS (Main Area) === */
        .main .stButton > button {
            background-color: #003366 !important;
            border: none !important;
            border-radius: 8px;
            color: #ffffff !important;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            transition: all 0.15s ease;
        }

        .main .stButton > button:hover {
            background-color: #002244 !important;
            transform: translateY(-1px);
        }

        .main .stButton > button[kind="primary"] {
            background-color: #e63312 !important;
        }

        .main .stButton > button[kind="primary"]:hover {
            background-color: #c42a0e !important;
        }

        /* === INPUTS === */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div {
            border: 1px solid #e0e5eb;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            background-color: #ffffff;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #003366;
            box-shadow: 0 0 0 3px rgba(0, 51, 102, 0.1);
        }

        /* === CHAT === */
        .stChatMessage {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #e0e5eb;
        }

        /* === CARDS === */
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            border-radius: 12px !important;
            border: 1px solid #e0e5eb !important;
            background-color: #ffffff !important;
        }

        /* === ALERTS === */
        .stAlert {
            border-radius: 10px;
            border: none;
        }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Baloise Sidebar Navigation"""
    current_page = st.session_state.get("current_page", "chat")

    with st.sidebar:
        # Logo
        st.markdown("#### 🛡️ Baloise Assistant")

        st.divider()

        # Hauptnavigation
        nav_items = [
            ("chat", "💬 Chat"),
            ("schadensmeldung", "📋 Schadensmeldung"),
            ("schaden_liste", "📁 Meine Schäden"),
            ("knowledge", "📚 Wissensbasis"),
        ]

        for page_id, label in nav_items:
            btn_type = "primary" if current_page == page_id else "secondary"
            if st.button(label, key=f"nav_{page_id}", use_container_width=True, type=btn_type):
                st.session_state.current_page = page_id
                st.rerun()

            # Chat-Historie unter Chat-Button
            if page_id == "chat":
                render_chat_settings()



def render_main_content():
    """Rendert den Hauptinhalt basierend auf aktueller Seite"""
    page = st.session_state.get("current_page", "chat")

    if page == "chat":
        render_chat_interface()

    elif page == "schadensmeldung":
        render_schadensmeldung()

    elif page == "schaden_liste":
        render_schadensmeldungen_liste()

    elif page == "knowledge":
        render_knowledge_manager()


def init_all_states():
    """Initialisiert alle Session-States"""
    defaults = {
        "authenticated": False,
        "current_user": None,
        "messages": [],
        "selected_knowledge_bases": [],
        "current_page": "chat"
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main():
    """Hauptfunktion"""
    init_all_states()

    apply_baloise_css()
    inject_icon_css()

    # Direkt starten ohne Login
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()
