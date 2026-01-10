"""
Baloise Knowledge Assistant - Konfiguration
Versicherungs-Chatbot mit RAG und Schadensmeldung
"""

import os
from pathlib import Path

# .env Datei laden (überschreibt System-Variablen)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# Basis-Pfade
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
KNOWLEDGE_BASES_DIR = DATA_DIR / "knowledge_bases"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

# Verzeichnisse erstellen falls nicht vorhanden
for dir_path in [UPLOADS_DIR, KNOWLEDGE_BASES_DIR, CHROMA_DB_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


class LLMProvider(Enum):
    """Verfügbare LLM-Anbieter (nur Cloud APIs)"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class STTProvider(Enum):
    """Verfügbare Speech-to-Text Anbieter"""
    WHISPER_LOCAL = "whisper_local"      # Lokales (faster-whisper)
    WHISPER_OPENAI = "whisper_openai"    # OpenAI Whisper API
    GOOGLE = "google"                     # Google Cloud Speech-to-Text (Schweizerdeutsch!)


class EmbeddingMode(Enum):
    """Embedding-Modus für RAG"""
    LOCAL_ONLY = "local"           # Nur lokales Modell (Ollama)
    API_ONLY = "api"               # Nur OpenAI API
    BOTH = "both"                  # Beide Modelle (Standard für neue Dokumente)


class UserRole(Enum):
    """Benutzerrollen"""
    ADMIN = "admin"
    POWER_USER = "power_user"
    STANDARD_USER = "standard_user"


@dataclass
class LLMConfig:
    """LLM-Konfiguration (nur Cloud APIs)"""
    provider: LLMProvider = LLMProvider.OPENAI
    
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o"
    openai_model_mini: str = "gpt-4o-mini"
    
    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = "claude-sonnet-4-20250514"
    
    # Google
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_model: str = "gemini-1.5-pro"
    google_model_flash: str = "gemini-1.5-flash"

    # ============ Sampling Parameter ============
    # Diese Parameter steuern wie das LLM Tokens auswählt

    # Temperature: Kontrolliert Zufälligkeit (0=deterministisch, 1+=kreativ)
    # Für RAG/Fakten empfohlen: 0.3-0.5
    temperature: float = 0.4

    # Top-P (Nucleus Sampling): Kumulative Wahrscheinlichkeits-Schwelle
    # 0.9 = fokussierter, 0.95 = breiter
    top_p: float = 0.9

    # Max Tokens: Maximale Antwortlänge
    # None = Provider-Default
    max_tokens: Optional[int] = None

    # Repeat Penalty: Bestraft Wiederholungen (1.0=keine, 1.1=leicht, 1.5=stark)
    # Nur bei Ollama und OpenAI (frequency_penalty) unterstützt
    repeat_penalty: float = 1.1


@dataclass
class STTConfig:
    """Speech-to-Text Konfiguration"""
    provider: STTProvider = STTProvider.WHISPER_LOCAL

    # Lokales Whisper (faster-whisper)
    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium, large-v3
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")  # cpu, cuda, auto
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8, float16, float32

    # OpenAI Whisper API (nutzt openai_api_key aus LLMConfig)
    openai_model: str = "whisper-1"

    # Google Cloud Speech-to-Text
    google_api_key: str = os.getenv("GOOGLE_STT_API_KEY", "")
    google_credentials_path: str = os.getenv("GOOGLE_STT_CREDENTIALS", "")  # Alternative: Service Account
    google_language_code: str = "de-CH"  # Schweizerdeutsch!

    # Gemeinsame Einstellungen
    language: str = "de"
    output_format: str = "text"  # text, json, vtt, srt


@dataclass
class EmbeddingConfig:
    """Embedding-Konfiguration"""
    # Lokal via Ollama
    local_model: str = "nomic-embed-text"
    local_dimensions: int = 768

    # Cloud via OpenAI
    openai_model: str = "text-embedding-3-small"
    openai_dimensions: int = 1536

    # Embedding-Modus: local, api, oder both
    mode: EmbeddingMode = EmbeddingMode.BOTH

    # Welches Modell für Suche verwenden (wenn mode=both)
    # OpenAI liefert deutlich bessere Suchergebnisse als lokale Embeddings
    search_provider: str = "openai"  # "local" oder "openai"

    # Legacy-Kompatibilität
    use_local: bool = True


@dataclass
class RAGConfig:
    """RAG-Konfiguration"""
    # Chunking-Parameter (optimiert für Gemeindewissen/Reglemente)
    # 800 Zeichen ≈ 150-200 Tokens - guter Kompromiss zwischen Kontext und Präzision
    chunk_size: int = 800
    # 100 Zeichen Überlappung (~12.5%) - verhindert Informationsverlust an Chunk-Grenzen
    chunk_overlap: int = 100

    # Suchparameter - Differenziert nach LLM-Typ
    # Lokale Modelle (Ollama) haben kleinere Kontextfenster (8k-32k Tokens)
    top_k_local: int = 5
    # API-Modelle (OpenAI, Anthropic, Google) haben grosse Kontextfenster (128k-200k)
    top_k_api: int = 12
    # Legacy/Fallback
    top_k_results: int = 5
    similarity_threshold: float = 0.5

    # ChromaDB
    collection_prefix: str = "sp_kb_"


@dataclass
class ScrapingConfig:
    """Scraping-Agent Konfiguration"""
    max_depth: int = 3
    max_pages: int = 100
    rate_limit_seconds: float = 1.0
    respect_robots_txt: bool = True
    user_agent: str = "KMU Knowledge Assistant Bot/1.0"


@dataclass
class UIConfig:
    """UI-Konfiguration (Baloise Branding)"""
    app_title: str = "Baloise Assistant"
    primary_color: str = "#003366"  # Baloise Dunkelblau
    secondary_color: str = "#e63312"  # Baloise Rot
    background_color: str = "#f5f7fa"
    text_color: str = "#1a1a1a"

    # Logo-Pfad (falls vorhanden)
    logo_path: Optional[str] = None

    # Sidebar-Icons
    icons: dict = field(default_factory=lambda: {
        "chat": "💬",
        "knowledge": "📚",
        "schadensmeldung": "📋",
        "admin": "⚙️",
        "user": "👤"
    })


@dataclass
class AppConfig:
    """Haupt-Konfiguration"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Performance
    response_timeout_local: int = 5  # Sekunden
    response_timeout_api: int = 3  # Sekunden
    
    # Sprache
    language: str = "de"
    
    # Debug-Modus
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


# Globale Konfiguration
config = AppConfig()


# Unterstützte Dokumentformate
SUPPORTED_FORMATS = {
    "text": {
        "extensions": [".pdf", ".docx", ".txt", ".md", ".rtf"],
        "mime_types": [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
            "application/rtf"
        ]
    },
    "tables": {
        "extensions": [".xlsx", ".csv"],
        "mime_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/csv"
        ]
    },
    "email": {
        "extensions": [".msg", ".eml"],
        "mime_types": [
            "application/vnd.ms-outlook",
            "message/rfc822"
        ]
    },
    "images": {
        "extensions": [".png", ".jpg", ".jpeg", ".tiff"],
        "mime_types": [
            "image/png",
            "image/jpeg",
            "image/tiff"
        ]
    },
    "web": {
        "extensions": [".html", ".htm"],
        "mime_types": [
            "text/html"
        ]
    }
}

# Alle unterstützten Erweiterungen
ALL_EXTENSIONS = []
for category in SUPPORTED_FORMATS.values():
    ALL_EXTENSIONS.extend(category["extensions"])


# Standard-Wissensbasen für Baloise
DEFAULT_KNOWLEDGE_BASES = [
    {
        "id": "versicherungsbedingungen",
        "name": "Versicherungsbedingungen",
        "description": "AVB, Policen, Deckungen",
        "icon": "📜"
    },
    {
        "id": "schadenbearbeitung",
        "name": "Schadenbearbeitung",
        "description": "Prozesse, Richtlinien, Formulare",
        "icon": "📋"
    },
    {
        "id": "produkte",
        "name": "Produktinformationen",
        "description": "Versicherungsprodukte, Tarife",
        "icon": "🛡️"
    },
    {
        "id": "kundenservice",
        "name": "Kundenservice",
        "description": "FAQ, Anleitungen, Support",
        "icon": "💬"
    },
    {
        "id": "rechtliches",
        "name": "Rechtliche Grundlagen",
        "description": "VVG, Gesetze, Compliance",
        "icon": "⚖️"
    }
]


# Initiale Benutzer
INITIAL_USERS = [
    {
        "id": "admin",
        "name": "Administrator",
        "role": UserRole.ADMIN
    },
    {
        "id": "user1",
        "name": "Benutzer 1",
        "role": UserRole.STANDARD_USER
    }
]
