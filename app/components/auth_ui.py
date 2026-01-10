"""
KMU Knowledge Assistant - Login & User UI
Streamlit-Komponenten für Authentifizierung und Benutzerverwaltung
Mit persistenter Session über Browser-Cookies
"""

import streamlit as st
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
import json

from app.core.user_management import (
    user_manager,
    audit_logger,
    User,
    UserRole,
    Department
)

# Session-Token Speicher (Datei-basiert für Persistenz)
SESSION_FILE = Path("data/sessions.json")


def _load_sessions() -> dict:
    """Lädt aktive Sessions aus Datei"""
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text())
        except:
            return {}
    return {}


def _save_sessions(sessions: dict):
    """Speichert Sessions in Datei"""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(sessions))


def _create_session_token(user_id: str) -> str:
    """Erstellt einen neuen Session-Token"""
    token = secrets.token_urlsafe(32)
    sessions = _load_sessions()

    # Token mit Ablaufzeit speichern (7 Tage)
    sessions[token] = {
        "user_id": user_id,
        "expires": (datetime.now() + timedelta(days=7)).isoformat()
    }

    # Alte Sessions bereinigen
    now = datetime.now()
    sessions = {
        k: v for k, v in sessions.items()
        if datetime.fromisoformat(v["expires"]) > now
    }

    _save_sessions(sessions)
    return token


def _validate_session_token(token: str) -> str | None:
    """Prüft Session-Token und gibt user_id zurück"""
    if not token:
        return None

    sessions = _load_sessions()
    session = sessions.get(token)

    if not session:
        return None

    # Ablauf prüfen
    if datetime.fromisoformat(session["expires"]) < datetime.now():
        # Abgelaufene Session löschen
        del sessions[token]
        _save_sessions(sessions)
        return None

    return session["user_id"]


def _invalidate_session(token: str):
    """Löscht eine Session"""
    sessions = _load_sessions()
    if token in sessions:
        del sessions[token]
        _save_sessions(sessions)


def init_auth_state():
    """Initialisiert Authentifizierungs-State mit Cookie-Persistenz"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
    if "session_token" not in st.session_state:
        st.session_state.session_token = None

    # Versuche Session aus URL-Parameter wiederherzustellen
    if not st.session_state.authenticated:
        _try_restore_session()


def _try_restore_session():
    """Versucht Session aus URL-Parameter wiederherzustellen"""
    try:
        # Session-Token aus URL-Parameter lesen
        token = st.query_params.get("session")

        # Debug
        print(f"[AUTH DEBUG] Query params: {dict(st.query_params)}")
        print(f"[AUTH DEBUG] Token from URL: {token}")

        # Falls Liste, erstes Element nehmen
        if isinstance(token, list):
            token = token[0] if token else None

        if token:
            user_id = _validate_session_token(token)
            print(f"[AUTH DEBUG] User ID from token: {user_id}")

            if user_id:
                user = user_manager.get_user(user_id)
                print(f"[AUTH DEBUG] User found: {user}")

                if user and user.is_active:
                    st.session_state.authenticated = True
                    st.session_state.current_user = user
                    st.session_state.session_token = token
                    print(f"[AUTH DEBUG] Session restored for: {user.display_name}")
                    return True
    except Exception as e:
        # Bei Fehler still fehlschlagen
        print(f"[AUTH DEBUG] Session restore error: {e}")
        import traceback
        traceback.print_exc()

    return False


def render_login_page():
    """Rendert die Login-Seite"""
    init_auth_state()
    
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>KMU Knowledge Assistant</h1>
            <p style="color: #666;">Muster KMU</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("Anmeldung")
            
            username = st.text_input(
                "Benutzername",
                placeholder="Ihr Benutzername",
                key="login_username"
            )
            
            password = st.text_input(
                "Passwort",
                type="password",
                placeholder="Ihr Passwort",
                key="login_password"
            )
            
            col_login, col_forgot = st.columns(2)
            
            with col_login:
                login_clicked = st.button(
                    "Anmelden",
                    type="primary",
                    use_container_width=True
                )
            
            if login_clicked:
                if username and password:
                    user = user_manager.authenticate(username, password)

                    if user:
                        # Session-Token erstellen und in URL setzen
                        token = _create_session_token(user.id)
                        st.query_params["session"] = token

                        st.session_state.authenticated = True
                        st.session_state.current_user = user
                        st.session_state.session_token = token
                        st.session_state.login_attempts = 0

                        # Audit-Log
                        audit_logger.log_login(user, success=True)

                        st.success(f"Willkommen, {user.display_name}!")
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        
                        # Dummy-User für Audit bei fehlgeschlagenem Login
                        dummy_user = User(
                            id="unknown",
                            username=username,
                            email="",
                            password_hash="",
                            role=UserRole.LESEZUGRIFF,
                            department=Department.ALLGEMEIN,
                            display_name=username
                        )
                        audit_logger.log_login(dummy_user, success=False)
                        
                        if st.session_state.login_attempts >= 3:
                            st.error("Zu viele fehlgeschlagene Versuche. Bitte warten Sie.")
                        else:
                            st.error("Ungültiger Benutzername oder Passwort.")
                else:
                    st.warning("Bitte Benutzername und Passwort eingeben.")
        
        st.caption("Standard-Login: admin / admin123")


def check_authentication() -> bool:
    """Prüft ob Benutzer authentifiziert ist"""
    # Zuerst prüfen ob bereits in Session
    if st.session_state.get("authenticated") and st.session_state.get("current_user"):
        return True

    # Falls nicht, versuche Session wiederherzustellen
    init_auth_state()

    # Nochmal prüfen nach Wiederherstellung
    return st.session_state.get("authenticated", False) and st.session_state.get("current_user") is not None


def get_current_user() -> User:
    """Gibt aktuellen Benutzer zurück"""
    return st.session_state.current_user


def require_permission(permission: str) -> bool:
    """Prüft ob Benutzer eine Berechtigung hat"""
    user = get_current_user()
    if not user:
        return False
    
    permission_map = {
        "upload": user.can_upload,
        "create_kb": user.can_create_kb,
        "scrape": user.can_scrape,
        "manage_users": user.can_manage_users,
        "view_audit": user.can_view_audit,
        "admin": user.role == UserRole.ADMIN
    }
    
    return permission_map.get(permission, False)


def render_logout_button():
    """Rendert Logout-Button in Sidebar"""
    user = get_current_user()
    if user:
        with st.sidebar:
            st.divider()
            st.markdown(f"**{user.display_name}**")
            st.caption(f"{user.role.value} | {user.department.value}")

            if st.button("Abmelden", use_container_width=True):
                # Session invalidieren
                if st.session_state.session_token:
                    _invalidate_session(st.session_state.session_token)

                # URL-Parameter entfernen
                if "session" in st.query_params:
                    del st.query_params["session"]

                st.session_state.authenticated = False
                st.session_state.current_user = None
                st.session_state.session_token = None
                st.rerun()


def render_user_management():
    """Rendert die Benutzerverwaltung (nur für Admins)"""
    if not require_permission("manage_users"):
        st.error("Keine Berechtigung für Benutzerverwaltung.")
        return
    
    st.header("Benutzerverwaltung")
    
    tab_list, tab_create, tab_audit = st.tabs([
        "Benutzer",
        "Neuer Benutzer",
        "Audit-Log"
    ])
    
    with tab_list:
        render_user_list()
    
    with tab_create:
        render_create_user()
    
    with tab_audit:
        render_audit_log()


def render_user_list():
    """Rendert Benutzerliste"""
    st.subheader("Aktive Benutzer")
    
    show_inactive = st.checkbox("Deaktivierte Benutzer anzeigen")
    users = user_manager.list_users(include_inactive=show_inactive)
    
    if not users:
        st.info("Keine Benutzer gefunden.")
        return
    
    for user in users:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                status = "[+]" if user.is_active else "[-]"
                st.markdown(f"**{status} {user.display_name}**")
                st.caption(f"@{user.username} | {user.email}")
            
            with col2:
                st.markdown(f"**Rolle:** {user.role.value}")
                st.markdown(f"**Abteilung:** {user.department.value}")
            
            with col3:
                if user.last_login:
                    st.markdown(f"**Letzter Login:**")
                    st.caption(user.last_login.strftime("%d.%m.%Y %H:%M"))
                else:
                    st.caption("Noch nie angemeldet")
            
            with col4:
                if user.id != get_current_user().id:  # Sich selbst nicht deaktivieren
                    if user.is_active:
                        if st.button("L", key=f"deact_{user.id}", help="Deaktivieren"):
                            user_manager.deactivate_user(user.id)
                            st.rerun()
                    else:
                        if st.button("U", key=f"act_{user.id}", help="Aktivieren"):
                            user_manager.update_user(user.id, is_active=True)
                            st.rerun()


def render_create_user():
    """Rendert Formular für neuen Benutzer"""
    st.subheader("Neuen Benutzer erstellen")
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Benutzername*", placeholder="max.muster")
            email = st.text_input("E-Mail*", placeholder="max.muster@gemeinde.ch")
            password = st.text_input("Passwort*", type="password")
            password_confirm = st.text_input("Passwort bestätigen*", type="password")
        
        with col2:
            display_name = st.text_input("Anzeigename*", placeholder="Max Muster")
            
            role = st.selectbox(
                "Rolle*",
                options=[r.value for r in UserRole],
                format_func=lambda x: {
                    "admin": "Administrator",
                    "abteilungsleiter": "Abteilungsleiter",
                    "sachbearbeiter": "Sachbearbeiter",
                    "lesezugriff": "Nur Lesezugriff"
                }.get(x, x)
            )
            
            department = st.selectbox(
                "Abteilung*",
                options=[d.value for d in Department],
                format_func=lambda x: x.capitalize()
            )
        
        st.divider()
        
        # Berechtigungen (nur anzeigen, werden automatisch gesetzt)
        with st.expander("Berechtigungen (basierend auf Rolle)"):
            selected_role = UserRole(role)
            
            st.checkbox("Dokumente hochladen", value=selected_role != UserRole.LESEZUGRIFF, disabled=True)
            st.checkbox("Wissensbasen erstellen", value=selected_role in [UserRole.ADMIN, UserRole.ABTEILUNGSLEITER], disabled=True)
            st.checkbox("Web-Scraping", value=selected_role == UserRole.ADMIN, disabled=True)
            st.checkbox("Benutzer verwalten", value=selected_role == UserRole.ADMIN, disabled=True)
            st.checkbox("Audit-Log einsehen", value=selected_role in [UserRole.ADMIN, UserRole.ABTEILUNGSLEITER], disabled=True)
        
        submitted = st.form_submit_button("Benutzer erstellen", type="primary")
        
        if submitted:
            # Validierung
            errors = []
            
            if not username or not email or not password or not display_name:
                errors.append("Alle Pflichtfelder müssen ausgefüllt sein.")
            
            if password != password_confirm:
                errors.append("Passwörter stimmen nicht überein.")
            
            if len(password) < 6:
                errors.append("Passwort muss mindestens 6 Zeichen haben.")
            
            if user_manager.get_user_by_username(username):
                errors.append(f"Benutzername '{username}' existiert bereits.")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    new_user = user_manager.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role=UserRole(role),
                        department=Department(department),
                        display_name=display_name
                    )
                    st.success(f"Benutzer '{new_user.display_name}' erfolgreich erstellt!")
                    
                    # Audit
                    audit_logger.log(
                        user=get_current_user(),
                        action="user_created",
                        details={"created_user": new_user.username}
                    )
                except Exception as e:
                    st.error(f"Fehler beim Erstellen: {str(e)}")


def render_audit_log():
    """Rendert das Audit-Log"""
    st.subheader("Audit-Log")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_back = st.selectbox(
            "Zeitraum",
            options=[7, 14, 30, 90],
            format_func=lambda x: f"Letzte {x} Tage"
        )
    
    with col2:
        action_filter = st.selectbox(
            "Aktion",
            options=["Alle", "chat_query", "document_upload", "search", "login_success", "login_failed", "user_created"],
        )
    
    with col3:
        users = user_manager.list_users(include_inactive=True)
        user_options = ["Alle"] + [u.username for u in users]
        user_filter = st.selectbox("Benutzer", options=user_options)
    
    # Logs abrufen
    start_date = datetime.now() - timedelta(days=days_back)
    
    logs = audit_logger.get_logs(
        start_date=start_date,
        action=action_filter if action_filter != "Alle" else None,
        user_id=next((u.id for u in users if u.username == user_filter), None) if user_filter != "Alle" else None,
        limit=200
    )
    
    st.markdown(f"**{len(logs)} Einträge gefunden**")
    
    # Statistiken
    if logs:
        col1, col2, col3, col4 = st.columns(4)
        
        actions = {}
        for log in logs:
            actions[log.action] = actions.get(log.action, 0) + 1
        
        with col1:
            st.metric("Chat-Anfragen", actions.get("chat_query", 0))
        with col2:
            st.metric("Uploads", actions.get("document_upload", 0))
        with col3:
            st.metric("Suchen", actions.get("search", 0))
        with col4:
            st.metric("Fehlgeschlagene Logins", actions.get("login_failed", 0))
    
    st.divider()
    
    # Log-Einträge anzeigen
    for log in logs[:50]:  # Nur erste 50 anzeigen
        action_icons = {
            "chat_query": "[C]",
            "document_upload": "[U]",
            "search": "[S]",
            "login_success": "[+]",
            "login_failed": "[-]",
            "user_created": "[N]"
        }

        icon = action_icons.get(log.action, "[?]")
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown(f"**{icon} {log.action}**")
                st.caption(log.timestamp.strftime("%d.%m.%Y %H:%M:%S"))
            
            with col2:
                st.markdown(f"**{log.username}** ({log.department})")
                
                if log.query:
                    st.caption(f"Query: {log.query[:100]}...")
                if log.document_name:
                    st.caption(f"Dokument: {log.document_name}")
                if log.details:
                    st.caption(f"Details: {log.details}")
    
    if len(logs) > 50:
        st.info(f"Zeige 50 von {len(logs)} Einträgen. Für vollständigen Export wenden Sie sich an den Administrator.")
    
    # Export-Button
    if st.button("Compliance-Bericht generieren"):
        report = audit_logger.generate_compliance_report(
            start_date=start_date,
            end_date=datetime.now()
        )
        
        st.json(report)
        
        st.download_button(
            "Bericht herunterladen",
            data=str(report),
            file_name=f"compliance_report_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )


def render_user_profile():
    """Rendert Benutzerprofil (für eigene Einstellungen)"""
    user = get_current_user()
    if not user:
        return
    
    st.header("Mein Profil")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.subheader("Kontoinformationen")
            st.markdown(f"**Name:** {user.display_name}")
            st.markdown(f"**Benutzername:** @{user.username}")
            st.markdown(f"**E-Mail:** {user.email}")
            st.markdown(f"**Rolle:** {user.role.value}")
            st.markdown(f"**Abteilung:** {user.department.value}")
            
            if user.last_login:
                st.markdown(f"**Letzter Login:** {user.last_login.strftime('%d.%m.%Y %H:%M')}")
    
    with col2:
        with st.container(border=True):
            st.subheader("Passwort ändern")
            
            with st.form("change_password"):
                current_pw = st.text_input("Aktuelles Passwort", type="password")
                new_pw = st.text_input("Neues Passwort", type="password")
                new_pw_confirm = st.text_input("Neues Passwort bestätigen", type="password")
                
                if st.form_submit_button("Passwort ändern"):
                    # Aktuelles Passwort prüfen
                    if not user_manager.authenticate(user.username, current_pw):
                        st.error("Aktuelles Passwort ist falsch.")
                    elif new_pw != new_pw_confirm:
                        st.error("Neue Passwörter stimmen nicht überein.")
                    elif len(new_pw) < 6:
                        st.error("Passwort muss mindestens 6 Zeichen haben.")
                    else:
                        user_manager.change_password(user.id, new_pw)
                        st.success("Passwort erfolgreich geändert!")
    
    # Aktivitätsübersicht
    st.divider()
    st.subheader("Meine Aktivitaet (letzte 30 Tage)")
    
    activity = audit_logger.get_user_activity(user.id, days=30)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Aktionen gesamt", activity["total_actions"])
    with col2:
        st.metric("Chat-Anfragen", activity["actions_breakdown"].get("chat_query", 0))
    with col3:
        st.metric("Uploads", activity["actions_breakdown"].get("document_upload", 0))
