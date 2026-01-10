"""
KMU Knowledge Assistant - Embedding-Modul
Dual-Embedding Support: Lokale Embeddings via Ollama UND Cloud via OpenAI
"""

import httpx
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from app.config import config, EmbeddingMode


class EmbeddingProvider(Enum):
    """Verfügbare Embedding-Provider"""
    LOCAL = "local"     # Ollama (nomic-embed-text)
    OPENAI = "openai"   # OpenAI API (text-embedding-3-small)


@dataclass
class EmbeddingResult:
    """Embedding-Ergebnis"""
    embeddings: List[List[float]]
    model: str
    provider: str
    dimensions: int


@dataclass
class DualEmbeddingResult:
    """Ergebnis für Dual-Embedding (beide Provider)"""
    local: Optional[EmbeddingResult] = None
    openai: Optional[EmbeddingResult] = None

    @property
    def local_available(self) -> bool:
        return self.local is not None and len(self.local.embeddings) > 0

    @property
    def openai_available(self) -> bool:
        return self.openai is not None and len(self.openai.embeddings) > 0

    def get_embeddings(self, provider: str = "local") -> Optional[List[List[float]]]:
        """Gibt Embeddings für den gewählten Provider zurück"""
        if provider == "local" and self.local:
            return self.local.embeddings
        elif provider == "openai" and self.openai:
            return self.openai.embeddings
        return None


class EmbeddingService:
    """Embedding Service - nur OpenAI API"""

    def __init__(self):
        self.local_model = config.embedding.local_model
        self.openai_model = config.embedding.openai_model
        self.mode = EmbeddingMode.API_ONLY  # Nur API

    def ollama_available(self) -> bool:
        """Ollama deaktiviert - nur API"""
        return False

    def openai_available(self) -> bool:
        """Prüft OpenAI-Verfügbarkeit"""
        return bool(config.llm.openai_api_key)

    def get_provider_status(self) -> Dict[str, bool]:
        """Gibt Status beider Provider zurück"""
        return {
            "local": self.ollama_available(),
            "openai": self.openai_available()
        }

    # ============ Einzelne Provider ============

    def embed_with_local(self, texts: List[str]) -> Optional[EmbeddingResult]:
        """Erstellt Embeddings nur mit lokalem Modell (Ollama)"""
        if not texts:
            return None

        if not self.ollama_available():
            return None

        try:
            embeddings = []
            for text in texts:
                response = httpx.post(
                    f"{self.ollama_host}/api/embeddings",
                    json={
                        "model": self.local_model,
                        "prompt": text
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])

            return EmbeddingResult(
                embeddings=embeddings,
                model=self.local_model,
                provider="local",
                dimensions=len(embeddings[0]) if embeddings else config.embedding.local_dimensions
            )
        except Exception as e:
            print(f"Fehler bei lokalem Embedding: {e}")
            return None

    def embed_with_openai(self, texts: List[str]) -> Optional[EmbeddingResult]:
        """Erstellt Embeddings nur mit OpenAI API"""
        if not texts:
            return None

        if not self.openai_available():
            return None

        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {config.llm.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.openai_model,
                    "input": texts
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            embeddings = [item["embedding"] for item in data["data"]]

            return EmbeddingResult(
                embeddings=embeddings,
                model=self.openai_model,
                provider="openai",
                dimensions=len(embeddings[0]) if embeddings else config.embedding.openai_dimensions
            )
        except Exception as e:
            print(f"Fehler bei OpenAI Embedding: {e}")
            return None

    # ============ Dual-Embedding ============

    def embed_dual(self, texts: List[str]) -> DualEmbeddingResult:
        """
        Erstellt Embeddings mit BEIDEN Providern (für mode=both).
        Gibt DualEmbeddingResult zurück mit separaten Ergebnissen.
        """
        result = DualEmbeddingResult()

        if not texts:
            return result

        # Lokal
        if self.mode in [EmbeddingMode.LOCAL_ONLY, EmbeddingMode.BOTH]:
            result.local = self.embed_with_local(texts)

        # OpenAI
        if self.mode in [EmbeddingMode.API_ONLY, EmbeddingMode.BOTH]:
            result.openai = self.embed_with_openai(texts)

        return result

    # ============ Einzelner Text ============

    def embed_text(self, text: str, provider: str = "auto") -> Optional[List[float]]:
        """
        Erstellt Embedding für einen einzelnen Text.

        Args:
            text: Der zu embeddende Text
            provider: "local", "openai", oder "auto" (nutzt search_provider aus config)

        Returns:
            Embedding-Vektor oder None bei Fehler
        """
        if provider == "auto":
            provider = config.embedding.search_provider

        if provider == "local":
            result = self.embed_with_local([text])
        else:
            result = self.embed_with_openai([text])

        if result and result.embeddings:
            return result.embeddings[0]
        return None

    # ============ Legacy-Kompatibilität ============

    def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        """
        Legacy-Methode für Rückwärtskompatibilität.
        Verwendet search_provider aus config.
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                model="none",
                provider="none",
                dimensions=0
            )

        provider = config.embedding.search_provider

        if provider == "local":
            result = self.embed_with_local(texts)
        else:
            result = self.embed_with_openai(texts)

        if result:
            return result

        # Fallback zum anderen Provider wenn der primäre fehlschlägt
        if provider == "local":
            result = self.embed_with_openai(texts)
        else:
            result = self.embed_with_local(texts)

        if result:
            return result

        raise RuntimeError(
            "Kein Embedding-Provider verfügbar. "
            "Bitte starten Sie Ollama oder konfigurieren Sie einen OpenAI API-Key."
        )

    # ============ Utilities ============

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Berechnet Kosinus-Ähnlichkeit zwischen zwei Vektoren"""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Globale Instanz
embedding_service = EmbeddingService()

# Legacy-Alias für Rückwärtskompatibilität
embedding_provider = embedding_service
