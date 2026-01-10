"""
Baloise Schadensmeldung Bot
Intelligenter Chatbot zur Erfassung von Versicherungsschäden
"""

import streamlit as st
import json
import uuid
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from enum import Enum

from app.config import DATA_DIR
from app.core.llm_provider import llm_provider
from app.core.fuzzy_risk_engine import fuzzy_risk_engine, FuzzyResult, RiskLevel
from app.core.input_validator import swiss_validator, generate_validation_response


# Schadensmeldungen Verzeichnis
CLAIMS_DIR = DATA_DIR / "schadensmeldungen"
CLAIMS_DIR.mkdir(parents=True, exist_ok=True)

# Fotos Verzeichnis
FOTOS_DIR = DATA_DIR / "schadensmeldungen" / "fotos"
FOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Schadenstypen bei denen Fotos sinnvoll sind
FOTO_RELEVANT_TYPEN = ["Motorfahrzeug", "Hausrat", "Gebäude", "Haftpflicht", "Unfall"]


class SchadensTyp(Enum):
    """Versicherbare Schadensarten"""
    MOTORFAHRZEUG = "Motorfahrzeug"
    HAUSRAT = "Hausrat"
    GEBAUDE = "Gebäude"
    HAFTPFLICHT = "Haftpflicht"
    REISE = "Reise"
    RECHTSSCHUTZ = "Rechtsschutz"
    UNFALL = "Unfall"
    ANDERE = "Andere"


class SchadensStatus(Enum):
    """Status einer Schadensmeldung"""
    ENTWURF = "Entwurf"
    EINGEREICHT = "Eingereicht"
    IN_BEARBEITUNG = "In Bearbeitung"
    ABGESCHLOSSEN = "Abgeschlossen"


@dataclass
class Schadensmeldung:
    """Datenmodell für eine Schadensmeldung"""
    id: str
    user_id: str
    erstellt_am: str
    aktualisiert_am: str
    status: str = SchadensStatus.ENTWURF.value

    # Grunddaten
    schadenstyp: str = ""
    polizennummer: str = ""

    # Schadensdetails
    schadensdatum: str = ""
    schadenszeit: str = ""
    schadensort: str = ""
    schadensort_plz: str = ""
    schadensbeschreibung: str = ""
    schadensursache: str = ""

    # Finanzielles
    geschaetzter_betrag: float = 0.0
    waehrung: str = "CHF"

    # Beteiligte
    beteiligte_personen: List[Dict] = field(default_factory=list)
    zeugen: List[Dict] = field(default_factory=list)

    # Fahrzeugschaden spezifisch
    fahrzeug_kennzeichen: str = ""
    fahrzeug_marke: str = ""
    fahrzeug_modell: str = ""
    gegner_kennzeichen: str = ""
    gegner_versicherung: str = ""

    # Dokumentation
    polizeibericht: bool = False
    polizeiposten: str = ""
    fotos_vorhanden: bool = False
    fotos: List[str] = field(default_factory=list)  # Pfade zu hochgeladenen Fotos
    dokumente: List[str] = field(default_factory=list)

    # Kontakt
    kontakt_telefon: str = ""
    kontakt_email: str = ""
    bevorzugte_kontaktzeit: str = ""

    # Chat-Verlauf
    chat_history: List[Dict] = field(default_factory=list)

    # Erfassung
    erfassung_abgeschlossen: bool = False
    aktuelle_frage: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Schadensmeldung":
        # Ensure list fields are lists
        for field_name in ['beteiligte_personen', 'zeugen', 'dokumente', 'chat_history', 'fotos']:
            if field_name not in data or data[field_name] is None:
                data[field_name] = []
        return cls(**data)


# Fragen-Flow für den Schadensmeldung Bot
FRAGEN_FLOW = [
    {
        "id": "schadenstyp",
        "frage": "Um welche Art von Schaden handelt es sich?",
        "typ": "auswahl",
        "optionen": [t.value for t in SchadensTyp],
        "feld": "schadenstyp",
        "pflicht": True
    },
    {
        "id": "polizennummer",
        "frage": "Wie lautet Ihre Policennummer? (Falls bekannt, sonst 'unbekannt' eingeben)",
        "typ": "text",
        "feld": "polizennummer",
        "pflicht": False,
        "placeholder": "z.B. 12-345-678"
    },
    {
        "id": "schadensdatum",
        "frage": "Wann ist der Schaden passiert? (Datum)",
        "typ": "datum",
        "feld": "schadensdatum",
        "pflicht": True
    },
    {
        "id": "schadenszeit",
        "frage": "Ungefähr um welche Uhrzeit ist der Schaden passiert?",
        "typ": "text",
        "feld": "schadenszeit",
        "pflicht": False,
        "placeholder": "z.B. 14:30 oder 'nachmittags'"
    },
    {
        "id": "schadensort",
        "frage": "Wo ist der Schaden passiert? (Adresse oder Beschreibung des Ortes)",
        "typ": "text",
        "feld": "schadensort",
        "pflicht": True,
        "placeholder": "z.B. Bahnhofstrasse 10, Zürich"
    },
    {
        "id": "schadensbeschreibung",
        "frage": "Bitte beschreiben Sie den Schaden so detailliert wie möglich. Was genau ist passiert?",
        "typ": "textarea",
        "feld": "schadensbeschreibung",
        "pflicht": True,
        "placeholder": "Beschreiben Sie den Hergang und die Schäden..."
    },
    {
        "id": "fotos",
        "frage": "Haben Sie Fotos vom Schaden? Sie können diese hier hochladen (optional, max. 5 Bilder).",
        "typ": "fotos",
        "feld": "fotos",
        "pflicht": False,
        "bedingung_typ": FOTO_RELEVANT_TYPEN
    },
    {
        "id": "schadensursache",
        "frage": "Was war die Ursache des Schadens?",
        "typ": "text",
        "feld": "schadensursache",
        "pflicht": False,
        "placeholder": "z.B. Auffahrunfall, Wasserschaden, Einbruch..."
    },
    {
        "id": "geschaetzter_betrag",
        "frage": "Wie hoch schätzen Sie den Schaden? (in CHF)",
        "typ": "number",
        "feld": "geschaetzter_betrag",
        "pflicht": False,
        "placeholder": "z.B. 5000"
    },
    {
        "id": "polizeibericht",
        "frage": "Wurde der Vorfall bei der Polizei gemeldet?",
        "typ": "ja_nein",
        "feld": "polizeibericht",
        "pflicht": True
    },
    {
        "id": "polizeiposten",
        "frage": "Bei welchem Polizeiposten wurde die Meldung gemacht?",
        "typ": "text",
        "feld": "polizeiposten",
        "pflicht": False,
        "bedingung": {"feld": "polizeibericht", "wert": True},
        "placeholder": "Name des Polizeipostens"
    },
    {
        "id": "kontakt_telefon",
        "frage": "Unter welcher Telefonnummer können wir Sie erreichen?",
        "typ": "text",
        "feld": "kontakt_telefon",
        "pflicht": True,
        "placeholder": "z.B. 079 123 45 67"
    },
    {
        "id": "kontakt_email",
        "frage": "Wie lautet Ihre E-Mail-Adresse für Rückfragen?",
        "typ": "text",
        "feld": "kontakt_email",
        "pflicht": True,
        "placeholder": "ihre.email@beispiel.ch"
    },
    {
        "id": "bevorzugte_kontaktzeit",
        "frage": "Wann können wir Sie am besten erreichen?",
        "typ": "text",
        "feld": "bevorzugte_kontaktzeit",
        "pflicht": False,
        "placeholder": "z.B. vormittags, nach 18 Uhr..."
    }
]

# Zusätzliche Fragen für Motorfahrzeugschäden
FAHRZEUG_FRAGEN = [
    {
        "id": "fahrzeug_kennzeichen",
        "frage": "Wie lautet das Kennzeichen Ihres Fahrzeugs?",
        "typ": "text",
        "feld": "fahrzeug_kennzeichen",
        "pflicht": True,
        "placeholder": "z.B. ZH 123456"
    },
    {
        "id": "fahrzeug_marke",
        "frage": "Welche Marke und welches Modell hat Ihr Fahrzeug?",
        "typ": "text",
        "feld": "fahrzeug_marke",
        "pflicht": False,
        "placeholder": "z.B. VW Golf"
    },
    {
        "id": "gegner_kennzeichen",
        "frage": "Falls ein anderes Fahrzeug beteiligt war: Wie lautet dessen Kennzeichen?",
        "typ": "text",
        "feld": "gegner_kennzeichen",
        "pflicht": False,
        "placeholder": "z.B. BE 987654 oder 'nicht bekannt'"
    },
    {
        "id": "gegner_versicherung",
        "frage": "Kennen Sie die Versicherung des anderen Fahrzeugs?",
        "typ": "text",
        "feld": "gegner_versicherung",
        "pflicht": False,
        "placeholder": "z.B. Mobiliar, AXA... oder 'unbekannt'"
    }
]


class SchadensmeldungManager:
    """Verwaltet Schadensmeldungen"""

    def __init__(self, user_id: str = "default"):
        self.user_dir = CLAIMS_DIR / user_id
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def save(self, meldung: Schadensmeldung) -> None:
        """Speichert eine Schadensmeldung"""
        meldung.aktualisiert_am = datetime.now().isoformat()
        file_path = self.user_dir / f"{meldung.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(meldung.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, meldung_id: str) -> Optional[Schadensmeldung]:
        """Lädt eine Schadensmeldung"""
        file_path = self.user_dir / f"{meldung_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return Schadensmeldung.from_dict(json.load(f))
        return None

    def list_all(self) -> List[Schadensmeldung]:
        """Listet alle Schadensmeldungen des Users"""
        meldungen = []
        for file_path in self.user_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    meldungen.append(Schadensmeldung.from_dict(json.load(f)))
            except Exception:
                continue
        meldungen.sort(key=lambda m: m.erstellt_am, reverse=True)
        return meldungen

    def delete(self, meldung_id: str) -> bool:
        """Löscht eine Schadensmeldung"""
        file_path = self.user_dir / f"{meldung_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False


def get_manager() -> SchadensmeldungManager:
    """Gibt Manager für aktuellen User zurück"""
    try:
        from app.components.auth_ui import get_current_user
        user = get_current_user()
        user_id = user.id if user else "default"
    except ImportError:
        user_id = "default"
    return SchadensmeldungManager(user_id)


def init_schaden_state():
    """Initialisiert Session State für Schadensmeldung"""
    if "aktuelle_meldung_id" not in st.session_state:
        st.session_state.aktuelle_meldung_id = None
    if "schaden_chat" not in st.session_state:
        st.session_state.schaden_chat = []
    if "schaden_step" not in st.session_state:
        st.session_state.schaden_step = 0
    if "schaden_data" not in st.session_state:
        st.session_state.schaden_data = {}


def get_aktuelle_fragen(schadenstyp: str) -> List[Dict]:
    """Gibt die relevanten Fragen basierend auf Schadenstyp zurück"""
    fragen = FRAGEN_FLOW.copy()

    # Fahrzeug-Fragen einfügen nach Schadensbeschreibung
    if schadenstyp == SchadensTyp.MOTORFAHRZEUG.value:
        insert_idx = next(
            (i for i, f in enumerate(fragen) if f["id"] == "geschaetzter_betrag"),
            len(fragen)
        )
        for i, frage in enumerate(FAHRZEUG_FRAGEN):
            fragen.insert(insert_idx + i, frage)

    return fragen


def sollte_frage_zeigen(frage: Dict, daten: Dict) -> bool:
    """Prüft ob eine Frage basierend auf Bedingungen gezeigt werden soll"""
    # Bedingung für bestimmte Schadenstypen (z.B. Fotos nur bei relevanten Typen)
    if "bedingung_typ" in frage:
        schadenstyp = daten.get("schadenstyp", "")
        if schadenstyp not in frage["bedingung_typ"]:
            return False

    # Standard-Bedingung (Feld == Wert)
    if "bedingung" not in frage:
        return True

    bedingung = frage["bedingung"]
    feld_wert = daten.get(bedingung["feld"])
    return feld_wert == bedingung["wert"]


def render_schadensmeldung():
    """Rendert den Schadensmeldung-Bot"""
    init_schaden_state()
    manager = get_manager()

    st.markdown("## 📋 Schadensmeldung erfassen")
    st.markdown("Ich helfe Ihnen, Ihren Schaden schnell und einfach zu melden.")

    # Neue Meldung starten oder bestehende fortsetzen
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🆕 Neue Schadensmeldung starten", type="primary", use_container_width=True):
            neue_meldung = Schadensmeldung(
                id=str(uuid.uuid4())[:8],
                user_id="default",
                erstellt_am=datetime.now().isoformat(),
                aktualisiert_am=datetime.now().isoformat()
            )
            manager.save(neue_meldung)
            st.session_state.aktuelle_meldung_id = neue_meldung.id
            st.session_state.schaden_chat = []
            st.session_state.schaden_step = 0
            st.session_state.schaden_data = {}
            st.rerun()

    with col2:
        # Entwürfe anzeigen
        entwuerfe = [m for m in manager.list_all() if m.status == SchadensStatus.ENTWURF.value and not m.erfassung_abgeschlossen]
        if entwuerfe:
            optionen = {m.id: f"{m.schadenstyp or 'Neu'} ({m.erstellt_am[:10]})" for m in entwuerfe}
            selected = st.selectbox(
                "Entwurf fortsetzen",
                options=list(optionen.keys()),
                format_func=lambda x: optionen[x],
                key="entwurf_select"
            )
            if st.button("Fortsetzen"):
                st.session_state.aktuelle_meldung_id = selected
                meldung = manager.load(selected)
                st.session_state.schaden_data = meldung.to_dict()
                st.session_state.schaden_step = meldung.aktuelle_frage
                st.session_state.schaden_chat = meldung.chat_history
                st.rerun()

    st.divider()

    # Aktive Erfassung
    if st.session_state.aktuelle_meldung_id:
        meldung = manager.load(st.session_state.aktuelle_meldung_id)

        if meldung and not meldung.erfassung_abgeschlossen:
            render_erfassung_chat(meldung, manager)
        elif meldung and meldung.erfassung_abgeschlossen:
            render_zusammenfassung(meldung, manager)
    else:
        # Willkommensnachricht
        st.info("👋 Willkommen! Klicken Sie auf **'Neue Schadensmeldung starten'** um zu beginnen.")

        # Tipps anzeigen
        with st.expander("ℹ️ Was Sie für die Meldung benötigen"):
            st.markdown("""
            **Halten Sie folgende Informationen bereit:**
            - Ihre Policennummer (falls bekannt)
            - Datum und Uhrzeit des Vorfalls
            - Ort des Geschehens
            - Beschreibung des Schadens
            - Kontaktdaten für Rückfragen

            **Bei Fahrzeugschäden zusätzlich:**
            - Fahrzeugkennzeichen
            - Angaben zum Unfallgegner (falls vorhanden)
            - Polizeirapport-Nummer (falls Polizei involviert)
            """)


def render_erfassung_chat(meldung: Schadensmeldung, manager: SchadensmeldungManager):
    """Rendert den Chat-basierten Erfassungsprozess"""

    # Fortschrittsanzeige
    schadenstyp = st.session_state.schaden_data.get("schadenstyp", "")
    fragen = get_aktuelle_fragen(schadenstyp)
    total_fragen = len([f for f in fragen if sollte_frage_zeigen(f, st.session_state.schaden_data)])
    aktueller_step = st.session_state.schaden_step

    progress = min(aktueller_step / max(total_fragen, 1), 1.0)
    st.progress(progress, text=f"Schritt {aktueller_step + 1} von {total_fragen}")

    # Chat-Container
    chat_container = st.container()

    with chat_container:
        # Begrüssung
        if not st.session_state.schaden_chat:
            bot_msg = {
                "role": "assistant",
                "content": "Guten Tag! Ich bin Ihr Schadensmeldungs-Assistent. Ich werde Ihnen einige Fragen stellen, um Ihren Schaden aufzunehmen. Sie können jederzeit 'zurück' eingeben um zur vorherigen Frage zu gelangen."
            }
            st.session_state.schaden_chat.append(bot_msg)

        # Chat-Verlauf anzeigen
        for msg in st.session_state.schaden_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Aktuelle Frage ermitteln
        while aktueller_step < len(fragen):
            frage = fragen[aktueller_step]
            if sollte_frage_zeigen(frage, st.session_state.schaden_data):
                break
            aktueller_step += 1
            st.session_state.schaden_step = aktueller_step

        if aktueller_step >= len(fragen):
            # Alle Fragen beantwortet
            finalisiere_meldung(meldung, manager)
            return

        aktuelle_frage = fragen[aktueller_step]

        # Frage stellen (falls noch nicht gestellt)
        frage_key = f"frage_{aktuelle_frage['id']}_gestellt"
        if frage_key not in st.session_state:
            bot_msg = {"role": "assistant", "content": aktuelle_frage["frage"]}
            st.session_state.schaden_chat.append(bot_msg)
            st.session_state[frage_key] = True
            with st.chat_message("assistant"):
                st.markdown(aktuelle_frage["frage"])

        # Eingabe je nach Fragetyp
        render_frage_eingabe(aktuelle_frage, meldung, manager, fragen)


def render_frage_eingabe(frage: Dict, meldung: Schadensmeldung, manager: SchadensmeldungManager, fragen: List[Dict]):
    """Rendert die Eingabe für eine Frage"""

    frage_typ = frage["typ"]
    feld = frage["feld"]

    if frage_typ == "auswahl":
        # Buttons für Auswahl
        cols = st.columns(2)
        for i, option in enumerate(frage["optionen"]):
            with cols[i % 2]:
                if st.button(option, key=f"opt_{frage['id']}_{i}", use_container_width=True):
                    verarbeite_antwort(option, frage, meldung, manager)

    elif frage_typ == "ja_nein":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Ja", key=f"ja_{frage['id']}", use_container_width=True):
                verarbeite_antwort(True, frage, meldung, manager)
        with col2:
            if st.button("❌ Nein", key=f"nein_{frage['id']}", use_container_width=True):
                verarbeite_antwort(False, frage, meldung, manager)

    elif frage_typ == "datum":
        datum = st.date_input(
            "Datum wählen",
            value=date.today(),
            max_value=date.today(),
            key=f"datum_{frage['id']}",
            label_visibility="collapsed"
        )
        if st.button("Bestätigen", key=f"confirm_{frage['id']}"):
            verarbeite_antwort(datum.isoformat(), frage, meldung, manager)

    elif frage_typ == "number":
        betrag = st.number_input(
            "Betrag",
            min_value=0.0,
            step=100.0,
            key=f"number_{frage['id']}",
            label_visibility="collapsed"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Bestätigen", key=f"confirm_{frage['id']}"):
                verarbeite_antwort(betrag, frage, meldung, manager)
        with col2:
            if st.button("Überspringen", key=f"skip_{frage['id']}"):
                verarbeite_antwort(0, frage, meldung, manager)

    elif frage_typ == "textarea":
        text = st.text_area(
            "Beschreibung",
            placeholder=frage.get("placeholder", ""),
            key=f"textarea_{frage['id']}",
            label_visibility="collapsed",
            height=150
        )
        if st.button("Weiter", key=f"confirm_{frage['id']}", disabled=not text.strip() if frage.get("pflicht") else False):
            verarbeite_antwort(text, frage, meldung, manager)

    elif frage_typ == "fotos":
        # Foto-Upload
        uploaded_files = st.file_uploader(
            "Fotos hochladen",
            type=["jpg", "jpeg", "png", "heic"],
            accept_multiple_files=True,
            key=f"fotos_{frage['id']}",
            label_visibility="collapsed"
        )

        # Bereits hochgeladene Fotos anzeigen
        existing_fotos = st.session_state.schaden_data.get("fotos", [])
        if existing_fotos:
            st.caption(f"📎 {len(existing_fotos)} Foto(s) bereits hochgeladen")

        # Vorschau der neuen Uploads
        if uploaded_files:
            cols = st.columns(min(len(uploaded_files), 3))
            for i, file in enumerate(uploaded_files[:5]):  # Max 5 Fotos
                with cols[i % 3]:
                    st.image(file, caption=file.name, width=100)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📸 Fotos speichern & weiter", key=f"confirm_{frage['id']}", use_container_width=True):
                foto_pfade = []
                if uploaded_files:
                    for file in uploaded_files[:5]:  # Max 5 Fotos
                        # Foto speichern
                        foto_name = f"{meldung.id}_{uuid.uuid4().hex[:8]}_{file.name}"
                        foto_pfad = FOTOS_DIR / foto_name
                        with open(foto_pfad, "wb") as f:
                            f.write(file.getbuffer())
                        foto_pfade.append(str(foto_pfad))
                # Kombiniere existierende und neue Fotos
                alle_fotos = existing_fotos + foto_pfade
                verarbeite_antwort(alle_fotos, frage, meldung, manager)
        with col2:
            if st.button("⏭️ Überspringen", key=f"skip_{frage['id']}", use_container_width=True):
                verarbeite_antwort(existing_fotos if existing_fotos else [], frage, meldung, manager)

    else:  # text
        text = st.text_input(
            "Eingabe",
            placeholder=frage.get("placeholder", ""),
            key=f"text_{frage['id']}",
            label_visibility="collapsed"
        )

        # Validierungs-State für dieses Feld
        validation_key = f"validation_error_{frage['id']}"

        # Zeige Validierungsfehler falls vorhanden
        if validation_key in st.session_state and st.session_state[validation_key]:
            st.error(st.session_state[validation_key])

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if st.button("Weiter", key=f"confirm_{frage['id']}", disabled=not text.strip() if frage.get("pflicht") else False):
                # Validierung für Telefon und E-Mail
                feld = frage["feld"]
                if feld in ['kontakt_telefon', 'kontakt_email'] and text.strip():
                    is_valid, error_msg, corrected = generate_validation_response(feld, text)
                    if not is_valid:
                        st.session_state[validation_key] = error_msg
                        st.rerun()
                    else:
                        # Validierung erfolgreich - Fehler löschen
                        if validation_key in st.session_state:
                            del st.session_state[validation_key]
                        # Korrigierten Wert verwenden falls vorhanden
                        final_value = corrected if corrected else text
                        verarbeite_antwort(final_value, frage, meldung, manager)
                else:
                    # Keine Validierung nötig
                    if validation_key in st.session_state:
                        del st.session_state[validation_key]
                    verarbeite_antwort(text, frage, meldung, manager)
        with col2:
            if not frage.get("pflicht"):
                if st.button("Überspringen", key=f"skip_{frage['id']}"):
                    if validation_key in st.session_state:
                        del st.session_state[validation_key]
                    verarbeite_antwort("", frage, meldung, manager)
        with col3:
            if st.session_state.schaden_step > 0:
                if st.button("⬅️ Zurück", key=f"back_{frage['id']}"):
                    if validation_key in st.session_state:
                        del st.session_state[validation_key]
                    gehe_zurueck(meldung, manager)


def verarbeite_antwort(antwort: Any, frage: Dict, meldung: Schadensmeldung, manager: SchadensmeldungManager):
    """Verarbeitet eine Antwort und geht zur nächsten Frage"""

    feld = frage["feld"]

    # Antwort in Chat speichern
    if isinstance(antwort, bool):
        antwort_text = "Ja" if antwort else "Nein"
    elif isinstance(antwort, list):
        # Für Fotos: Anzahl anzeigen statt Pfade
        if len(antwort) > 0:
            antwort_text = f"📸 {len(antwort)} Foto(s) hochgeladen"
        else:
            antwort_text = "Keine Fotos hochgeladen"
    else:
        antwort_text = str(antwort) if antwort else "(übersprungen)"

    user_msg = {"role": "user", "content": antwort_text}
    st.session_state.schaden_chat.append(user_msg)

    # Daten speichern
    st.session_state.schaden_data[feld] = antwort

    # Meldung aktualisieren
    setattr(meldung, feld, antwort)
    meldung.aktuelle_frage = st.session_state.schaden_step + 1
    meldung.chat_history = st.session_state.schaden_chat
    manager.save(meldung)

    # Nächste Frage
    st.session_state.schaden_step += 1

    # Frage-gestellt Flag zurücksetzen für nächste Frage
    schadenstyp = st.session_state.schaden_data.get("schadenstyp", "")
    fragen = get_aktuelle_fragen(schadenstyp)
    if st.session_state.schaden_step < len(fragen):
        next_frage = fragen[st.session_state.schaden_step]
        next_key = f"frage_{next_frage['id']}_gestellt"
        if next_key in st.session_state:
            del st.session_state[next_key]

    st.rerun()


def gehe_zurueck(meldung: Schadensmeldung, manager: SchadensmeldungManager):
    """Geht zur vorherigen Frage zurück"""
    if st.session_state.schaden_step > 0:
        st.session_state.schaden_step -= 1

        # Letzte Bot-Nachricht und User-Antwort entfernen
        if len(st.session_state.schaden_chat) >= 2:
            st.session_state.schaden_chat = st.session_state.schaden_chat[:-2]

        # Frage-gestellt Flag zurücksetzen
        schadenstyp = st.session_state.schaden_data.get("schadenstyp", "")
        fragen = get_aktuelle_fragen(schadenstyp)
        if st.session_state.schaden_step < len(fragen):
            frage = fragen[st.session_state.schaden_step]
            frage_key = f"frage_{frage['id']}_gestellt"
            if frage_key in st.session_state:
                del st.session_state[frage_key]

        meldung.aktuelle_frage = st.session_state.schaden_step
        meldung.chat_history = st.session_state.schaden_chat
        manager.save(meldung)

        st.rerun()


def finalisiere_meldung(meldung: Schadensmeldung, manager: SchadensmeldungManager):
    """Finalisiert die Schadensmeldung"""

    # Alle Daten in Meldung übertragen
    for key, value in st.session_state.schaden_data.items():
        if hasattr(meldung, key):
            setattr(meldung, key, value)

    meldung.erfassung_abgeschlossen = True
    meldung.chat_history = st.session_state.schaden_chat
    manager.save(meldung)

    # Abschlussnachricht
    bot_msg = {
        "role": "assistant",
        "content": "🎉 **Vielen Dank!** Ihre Schadensmeldung wurde erfolgreich erfasst. Sie können die Zusammenfassung unten prüfen und die Meldung einreichen."
    }
    st.session_state.schaden_chat.append(bot_msg)

    with st.chat_message("assistant"):
        st.markdown(bot_msg["content"])

    st.rerun()


def render_risk_analysis(meldung: Schadensmeldung):
    """
    Zeigt die Fuzzy-Logik Risikoanalyse für eine Schadensmeldung
    """
    # Risiko berechnen
    result = fuzzy_risk_engine.analyse_schadensmeldung(meldung)

    # Farben für Risikostufen
    risk_colors = {
        RiskLevel.SEHR_NIEDRIG: ("#22c55e", "#166534"),  # Grün
        RiskLevel.NIEDRIG: ("#84cc16", "#3f6212"),       # Hellgrün
        RiskLevel.MITTEL: ("#eab308", "#854d0e"),        # Gelb
        RiskLevel.HOCH: ("#f97316", "#c2410c"),          # Orange
        RiskLevel.SEHR_HOCH: ("#ef4444", "#b91c1c")      # Rot
    }

    bg_color, text_color = risk_colors.get(result.level, ("#6b7280", "#374151"))

    # Risk Analysis Container
    with st.container(border=True):
        st.markdown("**🔍 Fuzzy-Logik Risikoanalyse**")

        # Score und Level in Spalten
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            # Risiko-Score als Gauge
            st.markdown(f"""
            <div style="text-align: center; padding: 10px;">
                <div style="font-size: 42px; font-weight: bold; color: {bg_color};">
                    {result.score:.0f}
                </div>
                <div style="font-size: 12px; color: #6b7280;">Score (0-100)</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            # Risikostufe Badge
            st.markdown(f"""
            <div style="text-align: center; padding: 10px;">
                <div style="
                    display: inline-block;
                    background-color: {bg_color};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 14px;
                ">
                    {result.level.value}
                </div>
                <div style="font-size: 12px; color: #6b7280; margin-top: 8px;">Risikostufe</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            # Empfehlung
            st.markdown(f"""
            <div style="padding: 10px; background-color: rgba(0,0,0,0.05); border-radius: 8px;">
                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">📋 Empfehlung</div>
                <div style="font-size: 13px;">{result.empfehlung}</div>
            </div>
            """, unsafe_allow_html=True)

        # Expander für Details
        with st.expander("📊 Details zur Analyse"):
            # Faktoren als Tabelle
            st.markdown("**Bewertete Faktoren:**")

            for faktor in result.faktoren:
                einfluss_icon = "🔴" if faktor["einfluss"] == "hoch" else "🟡" if faktor["einfluss"] == "mittel" else "🟢"
                st.markdown(f"""
                - **{faktor['name']}**: {faktor['wert']} → _{faktor['bewertung']}_ {einfluss_icon}
                """)

            st.markdown("---")
            st.markdown("**Aktivierte Regeln:**")
            st.text(result.erklaerung)

            st.markdown("---")
            st.caption("""
            ℹ️ **Über Fuzzy-Logik Risikoanalyse:**
            Diese Analyse verwendet unscharfe Logik (Fuzzy Logic) um mehrere Faktoren
            wie Schadenshöhe, Vertragsdauer und Vollständigkeit der Angaben zu bewerten.
            Das Ergebnis dient als Entscheidungsunterstützung für Sachbearbeiter.
            """)


def render_zusammenfassung(meldung: Schadensmeldung, manager: SchadensmeldungManager):
    """Zeigt die Zusammenfassung einer abgeschlossenen Erfassung"""

    st.success("✅ Schadensmeldung erfasst!")

    # Zusammenfassung in Karten
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**📋 Schadensdetails**")
            st.write(f"**Typ:** {meldung.schadenstyp}")
            st.write(f"**Datum:** {meldung.schadensdatum}")
            if meldung.schadenszeit:
                st.write(f"**Zeit:** {meldung.schadenszeit}")
            st.write(f"**Ort:** {meldung.schadensort}")
            if meldung.geschaetzter_betrag:
                st.write(f"**Geschätzter Betrag:** CHF {meldung.geschaetzter_betrag:,.2f}")

    with col2:
        with st.container(border=True):
            st.markdown("**📞 Kontakt**")
            st.write(f"**Telefon:** {meldung.kontakt_telefon}")
            st.write(f"**E-Mail:** {meldung.kontakt_email}")
            if meldung.bevorzugte_kontaktzeit:
                st.write(f"**Erreichbar:** {meldung.bevorzugte_kontaktzeit}")
            st.write(f"**Polizeimeldung:** {'Ja' if meldung.polizeibericht else 'Nein'}")

    with st.container(border=True):
        st.markdown("**📝 Beschreibung**")
        st.write(meldung.schadensbeschreibung)

    # Fahrzeugdaten falls vorhanden
    if meldung.schadenstyp == SchadensTyp.MOTORFAHRZEUG.value and meldung.fahrzeug_kennzeichen:
        with st.container(border=True):
            st.markdown("**🚗 Fahrzeugdaten**")
            st.write(f"**Kennzeichen:** {meldung.fahrzeug_kennzeichen}")
            if meldung.fahrzeug_marke:
                st.write(f"**Fahrzeug:** {meldung.fahrzeug_marke}")
            if meldung.gegner_kennzeichen:
                st.write(f"**Gegner-Kennzeichen:** {meldung.gegner_kennzeichen}")
            if meldung.gegner_versicherung:
                st.write(f"**Gegner-Versicherung:** {meldung.gegner_versicherung}")

    # Hochgeladene Fotos anzeigen
    if meldung.fotos and len(meldung.fotos) > 0:
        with st.container(border=True):
            st.markdown(f"**📸 Fotos ({len(meldung.fotos)})**")
            cols = st.columns(min(len(meldung.fotos), 3))
            for i, foto_pfad in enumerate(meldung.fotos[:6]):  # Max 6 anzeigen
                with cols[i % 3]:
                    try:
                        st.image(foto_pfad, use_container_width=True)
                    except Exception:
                        st.caption(f"📎 {Path(foto_pfad).name}")

    # === FUZZY RISK ANALYSE ===
    render_risk_analysis(meldung)

    st.divider()

    # Aktionen
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤 Meldung einreichen", type="primary", use_container_width=True):
            meldung.status = SchadensStatus.EINGEREICHT.value
            manager.save(meldung)
            st.success("✅ Ihre Schadensmeldung wurde eingereicht! Sie erhalten in Kürze eine Bestätigung.")
            st.session_state.aktuelle_meldung_id = None
            st.session_state.schaden_chat = []
            st.session_state.schaden_data = {}
            st.session_state.schaden_step = 0

    with col2:
        if st.button("✏️ Bearbeiten", use_container_width=True):
            meldung.erfassung_abgeschlossen = False
            meldung.aktuelle_frage = 0
            manager.save(meldung)
            st.session_state.schaden_step = 0
            st.session_state.schaden_chat = []
            # Alle Frage-gestellt Flags zurücksetzen
            keys_to_delete = [k for k in st.session_state.keys() if k.startswith("frage_") and k.endswith("_gestellt")]
            for k in keys_to_delete:
                del st.session_state[k]
            st.rerun()

    with col3:
        if st.button("🗑️ Verwerfen", use_container_width=True):
            manager.delete(meldung.id)
            st.session_state.aktuelle_meldung_id = None
            st.session_state.schaden_chat = []
            st.session_state.schaden_data = {}
            st.session_state.schaden_step = 0
            st.rerun()


def render_schadensmeldungen_liste():
    """Zeigt alle Schadensmeldungen des Benutzers"""
    init_schaden_state()
    manager = get_manager()

    st.markdown("## 📁 Meine Schadensmeldungen")

    meldungen = manager.list_all()

    if not meldungen:
        st.info("Sie haben noch keine Schadensmeldungen erfasst.")
        if st.button("➕ Erste Schadensmeldung erstellen"):
            st.session_state.current_page = "schadensmeldung"
            st.rerun()
        return

    # Filter
    col1, col2 = st.columns([2, 1])
    with col1:
        status_filter = st.multiselect(
            "Status filtern",
            options=[s.value for s in SchadensStatus],
            default=[s.value for s in SchadensStatus],
            key="status_filter"
        )

    # Gefilterte Meldungen
    gefiltert = [m for m in meldungen if m.status in status_filter]

    st.caption(f"{len(gefiltert)} Schadensmeldung(en)")

    for meldung in gefiltert:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                typ_emoji = {
                    "Motorfahrzeug": "🚗",
                    "Hausrat": "🏠",
                    "Gebäude": "🏢",
                    "Haftpflicht": "⚖️",
                    "Reise": "✈️",
                    "Rechtsschutz": "📜",
                    "Unfall": "🚑",
                    "Andere": "📋"
                }.get(meldung.schadenstyp, "📋")

                st.markdown(f"**{typ_emoji} {meldung.schadenstyp or 'Nicht angegeben'}**")
                st.caption(f"Erstellt: {meldung.erstellt_am[:10]}")

            with col2:
                status_farbe = {
                    SchadensStatus.ENTWURF.value: "🟡",
                    SchadensStatus.EINGEREICHT.value: "🔵",
                    SchadensStatus.IN_BEARBEITUNG.value: "🟠",
                    SchadensStatus.ABGESCHLOSSEN.value: "🟢"
                }.get(meldung.status, "⚪")
                st.markdown(f"{status_farbe} {meldung.status}")

            with col3:
                if meldung.geschaetzter_betrag:
                    st.markdown(f"**CHF {meldung.geschaetzter_betrag:,.0f}**")
                else:
                    st.caption("Betrag offen")

            with col4:
                if st.button("Details", key=f"details_{meldung.id}"):
                    st.session_state.detail_meldung_id = meldung.id
                    st.rerun()

    # Detail-Ansicht
    if "detail_meldung_id" in st.session_state and st.session_state.detail_meldung_id:
        meldung = manager.load(st.session_state.detail_meldung_id)
        if meldung:
            st.divider()
            render_detail_ansicht(meldung, manager)


def render_detail_ansicht(meldung: Schadensmeldung, manager: SchadensmeldungManager):
    """Zeigt die Detailansicht einer Schadensmeldung"""

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"### Details: {meldung.schadenstyp}")
    with col2:
        if st.button("✖️ Schliessen"):
            st.session_state.detail_meldung_id = None
            st.rerun()

    # Tabs: Schadensinfo, Risikoanalyse, Fotos (falls vorhanden), Chat-Verlauf
    has_fotos = meldung.fotos and len(meldung.fotos) > 0
    if has_fotos:
        tab1, tab_risk, tab2, tab3 = st.tabs(["📋 Schadensinfo", "🔍 Risikoanalyse", "📸 Fotos", "💬 Chat-Verlauf"])
    else:
        tab1, tab_risk, tab3 = st.tabs(["📋 Schadensinfo", "🔍 Risikoanalyse", "💬 Chat-Verlauf"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Grunddaten**")
            st.write(f"- **ID:** {meldung.id}")
            st.write(f"- **Status:** {meldung.status}")
            st.write(f"- **Policennummer:** {meldung.polizennummer or 'Nicht angegeben'}")
            st.write(f"- **Schadensdatum:** {meldung.schadensdatum}")
            st.write(f"- **Schadensort:** {meldung.schadensort}")

        with col2:
            st.markdown("**Kontakt**")
            st.write(f"- **Telefon:** {meldung.kontakt_telefon}")
            st.write(f"- **E-Mail:** {meldung.kontakt_email}")
            st.write(f"- **Erreichbar:** {meldung.bevorzugte_kontaktzeit or 'Keine Angabe'}")

        st.markdown("**Beschreibung**")
        st.write(meldung.schadensbeschreibung or "Keine Beschreibung")

        if meldung.geschaetzter_betrag:
            st.metric("Geschätzter Schaden", f"CHF {meldung.geschaetzter_betrag:,.2f}")

    with tab_risk:
        render_risk_analysis(meldung)

    if has_fotos:
        with tab2:
            st.markdown(f"**{len(meldung.fotos)} Foto(s) hochgeladen**")
            cols = st.columns(3)
            for i, foto_pfad in enumerate(meldung.fotos):
                with cols[i % 3]:
                    try:
                        st.image(foto_pfad, use_container_width=True)
                        st.caption(Path(foto_pfad).name)
                    except Exception:
                        st.caption(f"📎 {Path(foto_pfad).name}")

    with tab3:
        if meldung.chat_history:
            for msg in meldung.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        else:
            st.info("Kein Chat-Verlauf vorhanden")
