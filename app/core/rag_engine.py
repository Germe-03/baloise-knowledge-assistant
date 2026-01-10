"""
KMU Knowledge Assistant - RAG Engine
ChromaDB-basierte Vektordatenbank mit Multi-Collection Support
Hybrid Search: BM25 + Vektor-Suche mit Reciprocal Rank Fusion (RRF)
"""

import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
import pickle

from rank_bm25 import BM25Okapi

from app.config import config, CHROMA_DB_DIR, DEFAULT_KNOWLEDGE_BASES, EmbeddingMode, LLMProvider
from app.core.embeddings import embedding_service, embedding_provider
from app.core.document_processor import DocumentChunk, ProcessedDocument
from app.core.llm_provider import llm_provider


# ============ BM25 Index Management ============

class BM25Index:
    """BM25-Index für eine Wissensbank"""

    # Deutsche Stoppwörter + URL-Artefakte + normalisierte Umlaute
    GERMAN_STOPWORDS = {
        # Artikel
        'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 'eines',
        'einem', 'einen',
        # Konjunktionen
        'und', 'oder', 'aber', 'wenn', 'weil', 'dass', 'als', 'ob', 'falls',
        # Adverbien
        'auch', 'nur', 'noch', 'schon', 'wieder', 'immer', 'sehr', 'mehr', 'viel',
        'hier', 'dort', 'da', 'nun', 'dann', 'also', 'doch', 'ja', 'nein',
        'gut', 'neu', 'alt', 'gross', 'klein', 'lang', 'kurz', 'jetzt', 'heute',
        # Hilfsverben
        'ist', 'sind', 'war', 'waren', 'wird', 'werden', 'wurde', 'wurden', 'hat',
        'haben', 'hatte', 'hatten', 'kann', 'können', 'konnte', 'konnten', 'muss',
        'müssen', 'musste', 'mussten', 'soll', 'sollen', 'sollte', 'sollten',
        'will', 'wollen', 'wollte', 'wollten', 'darf', 'dürfen', 'durfte', 'durften',
        'sein', 'seine', 'seiner', 'seinem', 'seinen', 'seines',
        # Pronomen (inkl. fehlende)
        'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'sich', 'mich', 'dich',
        'ihn', 'ihm', 'ihnen', 'uns', 'euch', 'mir', 'dir', 'am', 'im', 'zum', 'zur',
        'mein', 'dein', 'unser', 'euer', 'eure', 'eurer', 'eurem', 'euren',
        # Demonstrativpronomen
        'dieser', 'diese', 'dieses', 'diesem', 'diesen', 'jener', 'jene', 'jenes',
        'welcher', 'welche', 'welches', 'welchem', 'welchen',
        # Präpositionen
        'mit', 'bei', 'nach', 'von', 'zu', 'aus', 'in', 'an', 'auf', 'für', 'über',
        'unter', 'vor', 'hinter', 'neben', 'zwischen', 'durch', 'gegen', 'ohne',
        'um', 'bis', 'seit', 'während', 'wegen', 'trotz', 'samt', 'nebst',
        # Negation
        'nicht', 'kein', 'keine', 'keiner', 'keines', 'keinem', 'keinen', 'nichts',
        # Fragewörter
        'so', 'wie', 'was', 'wer', 'wo', 'wann', 'warum', 'weshalb', 'woher', 'wohin',
        # Sonstige
        'alle', 'allem', 'allen', 'aller', 'alles', 'andere', 'anderem', 'anderen',
        'anderer', 'anderes', 'beide', 'beiden', 'beider', 'beides',
        'etwa', 'etwas', 'man', 'mehr', 'meist', 'meisten', 'viele', 'vielen',
        'wenig', 'wenige', 'weniger', 'wenigsten',

        # === URL-Artefakte (Web-Scraping) ===
        'url', 'http', 'https', 'www', 'html', 'htm', 'php', 'asp', 'aspx', 'jsp',
        'com', 'org', 'net', 'edu', 'gov', 'info',
        'ch', 'de', 'at', 'li',  # Länder-Domains (DACH-Region)

        # === Normalisierte Umlaute (da tokenize() ae/oe/ue macht) ===
        'fuer', 'ueber', 'waehrend', 'koennen', 'koennten', 'muessen', 'muessten',
        'duerfen', 'duerften', 'wuerden', 'wuerde', 'grosse', 'grosser', 'grossem',
        'aehnlich', 'aehnliche', 'naechste', 'naechsten', 'naechster',

        # === Scraping-Artefakte ===
        'gescrapt', 'scraping', 'oeffnen', 'schliessen', 'klicken', 'button',
        'navigation', 'menu', 'footer', 'header', 'sidebar', 'cookie', 'cookies',
        'datenschutz', 'impressum', 'agb', 'kontakt', 'suche', 'suchen',
        'seite', 'seiten', 'weiter', 'zurueck', 'home', 'startseite',

        # === Zeitstempel-Artefakte ===
        'januar', 'februar', 'maerz', 'april', 'mai', 'juni', 'juli', 'august',
        'september', 'oktober', 'november', 'dezember',
        'montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag', 'samstag', 'sonntag'
    }

    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        self.bm25: Optional[BM25Okapi] = None
        self.doc_ids: List[str] = []
        self.documents: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self._index_path = CHROMA_DB_DIR / f"bm25_{kb_id}.pkl"

    def tokenize(self, text: str) -> List[str]:
        """Tokenisiert Text für BM25 (deutsch-optimiert)"""
        # Lowercase und Sonderzeichen entfernen
        text = text.lower()
        # Umlaute normalisieren für besseres Matching
        text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        # Nur alphanumerische Zeichen behalten
        tokens = re.findall(r'\b[a-z0-9]{2,}\b', text)
        # Stoppwörter entfernen
        tokens = [t for t in tokens if t not in self.GERMAN_STOPWORDS]
        return tokens

    def build_index(self, doc_ids: List[str], documents: List[str]):
        """Baut den BM25-Index auf"""
        self.doc_ids = doc_ids
        self.documents = documents
        self.tokenized_corpus = [self.tokenize(doc) for doc in documents]

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

        # Index persistieren
        self._save_index()

    def add_documents(self, doc_ids: List[str], documents: List[str]):
        """Fügt Dokumente zum Index hinzu und rebuildet"""
        self.doc_ids.extend(doc_ids)
        self.documents.extend(documents)
        new_tokens = [self.tokenize(doc) for doc in documents]
        self.tokenized_corpus.extend(new_tokens)

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

        self._save_index()

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, str]]:
        """
        BM25-Suche
        Returns: Liste von (doc_id, score, content)
        """
        if not self.bm25 or not self.doc_ids:
            return []

        tokenized_query = self.tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)

        # Top-K Ergebnisse mit Score > 0
        scored_docs = [(self.doc_ids[i], scores[i], self.documents[i])
                       for i in range(len(scores)) if scores[i] > 0]
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        return scored_docs[:top_k]

    def _save_index(self):
        """Speichert den Index auf Disk"""
        data = {
            'doc_ids': self.doc_ids,
            'documents': self.documents,
            'tokenized_corpus': self.tokenized_corpus
        }
        with open(self._index_path, 'wb') as f:
            pickle.dump(data, f)

    def load_index(self) -> bool:
        """Lädt den Index von Disk"""
        if not self._index_path.exists():
            return False

        try:
            with open(self._index_path, 'rb') as f:
                data = pickle.load(f)

            self.doc_ids = data['doc_ids']
            self.documents = data['documents']
            self.tokenized_corpus = data['tokenized_corpus']

            if self.tokenized_corpus:
                self.bm25 = BM25Okapi(self.tokenized_corpus)

            return True
        except Exception:
            return False

    def clear(self):
        """Löscht den Index"""
        self.bm25 = None
        self.doc_ids = []
        self.documents = []
        self.tokenized_corpus = []
        if self._index_path.exists():
            self._index_path.unlink()


@dataclass
class SearchResult:
    """Suchergebnis"""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class KnowledgeBase:
    """Wissensbank-Konfiguration"""
    id: str
    name: str
    description: str
    icon: str = "📄"
    created_at: datetime = field(default_factory=datetime.now)
    document_count: int = 0
    chunk_count: int = 0


class RAGEngine:
    """RAG-Engine mit ChromaDB und BM25 Hybrid Search"""

    def __init__(self):
        # ChromaDB Client initialisieren
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DB_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.collection_prefix = config.rag.collection_prefix
        # Differenzierte top_k Werte für lokale vs API-Modelle
        self.top_k_local = config.rag.top_k_local
        self.top_k_api = config.rag.top_k_api
        self.top_k = config.rag.top_k_results  # Legacy/Fallback
        self.similarity_threshold = config.rag.similarity_threshold

        # BM25-Indizes pro Wissensbank
        self._bm25_indices: Dict[str, BM25Index] = {}

        # RRF Parameter (k=60 ist Standard)
        self.rrf_k = 60

        # Standard-Wissensbasen erstellen falls nicht vorhanden
        self._ensure_default_knowledge_bases()

    def get_top_k(self) -> int:
        """
        Gibt das passende top_k basierend auf dem aktuellen LLM-Provider zurück.
        API-Modelle (OpenAI, Anthropic, Google) haben grosse Kontextfenster → mehr Chunks.
        """
        # Immer API top_k verwenden (kein lokales Ollama mehr)
        return self.top_k_api
    
    def _ensure_default_knowledge_bases(self):
        """Erstellt Standard-Wissensbasen"""
        existing = self.list_knowledge_bases()
        existing_ids = {kb.id for kb in existing}
        
        for kb_config in DEFAULT_KNOWLEDGE_BASES:
            if kb_config["id"] not in existing_ids:
                self.create_knowledge_base(
                    kb_id=kb_config["id"],
                    name=kb_config["name"],
                    description=kb_config["description"],
                    icon=kb_config.get("icon", "📄")
                )
    
    def _get_collection_name(self, kb_id: str, provider: str = None) -> str:
        """
        Generiert Collection-Namen.

        Args:
            kb_id: Wissensbank-ID
            provider: "local", "openai", oder None (für Metadata-Collection)

        Returns:
            Collection-Name mit optionalem Provider-Suffix
        """
        base_name = f"{self.collection_prefix}{kb_id}"
        if provider:
            return f"{base_name}_{provider}"
        return base_name  # Für Metadata-Abfragen (Legacy)

    def _get_or_create_collection(self, kb_id: str, provider: str = None):
        """Holt oder erstellt eine Collection für einen spezifischen Provider"""
        return self.client.get_or_create_collection(
            name=self._get_collection_name(kb_id, provider),
            metadata={"hnsw:space": "cosine"}
        )

    def _get_active_provider(self) -> str:
        """Gibt den aktuell für Suche konfigurierten Provider zurück"""
        return config.embedding.search_provider

    def get_embedding_status(self, kb_id: str) -> Dict[str, Any]:
        """
        Gibt Embedding-Status für eine Wissensbank zurück.

        Returns:
            Dict mit:
                - local_count: Anzahl Chunks mit lokalem Embedding
                - openai_count: Anzahl Chunks mit OpenAI Embedding
                - local_available: Ob lokale Embeddings vorhanden
                - openai_available: Ob OpenAI Embeddings vorhanden
        """
        local_count = 0
        openai_count = 0

        try:
            local_col = self._get_or_create_collection(kb_id, "local")
            local_count = max(0, local_col.count() - 1)  # -1 für Metadata
        except Exception:
            pass

        try:
            openai_col = self._get_or_create_collection(kb_id, "openai")
            openai_count = max(0, openai_col.count() - 1)  # -1 für Metadata
        except Exception:
            pass

        return {
            "local_count": local_count,
            "openai_count": openai_count,
            "local_available": local_count > 0,
            "openai_available": openai_count > 0
        }

    # ============ BM25 Index Verwaltung ============

    def _get_bm25_index(self, kb_id: str) -> BM25Index:
        """Holt oder erstellt BM25-Index für eine Wissensbank"""
        if kb_id not in self._bm25_indices:
            index = BM25Index(kb_id)
            # Versuche von Disk zu laden
            if not index.load_index():
                # Neu aufbauen aus ChromaDB
                self._rebuild_bm25_index(kb_id, index)
            self._bm25_indices[kb_id] = index
        return self._bm25_indices[kb_id]

    def _rebuild_bm25_index(self, kb_id: str, index: Optional[BM25Index] = None):
        """Baut BM25-Index aus ChromaDB-Daten neu auf"""
        if index is None:
            index = BM25Index(kb_id)

        collection = self._get_or_create_collection(kb_id)
        all_docs = collection.get(include=["documents", "metadatas"])

        doc_ids = []
        documents = []

        for i, doc_id in enumerate(all_docs["ids"]):
            # Metadata-Einträge überspringen
            if doc_id == "__kb_metadata__":
                continue
            meta = all_docs["metadatas"][i] if all_docs["metadatas"] else {}
            if meta.get("type") == "kb_metadata":
                continue

            doc_ids.append(doc_id)
            documents.append(all_docs["documents"][i])

        index.build_index(doc_ids, documents)
        self._bm25_indices[kb_id] = index

    def rebuild_all_bm25_indices(self):
        """Baut alle BM25-Indizes neu auf"""
        for kb in self.list_knowledge_bases():
            self._rebuild_bm25_index(kb.id)

    # ============ Wissensbank-Verwaltung ============
    
    def create_knowledge_base(
        self,
        kb_id: str,
        name: str,
        description: str,
        icon: str = "📄"
    ) -> KnowledgeBase:
        """Erstellt eine neue Wissensbank (beide Provider-Collections)"""
        metadata = {
            "type": "kb_metadata",
            "name": name,
            "description": description,
            "icon": icon,
            "created_at": datetime.now().isoformat()
        }

        # Metadata in beide Provider-Collections speichern
        for provider in ["local", "openai"]:
            collection = self._get_or_create_collection(kb_id, provider)

            # Dummy-Embedding mit richtiger Dimension pro Provider
            if provider == "local":
                dummy_embedding = [[0.0] * config.embedding.local_dimensions]
            else:
                dummy_embedding = [[0.0] * config.embedding.openai_dimensions]

            try:
                collection.add(
                    ids=["__kb_metadata__"],
                    documents=["Knowledge Base Metadata"],
                    metadatas=[metadata],
                    embeddings=dummy_embedding
                )
            except Exception:
                # Bereits vorhanden, aktualisieren
                collection.update(
                    ids=["__kb_metadata__"],
                    metadatas=[metadata]
                )

        return KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            icon=icon
        )
    
    def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """Listet alle Wissensbasen (dedupliziert nach KB-ID)"""
        collections = self.client.list_collections()
        kb_ids_seen = set()
        knowledge_bases = []

        for collection in collections:
            if collection.name.startswith(self.collection_prefix):
                # KB-ID extrahieren (entferne Prefix und Provider-Suffix)
                full_id = collection.name[len(self.collection_prefix):]

                # Provider-Suffix entfernen
                kb_id = full_id
                for suffix in ["_local", "_openai"]:
                    if full_id.endswith(suffix):
                        kb_id = full_id[:-len(suffix)]
                        break

                # Bereits verarbeitet?
                if kb_id in kb_ids_seen:
                    continue
                kb_ids_seen.add(kb_id)

                # Metadata aus einer der Collections abrufen
                name = kb_id
                description = ""
                icon = "📄"

                for provider in ["local", "openai"]:
                    try:
                        col = self._get_or_create_collection(kb_id, provider)
                        result = col.get(
                            ids=["__kb_metadata__"],
                            include=["metadatas"]
                        )
                        if result["metadatas"]:
                            meta = result["metadatas"][0]
                            name = meta.get("name", kb_id)
                            description = meta.get("description", "")
                            icon = meta.get("icon", "📄")
                            break
                    except Exception:
                        continue

                # Chunk-Anzahl aus lokaler Collection (primär)
                chunk_count = 0
                embedding_status = self.get_embedding_status(kb_id)
                chunk_count = max(embedding_status["local_count"], embedding_status["openai_count"])

                knowledge_bases.append(KnowledgeBase(
                    id=kb_id,
                    name=name,
                    description=description,
                    icon=icon,
                    chunk_count=chunk_count
                ))

        return knowledge_bases
    
    def delete_knowledge_base(self, kb_id: str) -> bool:
        """Löscht eine Wissensbank (alle Provider-Collections)"""
        deleted = False

        # Beide Provider-Collections löschen
        for provider in ["local", "openai"]:
            try:
                collection_name = self._get_collection_name(kb_id, provider)
                self.client.delete_collection(collection_name)
                deleted = True
            except Exception:
                pass

        # Legacy-Collection ohne Suffix (falls vorhanden)
        try:
            self.client.delete_collection(self._get_collection_name(kb_id, None))
        except Exception:
            pass

        # BM25-Index löschen
        if kb_id in self._bm25_indices:
            self._bm25_indices[kb_id].clear()
            del self._bm25_indices[kb_id]
        else:
            index = BM25Index(kb_id)
            index.clear()

        return deleted

    def delete_document(self, kb_id: str, doc_id: str) -> bool:
        """
        Löscht alle Chunks eines Dokuments aus der Wissensbank.

        Args:
            kb_id: Wissensbank-ID
            doc_id: Dokument-ID (Dateiname)

        Returns:
            True wenn mindestens ein Chunk gelöscht wurde
        """
        deleted = False

        # Aus beiden Provider-Collections löschen
        for provider in ["local", "openai"]:
            try:
                collection = self._get_or_create_collection(kb_id, provider)

                # Alle Chunks mit dieser source finden und löschen
                results = collection.get(
                    where={"source": doc_id},
                    include=["metadatas"]
                )

                if results["ids"]:
                    collection.delete(ids=results["ids"])
                    deleted = True
            except Exception as e:
                print(f"Fehler beim Löschen von {doc_id} aus {kb_id}/{provider}: {e}")

        # BM25-Index neu aufbauen (optional - kann auch lazy gemacht werden)
        if deleted and kb_id in self._bm25_indices:
            # Index wird beim nächsten Rebuild aktualisiert
            pass

        return deleted

    # ============ Dokument-Verwaltung ============

    def add_document(self, document: ProcessedDocument) -> Dict[str, bool]:
        """
        Fügt ein verarbeitetes Dokument zur Wissensbank hinzu.
        Erstellt Embeddings für alle konfigurierten Provider (local, openai, oder beide).

        Returns:
            Dict mit Erfolg pro Provider: {"local": True/False, "openai": True/False}
        """
        result = {"local": False, "openai": False}

        if not document.chunks:
            return result

        kb_id = document.metadata.get("knowledge_base", "default")
        texts = [chunk.content for chunk in document.chunks]
        chunk_ids = [chunk.id for chunk in document.chunks]
        metadatas = [chunk.metadata for chunk in document.chunks]

        # Dual-Embeddings erstellen
        dual_result = embedding_service.embed_dual(texts)

        # Lokale Embeddings speichern
        if dual_result.local_available:
            try:
                local_collection = self._get_or_create_collection(kb_id, "local")
                local_collection.add(
                    ids=chunk_ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=dual_result.local.embeddings
                )
                result["local"] = True
            except Exception as e:
                print(f"Fehler beim Speichern lokaler Embeddings: {e}")

        # OpenAI Embeddings speichern
        if dual_result.openai_available:
            try:
                openai_collection = self._get_or_create_collection(kb_id, "openai")
                openai_collection.add(
                    ids=chunk_ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=dual_result.openai.embeddings
                )
                result["openai"] = True
            except Exception as e:
                print(f"Fehler beim Speichern OpenAI Embeddings: {e}")

        # BM25-Index aktualisieren (unabhängig vom Embedding-Provider)
        if result["local"] or result["openai"]:
            bm25_index = self._get_bm25_index(kb_id)
            bm25_index.add_documents(chunk_ids, texts)

        return result
    
    def remove_document(self, doc_id: str, kb_id: str) -> bool:
        """Entfernt ein Dokument aus beiden Provider-Collections"""
        removed = False

        # Aus beiden Provider-Collections entfernen
        for provider in ["local", "openai"]:
            try:
                collection = self._get_or_create_collection(kb_id, provider)

                # Alle Chunks mit diesem Dokument-ID finden
                results = collection.get(
                    where={"$contains": doc_id},
                    include=["metadatas"]
                )

                if results["ids"]:
                    collection.delete(ids=results["ids"])
                    removed = True
            except Exception:
                pass

        # BM25-Index neu aufbauen
        if removed:
            self._rebuild_bm25_index(kb_id)

        return removed

    def clear_all_embeddings(self, kb_id: str) -> Dict[str, bool]:
        """
        Löscht alle Embeddings einer Wissensbank (für Re-Embedding).

        Returns:
            Dict mit Erfolg pro Provider
        """
        result = {"local": False, "openai": False}

        for provider in ["local", "openai"]:
            try:
                collection_name = self._get_collection_name(kb_id, provider)
                self.client.delete_collection(collection_name)
                result[provider] = True
            except Exception:
                pass

        # BM25-Index auch löschen
        if kb_id in self._bm25_indices:
            self._bm25_indices[kb_id].clear()
            del self._bm25_indices[kb_id]

        return result

    def list_documents(self, kb_id: str) -> List[Dict[str, Any]]:
        """
        Listet alle Dokumente in einer Wissensbank.
        Berücksichtigt beide Provider-Collections und zeigt Embedding-Status.
        """
        documents = {}

        # Aus beiden Collections zusammenführen
        for provider in ["local", "openai"]:
            try:
                collection = self._get_or_create_collection(kb_id, provider)
                results = collection.get(include=["metadatas"])

                for idx, meta in enumerate(results["metadatas"]):
                    if meta.get("type") == "kb_metadata":
                        continue

                    filename = meta.get("filename", "Unbekannt")
                    if filename not in documents:
                        documents[filename] = {
                            "id": filename,
                            "filename": filename,
                            "file_type": meta.get("file_type", ""),
                            "upload_date": meta.get("upload_date", ""),
                            "uploader": meta.get("uploader", ""),
                            "chunk_count": 0,
                            "has_local": False,
                            "has_openai": False
                        }

                    # Embedding-Status setzen
                    if provider == "local":
                        documents[filename]["has_local"] = True
                    else:
                        documents[filename]["has_openai"] = True

                    # Chunks nur einmal zählen (von einem Provider)
                    if provider == "local":
                        documents[filename]["chunk_count"] += 1

            except Exception:
                pass

        return list(documents.values())

    def document_exists(self, kb_id: str, filename: str) -> bool:
        """
        Prüft ob ein Dokument mit diesem Dateinamen bereits existiert.

        Args:
            kb_id: Wissensbank-ID
            filename: Dateiname des Dokuments

        Returns:
            True wenn Dokument existiert, sonst False
        """
        # In beiden Collections prüfen
        for provider in ["local", "openai"]:
            try:
                collection = self._get_or_create_collection(kb_id, provider)
                results = collection.get(include=["metadatas"])

                for meta in results["metadatas"]:
                    if meta.get("type") == "kb_metadata":
                        continue
                    if meta.get("filename") == filename:
                        return True
            except Exception:
                pass

        return False

    def get_document_hash(self, kb_id: str, filename: str) -> Optional[str]:
        """
        Gibt den Content-Hash eines Dokuments zurück.

        Args:
            kb_id: Wissensbank-ID
            filename: Dateiname des Dokuments

        Returns:
            Content-Hash oder None wenn nicht gefunden
        """
        for provider in ["local", "openai"]:
            try:
                collection = self._get_or_create_collection(kb_id, provider)
                results = collection.get(include=["metadatas"])

                for meta in results["metadatas"]:
                    if meta.get("type") == "kb_metadata":
                        continue
                    if meta.get("filename") == filename:
                        return meta.get("content_hash")
            except Exception:
                pass

        return None

    def needs_reembedding(self, kb_id: str, filename: str, new_content_hash: str) -> bool:
        """
        Prüft ob ein Dokument neu eingebettet werden muss.

        Args:
            kb_id: Wissensbank-ID
            filename: Dateiname des Dokuments
            new_content_hash: Hash des neuen Inhalts

        Returns:
            True wenn Re-Embedding nötig (Inhalt geändert oder neu), sonst False
        """
        existing_hash = self.get_document_hash(kb_id, filename)

        if existing_hash is None:
            return True  # Neues Dokument

        return existing_hash != new_content_hash  # Inhalt geändert?

    def get_document_chunks(self, kb_id: str, doc_id: str, provider: str = None) -> List[Dict[str, Any]]:
        """
        Gibt alle Chunks eines Dokuments zurück.

        Args:
            kb_id: Wissensbank-ID
            doc_id: Dokument-ID (Dateiname)
            provider: "local", "openai", oder None (verwendet search_provider)
        """
        if provider is None:
            provider = self._get_active_provider()

        try:
            collection = self._get_or_create_collection(kb_id, provider)
            results = collection.get(include=["metadatas", "documents"])

            chunks = []
            for idx, meta in enumerate(results["metadatas"]):
                if meta.get("type") == "kb_metadata":
                    continue

                if meta.get("filename") == doc_id:
                    chunks.append({
                        "id": results["ids"][idx] if results["ids"] else None,
                        "content": results["documents"][idx] if results["documents"] else "",
                        "chunk_index": meta.get("chunk_index", idx),
                        "metadata": meta
                    })

            chunks.sort(key=lambda x: x.get("chunk_index", 0))
            return chunks
        except Exception:
            return []
    
    # ============ Suche ============
    
    def search(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Semantische Suche über Wissensbasen.

        Args:
            query: Suchanfrage
            kb_ids: Liste der Wissensbank-IDs (None = alle)
            top_k: Anzahl Ergebnisse
            filters: ChromaDB Filter
            provider: Embedding-Provider ("local", "openai", oder None für config-Default)

        Returns:
            Liste von SearchResult
        """
        if top_k is None:
            top_k = self.get_top_k()

        # Provider bestimmen
        if provider is None:
            provider = self._get_active_provider()

        # Query-Embedding mit dem richtigen Provider erstellen
        query_embedding = embedding_service.embed_text(query, provider=provider)

        if query_embedding is None:
            print(f"Warnung: Konnte Query-Embedding nicht erstellen mit Provider '{provider}'")
            return []

        all_results = []

        # Über alle relevanten Wissensbasen suchen
        if kb_ids is None:
            kb_ids = [kb.id for kb in self.list_knowledge_bases()]

        # Validierung: Stelle sicher, dass kb_ids Strings sind (nicht SearchResult-Objekte)
        if kb_ids and not all(isinstance(kb, str) for kb in kb_ids):
            print("Warnung: kb_ids enthält ungültige Typen (erwartet: List[str])")
            kb_ids = [kb if isinstance(kb, str) else getattr(kb, 'metadata', {}).get('knowledge_base', str(kb)[:50])
                      for kb in kb_ids]
            kb_ids = [kb for kb in kb_ids if kb and isinstance(kb, str)]

        for kb_id in kb_ids:
            try:
                # Collection für den spezifischen Provider verwenden
                collection = self._get_or_create_collection(kb_id, provider)

                # Suche durchführen
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k + 1,  # +1 falls metadata-Eintrag dabei ist
                    where=filters if filters else None,
                    include=["documents", "metadatas", "distances"]
                )

                # Ergebnisse verarbeiten
                if results["ids"] and results["ids"][0]:
                    for i, chunk_id in enumerate(results["ids"][0]):
                        # Metadata-Einträge überspringen
                        if chunk_id == "__kb_metadata__":
                            continue
                        if results["metadatas"][0][i].get("type") == "kb_metadata":
                            continue

                        # ChromaDB gibt Distanz zurück, wir wollen Ähnlichkeit
                        distance = results["distances"][0][i]
                        score = 1 - distance  # Cosine distance to similarity

                        if score >= self.similarity_threshold:
                            all_results.append(SearchResult(
                                chunk_id=chunk_id,
                                content=results["documents"][0][i],
                                score=score,
                                metadata=results["metadatas"][0][i]
                            ))
            except Exception as e:
                print(f"Fehler bei Suche in {kb_id} (provider={provider}): {e}")
                continue
        
        # Nach Score sortieren und Top-K zurückgeben
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]
    
    def fulltext_search(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Einfache Volltextsuche (für Debugging/Fallback)"""
        results = []

        if kb_ids is None:
            kb_ids = [kb.id for kb in self.list_knowledge_bases()]

        query_lower = query.lower()

        for kb_id in kb_ids:
            try:
                collection = self._get_or_create_collection(kb_id)
                all_docs = collection.get(include=["documents", "metadatas"])

                for i, doc in enumerate(all_docs["documents"]):
                    if query_lower in doc.lower():
                        results.append(SearchResult(
                            chunk_id=all_docs["ids"][i],
                            content=doc,
                            score=1.0,  # Exakter Match
                            metadata=all_docs["metadatas"][i]
                        ))
            except Exception:
                continue

        return results

    def bm25_search(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """BM25 Keyword-Suche über Wissensbasen"""
        if top_k is None:
            top_k = self.get_top_k()

        all_results = []

        if kb_ids is None:
            kb_ids = [kb.id for kb in self.list_knowledge_bases()]

        for kb_id in kb_ids:
            try:
                bm25_index = self._get_bm25_index(kb_id)
                bm25_results = bm25_index.search(query, top_k=top_k * 2)

                # Metadata aus ChromaDB holen
                collection = self._get_or_create_collection(kb_id)

                for doc_id, score, content in bm25_results:
                    try:
                        meta_result = collection.get(ids=[doc_id], include=["metadatas"])
                        metadata = meta_result["metadatas"][0] if meta_result["metadatas"] else {}
                    except Exception:
                        metadata = {}

                    all_results.append(SearchResult(
                        chunk_id=doc_id,
                        content=content,
                        score=score,
                        metadata=metadata
                    ))
            except Exception as e:
                print(f"Fehler bei BM25-Suche in {kb_id}: {e}")
                continue

        # Nach Score sortieren und Top-K zurückgeben
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]

    def hybrid_search(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        enable_query_expansion: bool = True,
        enable_rerank: bool = True
    ) -> List[SearchResult]:
        """
        Hybrid Search: Kombiniert Vektor-Suche und BM25 mit Reciprocal Rank Fusion (RRF)

        Erweitert mit:
        - Query Expansion: Automatische Erweiterung mit Fachbegriffen (für Bundesrecht)
        - Re-Ranking: Nachträgliche Bewertung nach Relevanzkriterien

        Args:
            query: Suchanfrage
            kb_ids: Liste der Wissensbank-IDs (None = alle)
            top_k: Anzahl der Ergebnisse
            vector_weight: Gewichtung der Vektor-Suche (0-1)
            bm25_weight: Gewichtung der BM25-Suche (0-1)
            enable_query_expansion: Query Expansion aktivieren
            enable_rerank: Re-Ranking aktivieren

        Returns:
            Liste von SearchResult mit kombinierten Scores
        """
        if top_k is None:
            top_k = self.get_top_k()

        # Query Expansion (nur für bestimmte Wissensbasen wie Bundesrecht)
        search_query = query
        if enable_query_expansion and kb_ids:
            try:
                from app.core.query_enhancement import expand_query
                search_query = expand_query(query, kb_ids)
            except ImportError:
                pass  # Fallback ohne Expansion

        # Mehr Kandidaten holen für bessere Fusion
        candidates_k = top_k * 3

        # Vektor-Suche (mit erweiterter Query)
        vector_results = self.search(search_query, kb_ids, top_k=candidates_k)

        # BM25-Suche (mit erweiterter Query)
        bm25_results = self.bm25_search(search_query, kb_ids, top_k=candidates_k)

        # Reciprocal Rank Fusion (RRF)
        # Score = sum(weight / (k + rank)) für jede Suchmethode
        rrf_scores: Dict[str, float] = {}
        result_data: Dict[str, SearchResult] = {}

        # Vektor-Ergebnisse verarbeiten
        for rank, result in enumerate(vector_results):
            rrf_score = vector_weight / (self.rrf_k + rank + 1)
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0) + rrf_score
            result_data[result.chunk_id] = result

        # BM25-Ergebnisse verarbeiten
        for rank, result in enumerate(bm25_results):
            rrf_score = bm25_weight / (self.rrf_k + rank + 1)
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0) + rrf_score
            if result.chunk_id not in result_data:
                result_data[result.chunk_id] = result

        # Ergebnisse nach RRF-Score sortieren
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Top-K Ergebnisse mit normalisierten Scores zurückgeben
        final_results = []
        max_score = max(rrf_scores.values()) if rrf_scores else 1.0

        for chunk_id in sorted_ids[:top_k]:
            result = result_data[chunk_id]
            normalized_score = rrf_scores[chunk_id] / max_score
            final_results.append(SearchResult(
                chunk_id=result.chunk_id,
                content=result.content,
                score=normalized_score,
                metadata=result.metadata
            ))

        # Re-Ranking: Ergebnisse nach zusätzlichen Kriterien neu bewerten
        if enable_rerank and final_results:
            try:
                from app.core.query_enhancement import rerank_results
                # Prüfe ob es sich um juristische Inhalte handelt
                boost_legal = kb_ids and any(
                    kb in ["bundesrecht", "gemeindewissen"]
                    for kb in kb_ids
                )
                final_results = rerank_results(final_results, query, boost_legal=boost_legal)
            except ImportError:
                pass  # Fallback ohne Re-Ranking

        return final_results

    # ============ RAG-Generierung ============
    
    def generate_answer(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        additional_context: Optional[str] = None
    ):
        """Generiert eine Antwort basierend auf RAG"""
        # Relevante Dokumente suchen
        search_results = self.search(query, kb_ids)

        # Kontext aufbauen
        context_parts = []
        sources = []

        for result in search_results:
            context_parts.append(result.content)
            source = result.metadata.get("source") or result.metadata.get("filename", "Unbekannt")
            if source not in sources:
                sources.append(source)

        context = "\n\n---\n\n".join(context_parts)

        # CBR-Kontext hinzufügen (wenn vorhanden)
        if additional_context:
            context = f"{context}\n\n{additional_context}"

        # System-Prompt
        if system_prompt is None:
            # Prüfe ob Bundesrecht involviert ist für speziellen Prompt
            is_legal_context = kb_ids and any(kb in ["bundesrecht", "gemeindewissen"] for kb in kb_ids)

            if is_legal_context:
                system_prompt = """Du bist ein Rechtsauskunfts-Assistent für Schweizer Bundesrecht.
Du beantwortest Fragen basierend auf dem bereitgestellten Kontext aus Bundesgesetzen und Verordnungen.

WICHTIGE REGELN FÜR QUELLENANGABEN:
1. Zitiere IMMER die genaue Gesetzesquelle mit Artikel und Absatz (z.B. "Art. 1 Abs. 1 OR", "Art. 319 OR").
2. Nenne bei jeder relevanten Aussage die zugehörige SR-Nummer und Gesetzesbezeichnung.
3. Strukturiere deine Antwort: Zuerst die rechtliche Grundlage, dann die Erklärung.
4. Wenn mehrere Artikel relevant sind, liste alle auf.
5. Bei Unsicherheit oder fehlender Information im Kontext, sage dies ehrlich.

FORMAT-BEISPIEL:
"Gemäss Art. 1 Abs. 1 OR entsteht ein Vertrag durch übereinstimmende Willensäusserung der Parteien.
Dies bedeutet, dass..."

Antworte auf Deutsch. Sei präzise und fachlich korrekt."""
            else:
                system_prompt = """Du bist der KMU Knowledge Assistant, ein hilfreicher Assistent für Muster KMU.
Du beantwortest Fragen basierend auf dem bereitgestellten Kontext aus der Wissensdatenbank.

Wichtige Regeln:
1. Antworte nur basierend auf dem Kontext. Wenn die Information nicht im Kontext ist, sage es ehrlich.
2. Antworte auf Deutsch.
3. Sei präzise und hilfreich.
4. Zitiere IMMER die Quelle deiner Information (Dokumentname, Abschnitt oder Seite).
5. Wenn ähnliche erfolgreiche Antworten verfügbar sind, orientiere dich an deren Stil und Struktur."""

        # Prompt zusammenbauen
        full_prompt = f"""Kontext aus der Wissensdatenbank:

{context}

---

Frage: {query}

Bitte beantworte die Frage basierend auf dem obigen Kontext."""
        
        if stream:
            return llm_provider.stream(full_prompt, system_prompt), sources
        else:
            response = llm_provider.generate(full_prompt, system_prompt)
            return response, sources
    
    # ============ Wartung ============
    
    def reindex_knowledge_base(self, kb_id: str) -> int:
        """Reindexiert eine Wissensbank (erneuert Embeddings)"""
        collection = self._get_or_create_collection(kb_id)
        
        # Alle Dokumente abrufen
        all_docs = collection.get(include=["documents", "metadatas"])
        
        if not all_docs["ids"]:
            return 0
        
        # Metadata-Eintrag ausschließen
        valid_indices = [
            i for i, meta in enumerate(all_docs["metadatas"])
            if meta.get("type") != "kb_metadata"
        ]
        
        if not valid_indices:
            return 0
        
        # Neue Embeddings erstellen
        texts = [all_docs["documents"][i] for i in valid_indices]
        embedding_result = embedding_provider.embed_texts(texts)
        
        # Aktualisieren
        for idx, valid_idx in enumerate(valid_indices):
            collection.update(
                ids=[all_docs["ids"][valid_idx]],
                embeddings=[embedding_result.embeddings[idx]]
            )
        
        return len(valid_indices)
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken über alle Wissensbasen zurück"""
        knowledge_bases = self.list_knowledge_bases()
        
        total_chunks = sum(kb.chunk_count for kb in knowledge_bases)
        
        return {
            "knowledge_base_count": len(knowledge_bases),
            "total_chunks": total_chunks,
            "knowledge_bases": [
                {
                    "id": kb.id,
                    "name": kb.name,
                    "chunk_count": kb.chunk_count
                }
                for kb in knowledge_bases
            ]
        }


# Globale Instanz
rag_engine = RAGEngine()
