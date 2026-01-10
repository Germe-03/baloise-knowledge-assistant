"""
Baloise Knowledge Assistant - Chat Interface
Modernes Chat-UI mit Historie, Dokument-Upload und RAG-Integration
"""

import streamlit as st
import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from app.core.rag_engine import rag_engine
from app.core.llm_provider import llm_provider
from app.config import LLMProvider
from app.core.document_processor import document_processor
from app.core.cbr_engine import cbr_engine
from app.config import config, DATA_DIR, ALL_EXTENSIONS
from app.components.token_display import update_token_info, render_token_display, init_token_state
from app.components.icons import icon, icon_text, badge, ICONS



# Chat-Historie Verzeichnis
CHAT_HISTORY_DIR = DATA_DIR / "chat_history"
CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ChatMessage:
    """Eine Chat-Nachricht"""
    role: str  # "user" oder "assistant"
    content: str
    timestamp: str
    sources: List[str] = None
    attachments: List[str] = None  # Dateinamen von Anhängen
    message_id: str = None  # Für CBR Feedback-Tracking
    feedback: str = None  # "positive", "negative", None

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "sources": self.sources or [],
            "attachments": self.attachments or [],
            "message_id": self.message_id or str(uuid.uuid4())[:8],
            "feedback": self.feedback
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", ""),
            sources=data.get("sources", []),
            attachments=data.get("attachments", []),
            message_id=data.get("message_id"),
            feedback=data.get("feedback")
        )


@dataclass
class Conversation:
    """Eine gespeicherte Konversation"""
    id: str
    title: str
    messages: List[ChatMessage]
    created_at: str
    updated_at: str
    knowledge_bases: List[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "knowledge_bases": self.knowledge_bases or []
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        return cls(
            id=data["id"],
            title=data["title"],
            messages=[ChatMessage.from_dict(m) for m in data.get("messages", [])],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            knowledge_bases=data.get("knowledge_bases", [])
        )


class ChatHistoryManager:
    """Verwaltet Chat-Historie"""

    def __init__(self, user_id: str = "default"):
        self.user_dir = CHAT_HISTORY_DIR / user_id
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def save_conversation(self, conv: Conversation) -> None:
        """Speichert eine Konversation"""
        file_path = self.user_dir / f"{conv.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(conv.to_dict(), f, ensure_ascii=False, indent=2)

    def load_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Lädt eine Konversation"""
        file_path = self.user_dir / f"{conv_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return Conversation.from_dict(json.load(f))
        return None

    def list_conversations(self) -> List[Conversation]:
        """Listet alle Konversationen"""
        conversations = []
        for file_path in self.user_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    conversations.append(Conversation.from_dict(json.load(f)))
            except Exception:
                continue
        # Sortiere nach updated_at (neueste zuerst)
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations

    def delete_conversation(self, conv_id: str) -> bool:
        """Löscht eine Konversation"""
        file_path = self.user_dir / f"{conv_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False


def init_chat_state():
    """Initialisiert Chat-State"""
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_knowledge_bases" not in st.session_state:
        st.session_state.selected_knowledge_bases = []
    if "chat_attachments" not in st.session_state:
        st.session_state.chat_attachments = []  # Temporäre Anhänge für aktuelle Nachricht
    if "attachment_contexts" not in st.session_state:
        st.session_state.attachment_contexts = {}  # {filename: extracted_text}


def get_chat_history_manager() -> ChatHistoryManager:
    """Gibt ChatHistoryManager für aktuellen User zurück"""
    try:
        from app.components.auth_ui import get_current_user
        user = get_current_user()
        user_id = user.id if user else "default"
    except ImportError:
        user_id = "default"
    return ChatHistoryManager(user_id)


def generate_conversation_title(first_message: str, use_llm: bool = True) -> str:
    """Generiert einen kurzen Titel (3-6 Wörter) aus der ersten Nachricht via LLM"""
    if not first_message or len(first_message.strip()) < 3:
        return "Neuer Chat"

    if use_llm:
        try:
            # Kurze Zusammenfassung via LLM
            response = llm_provider.generate(
                prompt=f"Fasse diese Anfrage in 3-5 Wörtern zusammen (nur der Titel, keine Anführungszeichen):\n\n{first_message[:200]}",
                system_prompt="Du bist ein Titel-Generator. Antworte NUR mit einem kurzen Titel (3-5 Wörter). Kein Punkt am Ende. Keine Anführungszeichen."
            )
            title = response.content.strip().strip('"\'')
            # Sicherheitscheck: Falls zu lang, kürzen
            words = title.split()
            if len(words) > 6:
                title = " ".join(words[:5])
            return title if title else "Neuer Chat"
        except Exception:
            pass

    # Fallback: Erste 40 Zeichen
    title = first_message[:40].strip()
    if len(first_message) > 40:
        title += "..."
    return title or "Neuer Chat"


def render_chat_settings():
    """Rendert Chat-History in der Sidebar (ChatGPT Style) - ausklappbar"""
    init_chat_state()
    history_manager = get_chat_history_manager()

    # === Chat-Historie ===
    conversations = history_manager.list_conversations()
    conv_count = len(conversations) if conversations else 0

    # Ausklappbarer Bereich für Chat-Verläufe
    with st.sidebar.expander(f"Letzte Chats ({conv_count})", expanded=False):
        # === Neuer Chat Button ===
        if st.button("+ Neuer Chat", use_container_width=True, type="primary", key="new_chat_btn"):
            if st.session_state.messages:
                save_current_conversation()
            st.session_state.current_conversation_id = None
            st.session_state.messages = []
            st.session_state.chat_attachments = []
            st.session_state.attachment_contexts = {}
            st.rerun()

        if conversations:
            st.markdown("---")

            # Gruppiere nach Datum
            today_convs = []
            older_convs = []
            today = datetime.now().date()

            for conv in conversations[:20]:
                try:
                    conv_date = datetime.fromisoformat(conv.updated_at).date()
                    if conv_date == today:
                        today_convs.append(conv)
                    else:
                        older_convs.append(conv)
                except:
                    older_convs.append(conv)

            # Heute
            if today_convs:
                st.caption("HEUTE")
                for conv in today_convs:
                    _render_chat_item(conv, history_manager)

            # Ältere
            if older_convs:
                st.caption("FRÜHER")
                for conv in older_convs[:10]:
                    _render_chat_item(conv, history_manager)
        else:
            st.caption("Keine Chats vorhanden")


def _render_chat_item(conv, history_manager):
    """Rendert einen einzelnen Chat-Eintrag - clean und minimalistisch"""
    is_active = st.session_state.current_conversation_id == conv.id
    title = conv.title[:30] if len(conv.title) <= 30 else conv.title[:27] + "..."

    # Ein Button pro Chat - clean ohne Symbole (st.button weil im Expander-Kontext)
    if st.button(
        title,
        key=f"conv_{conv.id}",
        use_container_width=True,
        type="primary" if is_active else "secondary"
    ):
        load_conversation(conv.id)


def save_current_conversation():
    """Speichert die aktuelle Konversation"""
    if not st.session_state.messages:
        return

    history_manager = get_chat_history_manager()
    now = datetime.now().isoformat()

    if st.session_state.current_conversation_id:
        # Bestehende Konversation aktualisieren
        conv = history_manager.load_conversation(st.session_state.current_conversation_id)
        if conv:
            conv.messages = [ChatMessage.from_dict(m) if isinstance(m, dict) else m
                          for m in st.session_state.messages]
            conv.updated_at = now
            history_manager.save_conversation(conv)
    else:
        # Neue Konversation erstellen
        first_user_msg = next(
            (m["content"] if isinstance(m, dict) else m.content
             for m in st.session_state.messages
             if (m["role"] if isinstance(m, dict) else m.role) == "user"),
            "Neuer Chat"
        )

        conv = Conversation(
            id=str(uuid.uuid4())[:8],
            title=generate_conversation_title(first_user_msg),
            messages=[ChatMessage.from_dict(m) if isinstance(m, dict) else m
                     for m in st.session_state.messages],
            created_at=now,
            updated_at=now,
            knowledge_bases=st.session_state.selected_knowledge_bases
        )
        history_manager.save_conversation(conv)
        st.session_state.current_conversation_id = conv.id


def load_conversation(conv_id: str):
    """Lädt eine Konversation"""
    # Aktuelle speichern
    if st.session_state.messages and st.session_state.current_conversation_id != conv_id:
        save_current_conversation()

    history_manager = get_chat_history_manager()
    conv = history_manager.load_conversation(conv_id)

    if conv:
        st.session_state.current_conversation_id = conv.id
        st.session_state.messages = [m.to_dict() for m in conv.messages]
        st.session_state.selected_knowledge_bases = conv.knowledge_bases or []
        st.session_state.chat_attachments = []
        st.session_state.attachment_contexts = {}
        st.rerun()


def process_uploaded_file(uploaded_file) -> Optional[str]:
    """Verarbeitet eine hochgeladene Datei und extrahiert Text"""
    try:
        content = uploaded_file.read()
        uploaded_file.seek(0)  # Reset für weitere Verwendung

        # Text extrahieren
        doc = document_processor.process_bytes(
            content=content,
            filename=uploaded_file.name,
            knowledge_base_id="temp",
            uploader_id="chat"
        )

        return doc.raw_text
    except Exception as e:
        st.error(f"Fehler beim Verarbeiten von {uploaded_file.name}: {str(e)}")
        return None


def render_feedback_buttons(msg_idx: int, msg_id: str, current_feedback: str, msg_content: str):
    """Rendert Feedback-Buttons (👍/👎) für eine Assistant-Nachricht"""

    # Finde die zugehörige User-Frage (vorherige Nachricht)
    user_question = ""
    if msg_idx > 0:
        prev_msg = st.session_state.messages[msg_idx - 1]
        if (prev_msg.get("role") if isinstance(prev_msg, dict) else prev_msg.role) == "user":
            user_question = prev_msg.get("content") if isinstance(prev_msg, dict) else prev_msg.content

    col1, col2, col3 = st.columns([1, 1, 10])

    with col1:
        # Positives Feedback
        btn_type = "primary" if current_feedback == "positive" else "secondary"
        if st.button("▲", key=f"fb_pos_{msg_id}", type=btn_type, help="Hilfreiche Antwort"):
            handle_feedback(msg_idx, msg_id, "positive", user_question, msg_content)

    with col2:
        # Negatives Feedback
        btn_type = "primary" if current_feedback == "negative" else "secondary"
        if st.button("▼", key=f"fb_neg_{msg_id}", type=btn_type, help="Nicht hilfreich"):
            handle_feedback(msg_idx, msg_id, "negative", user_question, msg_content)

    with col3:
        # Feedback-Status anzeigen
        if current_feedback == "positive":
            st.caption("Als hilfreich markiert")
        elif current_feedback == "negative":
            st.caption("Als nicht hilfreich markiert")


def handle_feedback(msg_idx: int, msg_id: str, feedback: str, question: str, answer: str):
    """Verarbeitet Feedback und speichert im CBR-System"""

    # Message im Session State aktualisieren
    if isinstance(st.session_state.messages[msg_idx], dict):
        st.session_state.messages[msg_idx]["feedback"] = feedback
        st.session_state.messages[msg_idx]["message_id"] = msg_id
    else:
        st.session_state.messages[msg_idx].feedback = feedback
        st.session_state.messages[msg_idx].message_id = msg_id

    # Im CBR-System speichern
    if question and answer:
        cbr_engine.store_case(
            question=question,
            answer=answer,
            feedback=feedback,
            knowledge_bases=st.session_state.get("selected_knowledge_bases", []),
            model_used=llm_provider.current_provider.value,
            user_id="default"
        )

    # Konversation speichern
    save_current_conversation()
    st.rerun()


def render_chat_interface():
    """Rendert modernes Chat-Interface"""
    init_chat_state()

    # Automatisch alle Wissensbasen verwenden (keine Auswahl nötig)
    knowledge_bases = rag_engine.list_knowledge_bases()
    all_kb_ids = [kb.id for kb in knowledge_bases]
    st.session_state.selected_knowledge_bases = all_kb_ids

    # OpenAI als Standard setzen
    llm_provider.current_provider = LLMProvider.OPENAI

    # === Datei-Upload Bereich (minimiert) ===
    with st.expander("Anhänge", expanded=bool(st.session_state.chat_attachments)):
        uploaded_files = st.file_uploader(
            "Dateien hochladen (PDF, Word, Excel, E-Mails...)",
            type=[ext.replace(".", "") for ext in ALL_EXTENSIONS],
            accept_multiple_files=True,
            key="chat_file_upload",
            label_visibility="collapsed"
        )

        if uploaded_files:
            for file in uploaded_files:
                if file.name not in st.session_state.attachment_contexts:
                    with st.spinner(f"Verarbeite {file.name}..."):
                        extracted_text = process_uploaded_file(file)
                        if extracted_text:
                            st.session_state.attachment_contexts[file.name] = extracted_text
                            st.session_state.chat_attachments.append(file.name)

            # Zeige angehängte Dateien
            if st.session_state.chat_attachments:
                st.markdown("**Angehängte Dateien:**")
                for filename in st.session_state.chat_attachments:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        text_len = len(st.session_state.attachment_contexts.get(filename, ""))
                        st.caption(f"[Datei] {filename} ({text_len:,} Zeichen)")
                    with col2:
                        if st.button("", key=f"remove_{filename}"):
                            st.session_state.chat_attachments.remove(filename)
                            del st.session_state.attachment_contexts[filename]
                            st.rerun()

    # === Chat-Verlauf ===
    chat_container = st.container()

    with chat_container:
        for idx, message in enumerate(st.session_state.messages):
            msg_content = message["content"] if isinstance(message, dict) else message.content
            msg_role = message["role"] if isinstance(message, dict) else message.role
            msg_sources = message.get("sources", []) if isinstance(message, dict) else (message.sources or [])
            msg_attachments = message.get("attachments", []) if isinstance(message, dict) else (message.attachments or [])
            msg_id = message.get("message_id", f"msg_{idx}") if isinstance(message, dict) else (message.message_id or f"msg_{idx}")
            msg_feedback = message.get("feedback") if isinstance(message, dict) else message.feedback

            with st.chat_message(msg_role):
                st.markdown(msg_content)

                # Anhänge anzeigen
                if msg_attachments:
                    st.caption(f"[Anhaenge] {', '.join(msg_attachments)}")

                # Quellen anzeigen
                if msg_sources:
                    with st.expander("> Quellen"):
                        for source in msg_sources:
                            st.markdown(f"- {source}")

                # Feedback-Buttons für Assistant-Nachrichten
                if msg_role == "assistant" and msg_content and not msg_content.startswith("Fehler:"):
                    render_feedback_buttons(idx, msg_id, msg_feedback, msg_content)

    # === Chat-Input ===
    if prompt := st.chat_input("Schreiben Sie eine Nachricht..."):
        # Anhänge-Kontext vorbereiten
        attachment_context = ""
        attachment_names = []

        if st.session_state.attachment_contexts:
            attachment_names = list(st.session_state.attachment_contexts.keys())
            attachment_context = "\n\n---\nAngehängte Dokumente:\n"
            for filename, text in st.session_state.attachment_contexts.items():
                # Begrenze Text auf 4000 Zeichen pro Dokument
                truncated = text[:4000] + "..." if len(text) > 4000 else text
                attachment_context += f"\n[{filename}]:\n{truncated}\n"

        # User-Message speichern
        user_message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat(),
            "sources": [],
            "attachments": attachment_names
        }
        st.session_state.messages.append(user_message)

        with st.chat_message("user"):
            st.markdown(prompt)
            if attachment_names:
                st.caption(f"[Anhaenge] {', '.join(attachment_names)}")

        # Antwort generieren
        with st.chat_message("assistant"):
            with st.spinner("Denke nach..."):
                try:
                    # Variable initialisieren
                    response = None
                    kb_ids = st.session_state.selected_knowledge_bases or None

                    # === CBR: Ähnliche erfolgreiche Cases abrufen ===
                    cbr_context = ""
                    similar_cases = cbr_engine.retrieve_similar_cases(
                        question=prompt,
                        top_k=2,
                        min_feedback_score=0.5,
                        knowledge_bases=kb_ids
                    )
                    if similar_cases:
                        cbr_context = cbr_engine.build_context_from_cases(similar_cases)
                        # Reuse-Counter erhöhen
                        for case in similar_cases:
                            cbr_engine.increment_reuse_count(case["id"])

                    # Prompt mit Anhängen erweitern
                    full_prompt = prompt
                    if attachment_context:
                        full_prompt = f"{prompt}\n{attachment_context}"

                    if kb_ids:
                        # Mit RAG (und optional CBR-Kontext)
                        response, sources = rag_engine.generate_answer(
                            query=full_prompt,
                            kb_ids=kb_ids,
                            stream=False,
                            additional_context=cbr_context if cbr_context else None
                        )
                        answer = response.content
                    else:
                        # Ohne RAG - reines LLM
                        base_prompt = """Du bist der Baloise Assistant, ein freundlicher und kompetenter Versicherungs-Chatbot der Baloise Versicherung.

Deine Aufgaben:
- Beantworte Fragen zu Versicherungsthemen professionell und verständlich
- Hilf bei allgemeinen Versicherungsfragen (Hausrat, Haftpflicht, Auto, Gebäude, etc.)
- Erkläre Versicherungsbegriffe einfach und klar
- Verweise bei Schadensmeldungen auf den Schadensmeldung-Bereich

Wichtig:
- Antworte immer auf Deutsch (Schweizer Hochdeutsch)
- Sei freundlich und hilfsbereit
- Bei konkreten Policen-Fragen verweise auf den Kundenberater
- Gib keine rechtlich bindenden Auskünfte

Wenn Dokumente angehängt wurden, beziehe dich auf deren Inhalt."""

                        system_prompt = base_prompt
                        if cbr_context:
                            system_prompt += f"\n\n{cbr_context}"

                        response = llm_provider.generate(
                            prompt=full_prompt,
                            system_prompt=system_prompt
                        )
                        answer = response.content
                        sources = []

                    st.markdown(answer)

                    # Token-Info aktualisieren und anzeigen (nur wenn response existiert)
                    if response is not None and hasattr(response, 'tokens_used') and response.tokens_used:
                        update_token_info(
                            prompt_tokens=response.prompt_tokens or 0,
                            completion_tokens=response.completion_tokens or 0,
                            total_tokens=response.tokens_used or 0,
                            context_size=response.context_size,
                            model=response.model,
                            provider=response.provider
                        )
                        render_token_display(compact=True)

                    if sources:
                        with st.expander("> Quellen"):
                            for source in sources:
                                st.markdown(f"- {source}")

                    # Antwort speichern (mit message_id für CBR)
                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "timestamp": datetime.now().isoformat(),
                        "sources": sources,
                        "attachments": [],
                        "message_id": str(uuid.uuid4())[:8],
                        "feedback": None
                    }
                    st.session_state.messages.append(assistant_message)

                    # Konversation speichern
                    save_current_conversation()

                    # Anhänge zurücksetzen nach Verwendung
                    st.session_state.chat_attachments = []
                    st.session_state.attachment_contexts = {}

                except Exception as e:
                    error_msg = f"Fehler: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "timestamp": datetime.now().isoformat(),
                        "sources": [],
                        "attachments": []
                    })


def render_chat_with_streaming():
    """Rendert Chat mit Streaming (falls gewünscht)"""
    # Für zukünftige Streaming-Implementierung
    render_chat_interface()
