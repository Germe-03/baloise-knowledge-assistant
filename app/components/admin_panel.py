"""
KMU Knowledge Assistant - Admin Panel
Streamlit-Komponente für System-Administration
"""

import streamlit as st
import os
from datetime import datetime

from app.core.rag_engine import rag_engine
from app.core.llm_provider import llm_provider, LLMProvider
# STT entfernt für Baloise Version
from app.core.embeddings import embedding_provider
from app.core.cbr_engine import cbr_engine
from app.core.user_management import user_manager, department_manager, UserRole, Department
from app.utils.file_handlers import get_storage_stats, cleanup_temp_files
from app.config import config, INITIAL_USERS


def init_admin_state():
    """Initialisiert Admin-State"""
    if "users" not in st.session_state:
        st.session_state.users = INITIAL_USERS.copy()
    if "current_user" not in st.session_state:
        st.session_state.current_user = INITIAL_USERS[0]
    # Chat-Einstellungen
    if "chat_user_color" not in st.session_state:
        st.session_state.chat_user_color = "#3b82f6"  # Blau
    if "chat_bot_color" not in st.session_state:
        st.session_state.chat_bot_color = "#1a1a1a"  # Dunkel
    if "chat_user_initial" not in st.session_state:
        st.session_state.chat_user_initial = "Du"
    if "chat_bot_initial" not in st.session_state:
        st.session_state.chat_bot_initial = "SP"


def check_admin_access() -> bool:
    """Prüft Admin-Zugriff"""
    current_user = st.session_state.get("current_user")
    if current_user:
        # User kann ein Objekt oder Dictionary sein
        role = getattr(current_user, 'role', None) or current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, 'role', None)
        if role == UserRole.ADMIN:
            return True
    return True  # Phase 1: Keine Auth, alle haben Zugriff


def render_admin_panel():
    """Rendert das Admin-Panel"""
    init_admin_state()
    
    if not check_admin_access():
        st.error("[Zugriff verweigert] Admin-Rechte erforderlich.")
        return
    
    st.header("Administration")
    
    # Tabs
    tab_system, tab_improvements, tab_personal, tab_departments, tab_chat, tab_llm, tab_maintenance = st.tabs([
        "System",
        "Verbesserungen",
        "Personal",
        "Abteilungen",
        "Chat",
        "LLM-Settings",
        "Wartung"
    ])

    with tab_system:
        render_system_tab()

    with tab_improvements:
        render_improvements_tab()

    with tab_personal:
        render_personal_tab()

    with tab_departments:
        render_departments_tab()

    with tab_chat:
        render_chat_settings_tab()

    with tab_llm:
        render_llm_tab()

    with tab_maintenance:
        render_maintenance_tab()


def render_improvements_tab():
    """CBR Verbesserungen - Negatives Feedback bearbeiten"""
    st.subheader("Verbesserungen (CBR)")
    st.markdown("Bearbeite negatives User-Feedback und verbessere die Antworten.")

    # Statistiken
    stats = cbr_engine.get_statistics()
    category_stats = cbr_engine.get_category_statistics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Feedback", stats.get("total_cases", 0))
    with col2:
        st.metric("Positiv", stats.get("positive_cases", 0))
    with col3:
        st.metric("Negativ", stats.get("negative_cases", 0))
    with col4:
        positive_rate = stats.get("positive_rate", 0)
        st.metric("Erfolgsrate", f"{positive_rate:.0%}")

    # Kategorie-Übersicht
    if category_stats:
        st.divider()
        st.markdown("### Kategorien (automatisch klassifiziert)")

        # Kategorie-Karten
        cat_cols = st.columns(min(len(category_stats), 4))
        sorted_cats = sorted(category_stats.items(), key=lambda x: x[1]["total"], reverse=True)

        for idx, (cat_name, cat_data) in enumerate(sorted_cats[:4]):
            with cat_cols[idx % 4]:
                neg_count = cat_data.get("negative", 0)
                total = cat_data.get("total", 0)
                badge = "*" if neg_count > 0 else "o"

                st.markdown(f"""
                <div style="padding: 12px; border-radius: 8px; background: #f8f9fa; border: 1px solid #e5e7eb; text-align: center;">
                    <div style="font-size: 11px; color: #6b7280; text-transform: uppercase;">{badge} {cat_name}</div>
                    <div style="font-size: 24px; font-weight: 600;">{total}</div>
                    <div style="font-size: 12px; color: {'#dc2626' if neg_count > 0 else '#16a34a'};">
                        {neg_count} negativ
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Button zum Neu-Klassifizieren
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            if st.button("Alle neu klassifizieren", help="Klassifiziert alle Cases neu"):
                with st.spinner("Klassifiziere..."):
                    result = cbr_engine.auto_classify_cases()
                    st.success(f"Klassifiziert: {sum(result.values())} Cases")
                    st.rerun()

    st.divider()

    # Filter
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])

    with filter_col1:
        filter_type = st.selectbox(
            "Feedback-Filter",
            options=["Negatives Feedback", "Alle", "Positives Feedback"],
            index=0
        )

    with filter_col2:
        # Kategorie-Filter
        available_categories = ["Alle Kategorien"] + sorted(category_stats.keys()) if category_stats else ["Alle Kategorien"]
        category_filter = st.selectbox(
            "Kategorie",
            options=available_categories,
            index=0
        )

    # Cases laden
    all_cases = cbr_engine.get_all_cases(limit=200)

    # Filtern nach Feedback-Typ
    if filter_type == "Negatives Feedback":
        filtered_cases = [c for c in all_cases if c.get("feedback_score", 0) < 0]
    elif filter_type == "Positives Feedback":
        filtered_cases = [c for c in all_cases if c.get("feedback_score", 0) > 0]
    else:
        filtered_cases = all_cases

    # Filtern nach Kategorie
    if category_filter != "Alle Kategorien":
        filtered_cases = [c for c in filtered_cases if c.get("cluster_label", "sonstiges") == category_filter]

    st.markdown(f"**{len(filtered_cases)} Einträge**")

    if not filtered_cases:
        st.info("Keine Einträge mit diesem Filter gefunden.")
        return

    # Cases anzeigen
    for case in filtered_cases:
        case_id = case.get("id", "unknown")
        question = case.get("question", "")
        answer = case.get("answer", "")
        feedback = case.get("feedback", "neutral")
        feedback_score = case.get("feedback_score", 0)
        created_at = case.get("created_at", "")[:16]
        times_reused = case.get("times_reused", 0)
        cluster_label = case.get("cluster_label", "sonstiges")

        # Status-Badge
        if feedback_score > 0:
            badge = "✅"
            badge_color = "#d1fae5"
        elif feedback_score < 0:
            badge = "⚠️"
            badge_color = "#fee2e2"
        else:
            badge = "➖"
            badge_color = "#f3f4f6"

        # Kategorie-Tag
        cat_tag = f"[{cluster_label}]" if cluster_label else ""

        with st.expander(
            f"{badge} {cat_tag} [{case_id[:8]}] {question[:50]}...",
            expanded=(feedback_score < 0)
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown("**Frage:**")
                st.info(question)

                st.markdown("**Ursprüngliche Antwort:**")
                if feedback_score < 0:
                    st.error(answer[:800] + "..." if len(answer) > 800 else answer)
                else:
                    st.success(answer[:800] + "..." if len(answer) > 800 else answer)

            with col2:
                st.markdown("**Details:**")
                st.caption(f"ID: `{case_id[:8]}`")
                st.caption(f"Erstellt: {created_at}")
                st.caption(f"Feedback: {feedback}")
                st.caption(f"Kategorie: **{cluster_label}**")
                st.caption(f"Wiederverwendet: {times_reused}x")

            # Nur bei negativem Feedback: Verbesserungsmöglichkeit
            if feedback_score < 0:
                st.divider()
                st.markdown("### Verbesserte Antwort eingeben")

                improved_answer = st.text_area(
                    "Optimale Antwort",
                    height=200,
                    key=f"improve_{case_id}",
                    placeholder="Gib hier die korrekte/verbesserte Antwort ein..."
                )

                col_btn1, col_btn2, col_btn3 = st.columns(3)

                with col_btn1:
                    if st.button("Als korrigiert speichern", key=f"save_{case_id}", type="primary"):
                        if improved_answer:
                            # Neuen positiven Case erstellen mit der verbesserten Antwort
                            new_case = cbr_engine.store_case(
                                question=question,
                                answer=improved_answer,
                                feedback="positive",
                                context_used=[],
                                knowledge_bases=case.get("knowledge_bases", []),
                                model_used="admin_correction",
                                user_id="admin",
                                feedback_comment=f"Korrigiert. Original: {answer[:200]}..."
                            )

                            if new_case:
                                # Original-Case als bearbeitet markieren
                                cbr_engine.update_feedback(
                                    case_id,
                                    "corrected",
                                    f"Korrigiert -> Neuer Case: {new_case.id[:8]}"
                                )
                                st.success(f"Verbesserte Antwort gespeichert! (Neuer Case: {new_case.id[:8]})")
                                st.rerun()
                            else:
                                st.error("Fehler beim Speichern.")
                        else:
                            st.warning("Bitte eine verbesserte Antwort eingeben.")

                with col_btn2:
                    if st.button("Feedback ändern zu Positiv", key=f"mark_pos_{case_id}"):
                        cbr_engine.update_feedback(case_id, "positive", "Manuell als positiv markiert")
                        st.success("Feedback aktualisiert!")
                        st.rerun()

                with col_btn3:
                    if st.button("Löschen", key=f"delete_{case_id}"):
                        cbr_engine.delete_case(case_id)
                        st.success("Case gelöscht.")
                        st.rerun()

            else:
                # Bei positivem Feedback: Nur Löschen-Option
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Feedback ändern zu Negativ", key=f"mark_neg_{case_id}"):
                        cbr_engine.update_feedback(case_id, "negative")
                        st.rerun()
                with col_btn2:
                    if st.button("Löschen", key=f"del_{case_id}"):
                        cbr_engine.delete_case(case_id)
                        st.rerun()


def render_personal_tab():
    """Personalverwaltung - Mitarbeiter erstellen und verwalten"""
    st.subheader("Personalverwaltung")

    # Statistiken
    users = user_manager.list_users(include_inactive=True)
    active_users = [u for u in users if u.is_active]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aktive Mitarbeiter", len(active_users))
    with col2:
        st.metric("Gesamt", len(users))
    with col3:
        admins = len([u for u in active_users if u.role == UserRole.ADMIN])
        st.metric("Administratoren", admins)

    st.divider()

    # Tabs: Liste und Neu erstellen
    tab_list, tab_create = st.tabs(["Mitarbeiterliste", "Neuer Mitarbeiter"])

    with tab_list:
        show_inactive = st.checkbox("Deaktivierte anzeigen", value=False)
        display_users = users if show_inactive else active_users

        if not display_users:
            st.info("Keine Mitarbeiter gefunden.")
        else:
            for user in display_users:
                status_icon = "[+]" if user.is_active else "[-]"
                role_icon = "[A]" if user.role == UserRole.ADMIN else "[U]"

                with st.expander(f"{status_icon} {role_icon} {user.display_name} (@{user.username})"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Persönliche Daten:**")
                        st.write(f"Vorname: {user.first_name or '-'}")
                        st.write(f"Nachname: {user.last_name or '-'}")
                        st.write(f"E-Mail: {user.email or '-'}")
                        st.write(f"Telefon: {user.phone or '-'}")

                    with col2:
                        st.markdown("**Zugangsdaten:**")
                        st.write(f"Benutzername: `{user.username}`")
                        st.write(f"Rolle: {user.role.value}")
                        st.write(f"Haupt-Abteilung: {user.department.value}")
                        if user.departments:
                            st.write(f"Abteilungen: {', '.join(user.departments)}")
                        if user.last_login:
                            st.write(f"Letzter Login: {user.last_login.strftime('%d.%m.%Y %H:%M')}")

                    st.divider()

                    # Bearbeiten
                    st.markdown("**Bearbeiten:**")
                    col_edit1, col_edit2, col_edit3 = st.columns(3)

                    with col_edit1:
                        new_email = st.text_input("E-Mail ändern", value=user.email, key=f"email_{user.id}")
                        if new_email != user.email:
                            if st.button("Speichern", key=f"save_email_{user.id}"):
                                user_manager.update_user(user.id, email=new_email)
                                st.success("E-Mail aktualisiert!")
                                st.rerun()

                    with col_edit2:
                        # Abteilungen zuweisen
                        all_depts = department_manager.get_all_department_names()
                        current_depts = user.departments or []
                        selected_depts = st.multiselect(
                            "Abteilungen",
                            options=all_depts,
                            default=[d for d in current_depts if d in all_depts],
                            key=f"depts_{user.id}"
                        )
                        if selected_depts != current_depts:
                            if st.button("Abteilungen speichern", key=f"save_depts_{user.id}"):
                                user_manager.update_user(user.id, departments=selected_depts)
                                st.success("Abteilungen aktualisiert!")
                                st.rerun()

                    with col_edit3:
                        # Passwort zurücksetzen
                        new_pw = st.text_input("Neues Passwort", type="password", key=f"pw_{user.id}")
                        if st.button("Passwort setzen", key=f"set_pw_{user.id}", disabled=not new_pw):
                            user_manager.change_password(user.id, new_pw)
                            st.success("Passwort geändert!")

                    # Aktionen
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if user.is_active:
                            if st.button("Deaktivieren", key=f"deact_{user.id}"):
                                user_manager.deactivate_user(user.id)
                                st.rerun()
                        else:
                            if st.button("Aktivieren", key=f"act_{user.id}"):
                                user_manager.update_user(user.id, is_active=True)
                                st.rerun()

    with tab_create:
        st.markdown("### Neuen Mitarbeiter anlegen")
        st.caption("📝 Hinweis: 2FA-Unterstützung wird in Phase 2 implementiert")

        with st.form("create_employee"):
            col1, col2 = st.columns(2)

            with col1:
                first_name = st.text_input("Vorname*")
                last_name = st.text_input("Nachname*")
                email = st.text_input("E-Mail*", placeholder="vorname.nachname@firma.ch")
                phone = st.text_input("Telefon", placeholder="+41 79 123 45 67")

            with col2:
                username = st.text_input("Benutzername*", placeholder="v.nachname")
                password = st.text_input("Passwort*", type="password")
                password_confirm = st.text_input("Passwort bestätigen*", type="password")

                role = st.selectbox(
                    "Rolle*",
                    options=[r for r in UserRole],
                    format_func=lambda r: {
                        UserRole.ADMIN: "Administrator",
                        UserRole.ABTEILUNGSLEITER: "Abteilungsleiter",
                        UserRole.SACHBEARBEITER: "Sachbearbeiter",
                        UserRole.LESEZUGRIFF: "Nur Lesezugriff"
                    }.get(r, r.value)
                )

                # Abteilungen
                all_depts = department_manager.get_all_department_names()
                departments = st.multiselect("Abteilungen*", options=all_depts)

            st.divider()
            submitted = st.form_submit_button("Mitarbeiter anlegen", type="primary")

            if submitted:
                errors = []
                if not first_name or not last_name:
                    errors.append("Vor- und Nachname sind erforderlich")
                if not email:
                    errors.append("E-Mail ist erforderlich")
                if not username:
                    errors.append("Benutzername ist erforderlich")
                if not password or len(password) < 4:
                    errors.append("Passwort muss mindestens 4 Zeichen haben")
                if password != password_confirm:
                    errors.append("Passwörter stimmen nicht überein")
                if not departments:
                    errors.append("Mindestens eine Abteilung auswählen")

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    try:
                        display_name = f"{first_name} {last_name}"
                        primary_dept = Department.ALLGEMEIN
                        # Versuche primäre Abteilung zu finden
                        for d in Department:
                            if d.value in departments:
                                primary_dept = d
                                break

                        new_user = user_manager.create_user(
                            username=username,
                            email=email,
                            password=password,
                            role=role,
                            department=primary_dept,
                            display_name=display_name,
                            first_name=first_name,
                            last_name=last_name,
                            phone=phone,
                            departments=departments
                        )
                        st.success(f"Mitarbeiter '{display_name}' erfolgreich angelegt!")
                        st.balloons()
                    except ValueError as e:
                        st.error(str(e))


def render_departments_tab():
    """Abteilungsverwaltung - Abteilungen und Wissensbasis-Zuordnung"""
    st.subheader("Abteilungsverwaltung")

    departments = department_manager.list_departments(include_inactive=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Aktive Abteilungen", len([d for d in departments if d.is_active]))
    with col2:
        st.metric("Gesamt", len(departments))

    st.divider()

    tab_list, tab_create, tab_kb_access = st.tabs([
        "Abteilungsliste",
        "Neue Abteilung",
        "Wissensbasis-Zugriff"
    ])

    with tab_list:
        if not departments:
            st.info("Keine Abteilungen gefunden.")
        else:
            for dept in departments:
                status = "[+]" if dept.is_active else "[-]"

                with st.expander(f"{status} {dept.name} ({dept.id})"):
                    st.write(f"**Beschreibung:** {dept.description or '-'}")
                    st.write(f"**Erstellt:** {dept.created_at[:10] if dept.created_at else '-'}")

                    # Wissensbasen
                    if dept.allowed_knowledge_bases:
                        st.write(f"**Zugewiesene Wissensbasen:** {len(dept.allowed_knowledge_bases)}")
                        for kb_id in dept.allowed_knowledge_bases:
                            st.caption(f"  - {kb_id}")
                    else:
                        st.write("**Zugewiesene Wissensbasen:** Alle (keine Einschränkung)")

                    # Mitarbeiter in dieser Abteilung
                    users_in_dept = [u for u in user_manager.list_users() if dept.id in (u.departments or [])]
                    st.write(f"**Mitarbeiter:** {len(users_in_dept)}")

                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input("Name ändern", value=dept.name, key=f"name_{dept.id}")
                        if new_name != dept.name:
                            if st.button("Speichern", key=f"save_name_{dept.id}"):
                                department_manager.update_department(dept.id, name=new_name)
                                st.rerun()

                    with col2:
                        new_desc = st.text_input("Beschreibung", value=dept.description, key=f"desc_{dept.id}")
                        if new_desc != dept.description:
                            if st.button("Speichern", key=f"save_desc_{dept.id}"):
                                department_manager.update_department(dept.id, description=new_desc)
                                st.rerun()

                    if dept.is_active:
                        if st.button("Deaktivieren", key=f"del_{dept.id}"):
                            department_manager.delete_department(dept.id)
                            st.rerun()

    with tab_create:
        st.markdown("### Neue Abteilung erstellen")

        with st.form("create_department"):
            dept_id = st.text_input("ID (eindeutig)*", placeholder="verkauf")
            dept_name = st.text_input("Name*", placeholder="Verkauf & Vertrieb")
            dept_desc = st.text_area("Beschreibung", placeholder="Beschreibung der Abteilung...")

            submitted = st.form_submit_button("Abteilung erstellen", type="primary")

            if submitted:
                if not dept_id or not dept_name:
                    st.error("ID und Name sind erforderlich")
                else:
                    try:
                        new_dept = department_manager.create_department(
                            dept_id=dept_id.lower().replace(" ", "_"),
                            name=dept_name,
                            description=dept_desc
                        )
                        st.success(f"Abteilung '{dept_name}' erstellt!")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    with tab_kb_access:
        st.markdown("### Wissensbasis-Zugriff pro Abteilung")
        st.caption("Hier können Sie festlegen, welche Abteilungen auf welche Wissensbasen zugreifen dürfen.")

        # Alle Wissensbasen laden
        knowledge_bases = rag_engine.list_knowledge_bases()

        if not knowledge_bases:
            st.warning("Keine Wissensbasen vorhanden. Erstellen Sie zuerst Wissensbasen.")
        elif not departments:
            st.warning("Keine Abteilungen vorhanden.")
        else:
            # Matrix-Ansicht
            st.markdown("**Zugriffs-Matrix:**")

            for dept in [d for d in departments if d.is_active]:
                st.markdown(f"**{dept.name}**")

                current_kbs = dept.allowed_knowledge_bases or []

                selected_kbs = st.multiselect(
                    f"Wissensbasen für {dept.name}",
                    options=[kb.id for kb in knowledge_bases],
                    default=[kb for kb in current_kbs if kb in [k.id for k in knowledge_bases]],
                    format_func=lambda x: next((kb.name for kb in knowledge_bases if kb.id == x), x),
                    key=f"kb_access_{dept.id}",
                    label_visibility="collapsed"
                )

                if set(selected_kbs) != set(current_kbs):
                    if st.button(f"Speichern für {dept.name}", key=f"save_kb_{dept.id}"):
                        department_manager.update_department(dept.id, allowed_knowledge_bases=selected_kbs)
                        st.success(f"Zugriff für '{dept.name}' aktualisiert!")
                        st.rerun()

                st.divider()


def render_chat_settings_tab():
    """Chat-Einstellungen (Avatar-Farben und Initialen)"""
    st.subheader("Chat-Darstellung")

    st.markdown("Passe die Darstellung der Chat-Avatare an.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Benutzer (Du)**")

        user_color = st.color_picker(
            "Avatar-Farbe",
            value=st.session_state.chat_user_color,
            key="picker_user_color"
        )
        if user_color != st.session_state.chat_user_color:
            st.session_state.chat_user_color = user_color

        user_initial = st.text_input(
            "Initialen/Text",
            value=st.session_state.chat_user_initial,
            max_chars=3,
            key="input_user_initial"
        )
        if user_initial != st.session_state.chat_user_initial:
            st.session_state.chat_user_initial = user_initial

        # Vorschau
        st.markdown("**Vorschau:**")
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 40px; height: 40px; border-radius: 50%; background-color: {user_color};
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;">
                {user_initial[:2]}
            </div>
            <span>Benutzer-Nachricht</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("**Assistent (Bot)**")

        bot_color = st.color_picker(
            "Avatar-Farbe",
            value=st.session_state.chat_bot_color,
            key="picker_bot_color"
        )
        if bot_color != st.session_state.chat_bot_color:
            st.session_state.chat_bot_color = bot_color

        bot_initial = st.text_input(
            "Initialen/Text",
            value=st.session_state.chat_bot_initial,
            max_chars=3,
            key="input_bot_initial"
        )
        if bot_initial != st.session_state.chat_bot_initial:
            st.session_state.chat_bot_initial = bot_initial

        # Vorschau
        st.markdown("**Vorschau:**")
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 40px; height: 40px; border-radius: 50%; background-color: {bot_color};
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;">
                {bot_initial[:2]}
            </div>
            <span>Assistent-Nachricht</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Farbvorschläge
    st.markdown("**Schnellauswahl Farben:**")

    color_presets = {
        "Blau": "#3b82f6",
        "Gruen": "#22c55e",
        "Lila": "#8b5cf6",
        "Orange": "#f97316",
        "Rot": "#ef4444",
        "Grau": "#6b7280",
        "Dunkel": "#1a1a1a",
        "Tuerkis": "#14b8a6"
    }

    cols = st.columns(len(color_presets))
    for idx, (name, color) in enumerate(color_presets.items()):
        with cols[idx]:
            st.markdown(f"""
            <div style="width: 30px; height: 30px; border-radius: 6px; background-color: {color};
                        margin: 0 auto; cursor: pointer;" title="{name}"></div>
            <div style="text-align: center; font-size: 10px; margin-top: 4px;">{name}</div>
            """, unsafe_allow_html=True)

    st.caption("Kopiere den Hex-Wert und fuege ihn oben ein.")


def render_system_tab():
    """System-Übersicht"""
    st.subheader("System-Status")
    
    # Provider-Status
    col1, col2 = st.columns(2)

    with col1:
        openai_status = "✅ Verfügbar" if llm_provider.providers[LLMProvider.OPENAI].is_available() else "❌ Offline"
        st.metric("OpenAI API", openai_status)

    with col2:
        anthropic_status = "✅ Verfügbar" if llm_provider.providers[LLMProvider.ANTHROPIC].is_available() else "❌ Offline"
        st.metric("Anthropic API", anthropic_status)
    
    st.divider()
    
    # Speicher-Statistiken
    st.subheader("Speicher")
    storage = get_storage_stats()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Uploads",
            storage["uploads"]["size_human"],
            f"{storage['uploads']['file_count']} Dateien"
        )
    
    with col2:
        st.metric(
            "Wissensbasen",
            storage["knowledge_bases"]["size_human"],
            f"{storage['knowledge_bases']['file_count']} Dateien"
        )
    
    with col3:
        st.metric("Gesamt", storage["total"]["size_human"])
    
    st.divider()
    
    # RAG-Statistiken
    st.subheader("Wissensbasen")
    stats = rag_engine.get_stats()
    
    st.markdown(f"**{stats['knowledge_base_count']}** Wissensbasen mit **{stats['total_chunks']}** Chunks")
    
    if stats["knowledge_bases"]:
        for kb in stats["knowledge_bases"]:
            st.markdown(f"- {kb['name']}: {kb['chunk_count']} Chunks")


def render_users_tab():
    """Benutzerverwaltung"""
    st.subheader("Benutzerverwaltung")
    
    st.info("Phase 1: Keine Authentifizierung aktiv. Benutzer werden nur simuliert.")
    
    # Benutzer auflisten
    users = st.session_state.users
    
    for idx, user in enumerate(users):
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                role_icon = "👑" if user["role"] == UserRole.ADMIN else "👤"
                st.markdown(f"**{role_icon} {user['name']}**")
                st.caption(f"ID: {user['id']}")
            
            with col2:
                st.markdown(f"Rolle: {user['role'].value}")
            
            with col3:
                if user["id"] != "admin":  # Admin kann nicht gelöscht werden
                    if st.button("x", key=f"del_user_{user['id']}"):
                        st.session_state.users.remove(user)
                        st.rerun()
    
    st.divider()
    
    # Neuen Benutzer hinzufügen
    with st.expander("Neuen Benutzer hinzufuegen"):
        new_name = st.text_input("Name", key="new_user_name")
        new_id = st.text_input("ID", key="new_user_id")
        new_role = st.selectbox(
            "Rolle",
            options=[r for r in UserRole],
            format_func=lambda r: r.value,
            key="new_user_role"
        )
        
        if st.button("Hinzufügen", disabled=not (new_name and new_id)):
            st.session_state.users.append({
                "id": new_id,
                "name": new_name,
                "role": new_role
            })
            st.success(f"Benutzer '{new_name}' hinzugefügt!")
            st.rerun()


def render_llm_tab():
    """LLM-Einstellungen"""
    st.subheader("LLM-Konfiguration")
    
    # Aktueller Provider
    current = llm_provider.current_provider
    st.markdown(f"**Aktueller Provider:** {current.value}")

    st.divider()

    # API-Keys
    st.markdown("### API-Keys")
    
    col1, col2 = st.columns(2)
    
    with col1:
        openai_key = st.text_input(
            "OpenAI API Key",
            value=config.llm.openai_api_key[:10] + "..." if config.llm.openai_api_key else "",
            type="password",
            help="sk-..."
        )
        
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=config.llm.anthropic_api_key[:10] + "..." if config.llm.anthropic_api_key else "",
            type="password",
            help="sk-ant-..."
        )
    
    with col2:
        google_key = st.text_input(
            "Google API Key",
            value=config.llm.google_api_key[:10] + "..." if config.llm.google_api_key else "",
            type="password"
        )
    
    st.info("""
    API-Keys können auch über Umgebungsvariablen gesetzt werden:
    - `OPENAI_API_KEY`
    - `ANTHROPIC_API_KEY`
    - `GOOGLE_API_KEY`
    """)

    st.divider()

    # Sampling-Parameter
    st.markdown("### Sampling-Parameter")
    st.caption("Diese Parameter steuern, wie das LLM Tokens auswählt")

    col1, col2 = st.columns(2)

    with col1:
        new_temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.5,
            value=config.llm.temperature,
            step=0.1,
            help="0 = deterministisch, 1+ = kreativ. Für RAG empfohlen: 0.3-0.5"
        )

        new_top_p = st.slider(
            "Top-P (Nucleus Sampling)",
            min_value=0.1,
            max_value=1.0,
            value=config.llm.top_p,
            step=0.05,
            help="Kumulative Wahrscheinlichkeits-Schwelle. 0.9 = fokussiert"
        )

    with col2:
        new_repeat_penalty = st.slider(
            "Repeat Penalty",
            min_value=1.0,
            max_value=2.0,
            value=config.llm.repeat_penalty,
            step=0.1,
            help="Bestraft Wiederholungen. 1.0 = keine, 1.1 = leicht"
        )

        new_max_tokens = st.number_input(
            "Max Tokens (Antwortlänge)",
            min_value=256,
            max_value=8192,
            value=config.llm.max_tokens or 2048,
            step=256,
            help="Maximale Anzahl Tokens in der Antwort"
        )

    # Sampling-Parameter speichern
    if st.button("Sampling-Parameter speichern", key="save_sampling"):
        config.llm.temperature = new_temperature
        config.llm.top_p = new_top_p
        config.llm.repeat_penalty = new_repeat_penalty
        config.llm.max_tokens = new_max_tokens
        st.success("Sampling-Parameter gespeichert!")
        st.rerun()

    st.divider()

    # Embedding-Einstellungen
    st.markdown("### Embeddings")
    
    use_local = st.checkbox(
        "Lokale Embeddings bevorzugen",
        value=config.embedding.use_local,
        help="Verwendet nomic-embed-text via Ollama wenn verfügbar"
    )
    
    st.markdown(f"**Lokales Modell:** {config.embedding.local_model}")
    st.markdown(f"**Cloud-Fallback:** {config.embedding.openai_model}")


def render_maintenance_tab():
    """Wartungsfunktionen"""
    st.subheader("Wartung")
    
    # Temp-Dateien bereinigen
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Temporaere Dateien")
        
        if st.button("Temp-Dateien bereinigen", use_container_width=True):
            deleted = cleanup_temp_files()
            st.success(f"{deleted} temporäre Dateien gelöscht")
    
    with col2:
        st.markdown("### Wissensbasen")
        
        if st.button("Alle Wissensbasen reindexieren", use_container_width=True):
            knowledge_bases = rag_engine.list_knowledge_bases()
            total = 0
            progress = st.progress(0)
            
            for idx, kb in enumerate(knowledge_bases):
                count = rag_engine.reindex_knowledge_base(kb.id)
                total += count
                progress.progress((idx + 1) / len(knowledge_bases))
            
            st.success(f"{total} Chunks reindexiert")
    
    st.divider()
    
    # System-Informationen
    st.markdown("### System-Info")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**App-Version:** 1.0.0")
        st.markdown(f"**Python:** {os.sys.version.split()[0]}")
    
    with col2:
        st.markdown(f"**Sprache:** {config.language}")
        st.markdown(f"**Debug-Modus:** {'Ja' if config.debug else 'Nein'}")
    
    st.divider()
    
    # Gefährliche Aktionen
    st.markdown("### Gefaehrliche Aktionen")
    
    with st.expander("Alle Daten loeschen", expanded=False):
        st.warning("Diese Aktion löscht ALLE Wissensbasen und Dokumente unwiderruflich!")
        
        confirm_text = st.text_input(
            "Zum Bestätigen 'LÖSCHEN' eingeben:",
            key="confirm_delete_all"
        )
        
        if st.button(
            "Alle Daten löschen",
            type="primary",
            disabled=confirm_text != "LÖSCHEN"
        ):
            knowledge_bases = rag_engine.list_knowledge_bases()
            for kb in knowledge_bases:
                rag_engine.delete_knowledge_base(kb.id)
            
            st.success("Alle Daten gelöscht.")
            st.rerun()
