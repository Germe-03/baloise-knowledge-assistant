"""
KMU Knowledge Assistant - Wissensverwaltung
Streamlit-Komponente für Wissensbasen-Management
"""

import streamlit as st
from pathlib import Path
from datetime import datetime

from app.core.rag_engine import rag_engine, KnowledgeBase
from app.core.document_processor import document_processor
from app.core.embeddings import embedding_service
from app.utils.file_handlers import (
    is_supported_file,
    format_file_size,
    get_file_category,
    get_storage_stats
)
from app.config import ALL_EXTENSIONS, config, EmbeddingMode


def init_knowledge_state():
    """Initialisiert Knowledge-State"""
    if "selected_kb" not in st.session_state:
        st.session_state.selected_kb = None
    if "upload_success" not in st.session_state:
        st.session_state.upload_success = False


def render_knowledge_base_selector():
    """Rendert Wissensbank-Auswahl in der Sidebar"""
    # State sicherstellen
    if "selected_kb" not in st.session_state:
        st.session_state.selected_kb = None
    
    st.sidebar.subheader("Wissensbasen")
    
    knowledge_bases = rag_engine.list_knowledge_bases()
    
    if knowledge_bases:
        kb_options = {kb.id: f"{kb.icon} {kb.name} ({kb.chunk_count} Chunks)" for kb in knowledge_bases}
        kb_keys = list(kb_options.keys())
        
        # Index bestimmen
        current_kb = st.session_state.selected_kb
        if current_kb and current_kb in kb_keys:
            current_index = kb_keys.index(current_kb)
        else:
            current_index = 0
        
        selected = st.sidebar.radio(
            "Wissensbank auswählen:",
            options=kb_keys,
            format_func=lambda x: kb_options[x],
            index=current_index
        )
        
        st.session_state.selected_kb = selected
    else:
        st.sidebar.info("Keine Wissensbasen vorhanden")
        st.session_state.selected_kb = None


def render_knowledge_manager():
    """Rendert die Wissensverwaltungs-Oberfläche"""
    init_knowledge_state()
    
    st.header("Wissensverwaltung")
    
    # Tabs für verschiedene Funktionen
    tab_overview, tab_upload, tab_search, tab_manage = st.tabs([
        "Uebersicht",
        "Upload",
        "Suche",
        "Verwalten"
    ])
    
    with tab_overview:
        render_overview_tab()
    
    with tab_upload:
        render_upload_tab()
    
    with tab_search:
        render_search_tab()
    
    with tab_manage:
        render_manage_tab()


def render_overview_tab():
    """Übersicht über alle Wissensbasen"""

    # Prüfen ob eine Wissensbank ausgewählt ist
    if st.session_state.get("selected_kb") and st.session_state.get("show_kb_detail"):
        render_knowledge_base_detail(st.session_state.selected_kb)
        return

    st.subheader("Übersicht")

    # Statistiken
    stats = rag_engine.get_stats()
    storage = get_storage_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Wissensbasen", stats["knowledge_base_count"])

    with col2:
        st.metric("Chunks gesamt", stats["total_chunks"])

    with col3:
        st.metric("Speicher", storage["total"]["size_human"])

    st.divider()

    # Wissensbasen-Karten
    knowledge_bases = rag_engine.list_knowledge_bases()

    if knowledge_bases:
        cols = st.columns(2)
        for idx, kb in enumerate(knowledge_bases):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### {kb.icon} {kb.name}")
                    st.caption(kb.description)

                    # Dokumente zählen
                    docs = rag_engine.list_documents(kb.id)

                    st.markdown(f"**{len(docs)}** Dokumente | **{kb.chunk_count}** Chunks")

                    if st.button(f"Öffnen", key=f"open_{kb.id}", use_container_width=True):
                        st.session_state.selected_kb = kb.id
                        st.session_state.show_kb_detail = True
                        st.rerun()
    else:
        st.info("Noch keine Wissensbasen vorhanden. Erstellen Sie eine neue!")


def render_knowledge_base_detail(kb_id: str):
    """Detailansicht einer Wissensbank mit Dokumenten und Chunks"""
    # Wissensbank laden
    knowledge_bases = rag_engine.list_knowledge_bases()
    kb = next((k for k in knowledge_bases if k.id == kb_id), None)

    if not kb:
        st.error(f"Wissensbank '{kb_id}' nicht gefunden")
        return

    # Header mit Zurück-Button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("< Zurück"):
            st.session_state.show_kb_detail = False
            st.rerun()
    with col2:
        st.subheader(f"{kb.icon} {kb.name}")

    st.caption(kb.description)

    # Embedding-Status anzeigen
    emb_status = rag_engine.get_embedding_status(kb_id)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Chunks", kb.chunk_count)
    with col2:
        local_icon = "✅" if emb_status["local_available"] else "❌"
        st.metric("Lokal", f"{emb_status['local_count']} {local_icon}")
    with col3:
        openai_icon = "✅" if emb_status["openai_available"] else "❌"
        st.metric("OpenAI", f"{emb_status['openai_count']} {openai_icon}")

    st.divider()

    # Dokumente auflisten
    docs = rag_engine.list_documents(kb_id)

    if docs:
        st.markdown(f"### Dokumente ({len(docs)})")

        for doc in docs:
            # Embedding-Status Icons
            local_icon = "🏠" if doc.get('has_local', False) else "⬜"
            openai_icon = "☁️" if doc.get('has_openai', False) else "⬜"
            status_icons = f"{local_icon}{openai_icon}"

            with st.expander(f"{status_icons} {doc.get('filename', 'Unbekannt')}", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.caption(f"Typ: {doc.get('file_type', '-')}")
                with col2:
                    st.caption(f"Chunks: {doc.get('chunk_count', '-')}")
                with col3:
                    upload_date = doc.get('upload_date', '')
                    if upload_date:
                        st.caption(f"Datum: {upload_date[:10]}")
                with col4:
                    # Embedding-Status
                    status_parts = []
                    if doc.get('has_local'):
                        status_parts.append("Lokal")
                    if doc.get('has_openai'):
                        status_parts.append("OpenAI")
                    st.caption(f"Embeddings: {', '.join(status_parts) if status_parts else 'Keine'}")

                # Chunks des Dokuments anzeigen
                doc_id = doc.get('id')
                if doc_id:
                    chunks = rag_engine.get_document_chunks(kb_id, doc_id)
                    if chunks:
                        st.markdown("**Chunk-Vorschau:**")
                        for i, chunk in enumerate(chunks[:3]):
                            content = chunk.get('content', '')[:200]
                            st.text_area(
                                f"Chunk {i+1}",
                                value=content + "..." if len(chunk.get('content', '')) > 200 else content,
                                height=80,
                                disabled=True,
                                key=f"chunk_{doc_id}_{i}"
                            )
                        if len(chunks) > 3:
                            st.caption(f"... und {len(chunks) - 3} weitere Chunks")
    else:
        st.info("Noch keine Dokumente in dieser Wissensbank.")


def render_upload_tab():
    """Dokumente hochladen"""
    st.subheader("Dokumente hochladen")

    # Embedding-Provider Status anzeigen
    provider_status = embedding_service.get_provider_status()
    with st.container(border=True):
        st.markdown("**Embedding-Provider Status:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            local_status = "✅ Verfügbar" if provider_status["local"] else "❌ Offline"
            st.markdown(f"Lokal (Ollama): {local_status}")
        with col2:
            openai_status = "✅ Verfügbar" if provider_status["openai"] else "❌ Offline"
            st.markdown(f"OpenAI API: {openai_status}")
        with col3:
            mode_str = {
                EmbeddingMode.LOCAL_ONLY: "Nur Lokal",
                EmbeddingMode.API_ONLY: "Nur API",
                EmbeddingMode.BOTH: "Beide"
            }.get(config.embedding.mode, "Beide")
            st.markdown(f"Modus: **{mode_str}**")

    st.divider()

    # Wissensbank auswählen
    knowledge_bases = rag_engine.list_knowledge_bases()

    if not knowledge_bases:
        st.warning("Bitte erstellen Sie zuerst eine Wissensbank unter 'Verwalten'.")
        return

    kb_options = {kb.id: f"{kb.icon} {kb.name}" for kb in knowledge_bases}

    target_kb = st.selectbox(
        "Ziel-Wissensbank:",
        options=list(kb_options.keys()),
        format_func=lambda x: kb_options[x],
        index=list(kb_options.keys()).index(st.session_state.selected_kb)
              if st.session_state.selected_kb in kb_options else 0
    )

    # Embedding-Status der gewählten Wissensbank anzeigen
    if target_kb:
        emb_status = rag_engine.get_embedding_status(target_kb)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Lokale Embeddings", emb_status["local_count"])
        with col2:
            st.metric("OpenAI Embeddings", emb_status["openai_count"])

    st.divider()

    # Unterstützte Formate anzeigen
    with st.expander("Unterstuetzte Formate"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Dokumente:** PDF, DOCX, TXT, MD, RTF")
            st.markdown("**Tabellen:** XLSX, CSV")
            st.markdown("**E-Mails:** MSG, EML")
        with col2:
            st.markdown("**Bilder (OCR):** PNG, JPG, TIFF")
            st.markdown("**Web:** HTML")

    # Datei-Upload
    uploaded_files = st.file_uploader(
        "Dateien auswählen",
        type=[ext.replace(".", "") for ext in ALL_EXTENSIONS],
        accept_multiple_files=True,
        help="Drag & Drop oder klicken zum Auswählen"
    )

    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} Datei(en) ausgewählt:**")

        for file in uploaded_files:
            category = get_file_category(file.name) or "Unbekannt"
            size = format_file_size(file.size)
            st.markdown(f"- {file.name} ({size}, {category})")

        if st.button("Hochladen und Verarbeiten", type="primary", use_container_width=True):
            progress = st.progress(0)
            status = st.empty()

            results = {"local": 0, "openai": 0, "errors": 0}

            for idx, file in enumerate(uploaded_files):
                status.text(f"Verarbeite {file.name}...")

                try:
                    # Datei verarbeiten
                    content = file.read()

                    doc = document_processor.process_bytes(
                        content=content,
                        filename=file.name,
                        knowledge_base_id=target_kb,
                        uploader_id="user"
                    )

                    # Zur Wissensbank hinzufügen (Dual-Embedding)
                    embed_result = rag_engine.add_document(doc)

                    if embed_result["local"]:
                        results["local"] += 1
                    if embed_result["openai"]:
                        results["openai"] += 1
                    if not embed_result["local"] and not embed_result["openai"]:
                        results["errors"] += 1

                except Exception as e:
                    st.error(f"Fehler bei {file.name}: {str(e)}")
                    results["errors"] += 1

                progress.progress((idx + 1) / len(uploaded_files))

            status.empty()
            progress.empty()

            # Ergebnis-Zusammenfassung
            st.markdown("**Ergebnis:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if results["local"] > 0:
                    st.success(f"Lokal: {results['local']} Dokument(e)")
                else:
                    st.warning("Lokal: 0 Dokumente")
            with col2:
                if results["openai"] > 0:
                    st.success(f"OpenAI: {results['openai']} Dokument(e)")
                else:
                    st.warning("OpenAI: 0 Dokumente")
            with col3:
                if results["errors"] > 0:
                    st.error(f"Fehler: {results['errors']}")
                else:
                    st.info("Keine Fehler")


def render_search_tab():
    """Semantische Suche"""
    st.subheader("Suche in Wissensbasen")

    # Suchoptionen
    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input(
            "Suchbegriff",
            placeholder="Was möchten Sie wissen?",
            label_visibility="collapsed"
        )

    with col2:
        search_type = st.selectbox(
            "Typ",
            ["Hybrid (empfohlen)", "Semantisch", "BM25 (Keyword)", "Volltext"],
            label_visibility="collapsed",
            help="Hybrid kombiniert Vektor- und Keyword-Suche für beste Ergebnisse"
        )

    # Erweiterte Optionen für Hybrid Search
    if search_type == "Hybrid (empfohlen)":
        with st.expander("Erweiterte Einstellungen"):
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                vector_weight = st.slider(
                    "Vektor-Gewichtung",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.1,
                    help="Höher = mehr semantische Ähnlichkeit"
                )
            with col_w2:
                bm25_weight = st.slider(
                    "BM25-Gewichtung",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.1,
                    help="Höher = mehr exakte Keyword-Matches"
                )
    else:
        vector_weight = 0.5
        bm25_weight = 0.5

    # Wissensbasen-Filter
    knowledge_bases = rag_engine.list_knowledge_bases()
    kb_options = {kb.id: f"{kb.icon} {kb.name}" for kb in knowledge_bases}

    selected_kbs = st.multiselect(
        "In Wissensbasen suchen:",
        options=list(kb_options.keys()),
        format_func=lambda x: kb_options[x],
        default=list(kb_options.keys())
    )

    if query and st.button("Suchen", type="primary"):
        with st.spinner("Suche..."):
            if search_type == "Hybrid (empfohlen)":
                results = rag_engine.hybrid_search(
                    query,
                    kb_ids=selected_kbs,
                    vector_weight=vector_weight,
                    bm25_weight=bm25_weight
                )
                search_method = "Hybrid"
            elif search_type == "Semantisch":
                results = rag_engine.search(query, kb_ids=selected_kbs)
                search_method = "Vektor"
            elif search_type == "BM25 (Keyword)":
                results = rag_engine.bm25_search(query, kb_ids=selected_kbs)
                search_method = "BM25"
            else:
                results = rag_engine.fulltext_search(query, kb_ids=selected_kbs)
                search_method = "Volltext"

        if results:
            st.markdown(f"**{len(results)} Ergebnis(se) gefunden** ({search_method}-Suche):")

            for idx, result in enumerate(results):
                with st.expander(
                    f"{result.metadata.get('filename', 'Unbekannt')} "
                    f"(Score: {result.score:.2f})"
                ):
                    st.markdown(result.content)

                    st.divider()

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f"Wissensbank: {result.metadata.get('knowledge_base', '-')}")
                    with col2:
                        upload_date = result.metadata.get('upload_date', '-')
                        if upload_date and len(upload_date) >= 10:
                            upload_date = upload_date[:10]
                        st.caption(f"Hochgeladen: {upload_date}")
                    with col3:
                        st.caption(f"Chunk: {result.metadata.get('chunk_index', '-')}")
        else:
            st.info("Keine Ergebnisse gefunden.")


def render_manage_tab():
    """Wissensbasen verwalten"""
    st.subheader("Wissensbasen verwalten")
    
    # Neue Wissensbank erstellen
    with st.expander("Neue Wissensbank erstellen"):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            new_icon = st.text_input("Icon", value="📄", max_chars=4)
        
        with col2:
            new_name = st.text_input("Name", placeholder="z.B. Projektdokumentation")
        
        new_id = st.text_input(
            "ID (keine Leerzeichen)",
            placeholder="z.B. projektdoku",
            help="Eindeutige ID für interne Verwendung"
        )
        
        new_desc = st.text_area("Beschreibung", placeholder="Kurze Beschreibung der Wissensbank")
        
        if st.button("Erstellen", disabled=not (new_name and new_id)):
            try:
                kb = rag_engine.create_knowledge_base(
                    kb_id=new_id.lower().replace(" ", "_"),
                    name=new_name,
                    description=new_desc,
                    icon=new_icon
                )
                st.success(f"Wissensbank '{kb.name}' erstellt!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {str(e)}")
    
    st.divider()
    
    # Embedding-Einstellungen
    with st.expander("Embedding-Einstellungen"):
        st.markdown("**Aktueller Modus:**")

        # Provider-Status
        provider_status = embedding_service.get_provider_status()
        col1, col2 = st.columns(2)
        with col1:
            local_status = "✅ Verfügbar" if provider_status["local"] else "❌ Nicht verfügbar"
            st.markdown(f"Ollama (Lokal): {local_status}")
        with col2:
            openai_status = "✅ Verfügbar" if provider_status["openai"] else "❌ Nicht verfügbar"
            st.markdown(f"OpenAI API: {openai_status}")

        st.divider()

        # Modus-Anzeige
        mode_desc = {
            EmbeddingMode.LOCAL_ONLY: "Nur lokales Modell (Ollama nomic-embed-text)",
            EmbeddingMode.API_ONLY: "Nur OpenAI API (text-embedding-3-small)",
            EmbeddingMode.BOTH: "Beide Modelle (Lokal + OpenAI)"
        }
        current_mode = config.embedding.mode
        st.info(f"Embedding-Modus: **{mode_desc.get(current_mode, 'Beide')}**")

        st.markdown("**Such-Provider:** " + config.embedding.search_provider)
        st.caption("Der Such-Provider bestimmt, welche Embeddings für die Suche verwendet werden.")

        st.divider()

        st.markdown("**Modelle:**")
        st.markdown(f"- Lokal: `{config.embedding.local_model}` ({config.embedding.local_dimensions}d)")
        st.markdown(f"- OpenAI: `{config.embedding.openai_model}` ({config.embedding.openai_dimensions}d)")

    st.divider()

    # Bestehende Wissensbasen
    st.markdown("### Bestehende Wissensbasen")

    knowledge_bases = rag_engine.list_knowledge_bases()

    for kb in knowledge_bases:
        with st.container(border=True):
            # Embedding-Status abrufen
            emb_status = rag_engine.get_embedding_status(kb.id)

            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.markdown(f"**{kb.icon} {kb.name}**")
                # Embedding-Status Icons
                local_icon = "🏠" if emb_status["local_available"] else "⬜"
                openai_icon = "☁️" if emb_status["openai_available"] else "⬜"
                st.caption(f"ID: {kb.id} | {kb.chunk_count} Chunks | {local_icon}{openai_icon}")

            with col2:
                if st.button("Reindex", key=f"reindex_{kb.id}"):
                    with st.spinner("Reindexiere..."):
                        count = rag_engine.reindex_knowledge_base(kb.id)
                        st.success(f"{count} Chunks reindexiert")

            with col3:
                if st.button("Clear Emb.", key=f"clear_emb_{kb.id}"):
                    st.session_state[f"confirm_clear_emb_{kb.id}"] = True

            with col4:
                if st.button("Loeschen", key=f"delete_{kb.id}", type="secondary"):
                    st.session_state[f"confirm_delete_{kb.id}"] = True

            # Clear Embeddings Bestätigung
            if st.session_state.get(f"confirm_clear_emb_{kb.id}"):
                st.warning(f"Alle Embeddings von '{kb.name}' löschen? (Dokumente bleiben erhalten, müssen neu embedded werden)")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Ja, loeschen", key=f"confirm_clear_yes_{kb.id}"):
                        result = rag_engine.clear_all_embeddings(kb.id)
                        st.session_state[f"confirm_clear_emb_{kb.id}"] = False
                        st.success(f"Embeddings gelöscht (Local: {result['local']}, OpenAI: {result['openai']})")
                        st.rerun()
                with col_no:
                    if st.button("Abbrechen", key=f"confirm_clear_no_{kb.id}"):
                        st.session_state[f"confirm_clear_emb_{kb.id}"] = False
                        st.rerun()

            # Lösch-Bestätigung
            if st.session_state.get(f"confirm_delete_{kb.id}"):
                st.warning(f"Wissensbank '{kb.name}' wirklich loeschen?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Ja, loeschen", key=f"confirm_yes_{kb.id}"):
                        rag_engine.delete_knowledge_base(kb.id)
                        st.session_state[f"confirm_delete_{kb.id}"] = False
                        st.rerun()
                with col_no:
                    if st.button("Abbrechen", key=f"confirm_no_{kb.id}"):
                        st.session_state[f"confirm_delete_{kb.id}"] = False
                        st.rerun()
