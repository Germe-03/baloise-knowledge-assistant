"""
KMU Knowledge Assistant - Token Display Component
Zeigt Token-Nutzung und verbleibende Kapazität an
"""

import streamlit as st
from typing import Optional
from dataclasses import dataclass


@dataclass
class TokenInfo:
    """Token-Informationen für Anzeige"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    context_size: int = 16384
    model: str = ""
    provider: str = ""

    @property
    def remaining(self) -> int:
        return max(0, self.context_size - self.total_tokens)

    @property
    def usage_percent(self) -> float:
        return min(100, (self.total_tokens / self.context_size) * 100)


def init_token_state():
    """Initialisiert Token-Tracking im Session State"""
    if "last_token_info" not in st.session_state:
        st.session_state.last_token_info = None
    if "session_total_tokens" not in st.session_state:
        st.session_state.session_total_tokens = 0


def update_token_info(
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    context_size: int = 16384,
    model: str = "",
    provider: str = ""
):
    """Aktualisiert Token-Info im Session State"""
    init_token_state()

    st.session_state.last_token_info = TokenInfo(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        context_size=context_size,
        model=model,
        provider=provider
    )
    st.session_state.session_total_tokens += total_tokens


def render_token_display(compact: bool = True):
    """
    Rendert die Token-Anzeige

    Args:
        compact: True für kompakte einzeilige Anzeige, False für detaillierte Anzeige
    """
    init_token_state()

    info = st.session_state.last_token_info

    if info is None:
        return

    if compact:
        # Kompakte Anzeige: eine Zeile
        remaining = info.remaining
        usage = info.usage_percent

        # Farbcodierung basierend auf Nutzung
        if usage < 50:
            color = "#22c55e"  # Gruen
        elif usage < 80:
            color = "#f59e0b"  # Orange
        else:
            color = "#ef4444"  # Rot

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; padding: 8px 12px;
                    background: #f8f9fa; border-radius: 8px; font-size: 12px; color: #6b7280;">
            <span style="color: {color}; font-weight: 600;">{remaining:,} Tokens frei</span>
            <span>|</span>
            <span>Verwendet: {info.total_tokens:,} ({usage:.0f}%)</span>
            <span>|</span>
            <span>In: {info.prompt_tokens:,} / Out: {info.completion_tokens:,}</span>
        </div>
        """, unsafe_allow_html=True)

    else:
        # Detaillierte Anzeige
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Verbleibend",
                f"{info.remaining:,}",
                delta=None,
                help="Tokens die noch im Kontext verfuegbar sind"
            )

        with col2:
            st.metric(
                "Verwendet",
                f"{info.total_tokens:,}",
                delta=f"{info.usage_percent:.1f}%",
                help="Gesamt verwendete Tokens (Input + Output)"
            )

        with col3:
            st.metric(
                "Input",
                f"{info.prompt_tokens:,}",
                help="Tokens im Prompt (Frage + Kontext)"
            )

        with col4:
            st.metric(
                "Output",
                f"{info.completion_tokens:,}",
                help="Tokens in der Antwort"
            )

        # Progress Bar
        usage = info.usage_percent
        if usage < 50:
            bar_color = "#22c55e"
        elif usage < 80:
            bar_color = "#f59e0b"
        else:
            bar_color = "#ef4444"

        st.markdown(f"""
        <div style="background: #e5e7eb; border-radius: 4px; height: 8px; margin-top: 8px;">
            <div style="background: {bar_color}; width: {min(usage, 100)}%; height: 100%; border-radius: 4px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #9ca3af; margin-top: 4px;">
            <span>0</span>
            <span>Kontext: {info.context_size:,} Tokens ({info.model})</span>
            <span>{info.context_size:,}</span>
        </div>
        """, unsafe_allow_html=True)


def render_session_stats():
    """Zeigt Session-Statistiken an"""
    init_token_state()

    total = st.session_state.session_total_tokens
    if total > 0:
        st.caption(f"Session gesamt: {total:,} Tokens")
