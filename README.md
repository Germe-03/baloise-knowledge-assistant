# Baloise Knowledge Assistant

Intelligenter Versicherungs-Chatbot mit RAG (Retrieval-Augmented Generation) und integriertem Schadensmeldung-Bot.

## Features

### 💬 Chat
- KI-gestützter Chatbot für Versicherungsfragen
- RAG-Integration für kontextbezogene Antworten aus der Wissensbasis
- Chat-Historie mit Speicherung
- Multi-LLM Support (OpenAI, Anthropic, Google, Ollama)

### 📋 Schadensmeldung Bot
- Geführte Schadenserfassung im Chat-Format
- Unterstützte Schadensarten:
  - Motorfahrzeug
  - Hausrat
  - Gebäude
  - Haftpflicht
  - Reise
  - Rechtsschutz
  - Unfall
- Speicherung und Verwaltung aller Meldungen
- Status-Tracking (Entwurf → Eingereicht → In Bearbeitung → Abgeschlossen)

### 📚 Wissensbasis (RAG)
- Dokument-Upload (PDF, Word, Excel, etc.)
- Automatische Indexierung mit ChromaDB
- Hybrid Search (BM25 + Vektorsuche)
- Mehrere Wissensbasen möglich

## Installation

```bash
# In das Projektverzeichnis wechseln
cd rag_baloise

# Python-Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# .env Datei erstellen
cp .env.example .env
# API-Keys in .env eintragen

# Starten
streamlit run app/main.py
```

## Konfiguration

### .env Datei
```env
# LLM Provider (mindestens einer)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Oder lokales Ollama
OLLAMA_HOST=http://localhost:11434
```

### Unterstützte LLM-Provider
- **OpenAI** (GPT-4, GPT-4o)
- **Anthropic** (Claude 3.5 Sonnet)
- **Google** (Gemini 1.5 Pro)
- **Ollama** (Mistral, Llama, etc.)

## Projektstruktur

```
rag_baloise/
├── app/
│   ├── main.py              # Hauptanwendung
│   ├── config.py            # Konfiguration
│   ├── components/
│   │   ├── chat.py          # Chat-Interface
│   │   ├── schadensmeldung.py  # Schadensmeldung-Bot
│   │   ├── knowledge_manager.py # Wissensbasis-Verwaltung
│   │   ├── admin_panel.py   # Admin-Bereich
│   │   └── auth_ui.py       # Authentifizierung
│   ├── core/
│   │   ├── rag_engine.py    # RAG-Engine mit Hybrid Search
│   │   ├── llm_provider.py  # LLM-Anbindung
│   │   └── embeddings.py    # Embedding-Generierung
│   └── utils/
├── data/
│   ├── schadensmeldungen/   # Gespeicherte Schäden
│   ├── knowledge_bases/     # Wissensbasis-Metadaten
│   ├── chroma_db/          # Vektor-Datenbank
│   └── uploads/            # Hochgeladene Dokumente
└── requirements.txt
```

## Schadensmeldung-Flow

1. **Neue Meldung starten** → Bot begrüsst und startet Erfassung
2. **Schadensart wählen** → Motorfahrzeug, Hausrat, etc.
3. **Details erfassen** → Datum, Ort, Beschreibung
4. **Kontaktdaten** → Telefon, E-Mail
5. **Zusammenfassung** → Prüfen und Einreichen

## Standard-Wissensbasen

- **Versicherungsbedingungen** - AVB, Policen, Deckungen
- **Schadenbearbeitung** - Prozesse, Richtlinien, Formulare
- **Produktinformationen** - Versicherungsprodukte, Tarife
- **Kundenservice** - FAQ, Anleitungen, Support
- **Rechtliche Grundlagen** - VVG, Gesetze, Compliance

## Baloise Branding

- Farben: Dunkelblau (#003366), Rot (#e63312)
- Modernes, professionelles Design
- Responsive Sidebar-Navigation

## Technische Details

| Komponente | Konfiguration |
|------------|---------------|
| Chunk-Grösse | 800 Zeichen |
| Chunk-Überlappung | 100 Zeichen (12.5%) |
| Lokales Embedding | nomic-embed-text (768 Dim.) |
| Cloud Embedding | text-embedding-3-small (1536 Dim.) |
| LLM Temperature | 0.4 (optimiert für RAG) |

## Lizenz

Proprietär - Nur für internen Gebrauch
