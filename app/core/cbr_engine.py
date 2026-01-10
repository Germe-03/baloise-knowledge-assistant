"""
KMU Knowledge Assistant - Case-Based Reasoning Engine
Lernt aus User-Feedback um Antworten zu verbessern
Mit ML-basiertem Clustering für Kategorisierung
"""

import uuid
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter

from app.config import CHROMA_DB_DIR, config

# ML für Clustering
try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class Case:
    """Ein Case (Frage-Antwort-Paar mit Feedback)"""
    id: str
    question: str
    answer: str
    feedback: str  # "positive", "negative", "neutral"
    feedback_score: float  # -1.0 bis 1.0
    context_used: List[str]  # Welche Dokumente wurden verwendet
    knowledge_bases: List[str]
    model_used: str
    user_id: str
    created_at: str
    feedback_comment: Optional[str] = None
    times_reused: int = 0  # Wie oft wurde dieser Case wiederverwendet
    cluster_id: int = -1  # Cluster/Kategorie ID (-1 = nicht klassifiziert)
    cluster_label: str = ""  # Automatisch generiertes Label


# Vordefinierte Kategorien für HR/Personalvermittlung
PREDEFINED_CATEGORIES = {
    "lohn": ["lohn", "gehalt", "salär", "zahlung", "überweisung", "abrechnung", "spesen"],
    "vertrag": ["vertrag", "kündigung", "anstellung", "pensum", "arbeitszeit", "befristung"],
    "personal": ["mitarbeiter", "kandidat", "bewerber", "referenz", "zeugnis", "profil"],
    "kunde": ["kunde", "klient", "auftrag", "beschwerde", "reklamation", "feedback"],
    "einsatzplanung": ["einsatz", "planung", "springer", "temporär", "datum", "buchung"],
    "dokumente": ["vorlage", "dokument", "formular", "pdf", "word", "template"],
    "prozess": ["ablauf", "prozess", "anleitung", "workflow", "schritt"]
}


class CBREngine:
    """Case-Based Reasoning Engine für kontinuierliches Lernen"""

    def __init__(self, chroma_client=None):
        # Verwende existierenden Client oder erstelle neuen via lazy loading
        self._client = chroma_client
        self.collection_name = "sp_cbr_cases"
        self.collection = None  # Lazy loading

    @property
    def client(self):
        """Lazy loading des ChromaDB Clients"""
        if self._client is None:
            # Client von RAG Engine verwenden
            from app.core.rag_engine import rag_engine
            self._client = rag_engine.client
        return self._client

    def _ensure_collection(self):
        """Stellt sicher dass die CBR Collection existiert (lazy)"""
        if self.collection is not None:
            return

        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "CBR Cases für Feedback-basiertes Lernen"}
            )
        except Exception as e:
            print(f"CBR Collection Fehler: {e}")
            self.collection = None

    def store_case(
        self,
        question: str,
        answer: str,
        feedback: str,
        context_used: List[str] = None,
        knowledge_bases: List[str] = None,
        model_used: str = "",
        user_id: str = "",
        feedback_comment: str = None
    ) -> Optional[Case]:
        """Speichert einen neuen Case"""
        self._ensure_collection()
        if not self.collection:
            return None

        # Feedback Score berechnen
        feedback_scores = {
            "positive": 1.0,
            "very_positive": 1.0,
            "neutral": 0.0,
            "negative": -0.5,
            "very_negative": -1.0,
            "corrected": 0.2  # Korrigierte Cases haben niedrigeren Score als positiv
        }
        feedback_score = feedback_scores.get(feedback, 0.0)

        # Automatische Kategorisierung
        category, confidence = self.classify_question(question)

        case = Case(
            id=str(uuid.uuid4()),
            question=question,
            answer=answer,
            feedback=feedback,
            feedback_score=feedback_score,
            context_used=context_used or [],
            knowledge_bases=knowledge_bases or [],
            model_used=model_used,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            feedback_comment=feedback_comment,
            times_reused=0,
            cluster_id=-1,
            cluster_label=category
        )

        try:
            # In ChromaDB speichern
            self.collection.add(
                ids=[case.id],
                documents=[f"{question}\n\n{answer}"],
                metadatas=[{
                    "question": question[:1000],  # Limit für Metadata
                    "answer": answer[:2000],
                    "feedback": feedback,
                    "feedback_score": feedback_score,
                    "knowledge_bases": json.dumps(knowledge_bases or []),
                    "model_used": model_used,
                    "user_id": user_id,
                    "created_at": case.created_at,
                    "times_reused": 0,
                    "cluster_label": category,
                    "cluster_confidence": confidence
                }]
            )
            return case
        except Exception as e:
            print(f"Case speichern Fehler: {e}")
            return None

    def retrieve_similar_cases(
        self,
        question: str,
        top_k: int = 3,
        min_feedback_score: float = 0.5,
        knowledge_bases: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Findet ähnliche Cases mit positivem Feedback"""
        self._ensure_collection()
        if not self.collection:
            return []

        try:
            # Suche in ChromaDB
            results = self.collection.query(
                query_texts=[question],
                n_results=top_k * 2,  # Mehr holen, dann filtern
                include=["documents", "metadatas", "distances"]
            )

            if not results["ids"][0]:
                return []

            cases = []
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if results["distances"] else 1.0

                # Nur positive Cases
                if metadata.get("feedback_score", 0) < min_feedback_score:
                    continue

                # Knowledge Base Filter
                if knowledge_bases:
                    case_kbs = json.loads(metadata.get("knowledge_bases", "[]"))
                    if not any(kb in case_kbs for kb in knowledge_bases):
                        continue

                similarity = 1.0 - (distance / 2.0)  # Normalisieren

                cases.append({
                    "id": doc_id,
                    "question": metadata.get("question", ""),
                    "answer": metadata.get("answer", ""),
                    "feedback": metadata.get("feedback", ""),
                    "feedback_score": metadata.get("feedback_score", 0),
                    "similarity": similarity,
                    "times_reused": metadata.get("times_reused", 0)
                })

            # Nach Relevanz sortieren (Kombination aus Similarity und Feedback)
            cases.sort(key=lambda x: x["similarity"] * (1 + x["feedback_score"]), reverse=True)

            return cases[:top_k]

        except Exception as e:
            print(f"Case Retrieval Fehler: {e}")
            return []

    def increment_reuse_count(self, case_id: str):
        """Erhöht den Reuse-Counter eines Cases"""
        self._ensure_collection()
        if not self.collection:
            return

        try:
            result = self.collection.get(ids=[case_id], include=["metadatas"])
            if result["metadatas"]:
                metadata = result["metadatas"][0]
                metadata["times_reused"] = metadata.get("times_reused", 0) + 1
                self.collection.update(ids=[case_id], metadatas=[metadata])
        except Exception:
            pass

    def update_feedback(self, case_id: str, new_feedback: str, comment: str = None):
        """Aktualisiert das Feedback eines Cases"""
        self._ensure_collection()
        if not self.collection:
            return False

        feedback_scores = {
            "positive": 1.0,
            "very_positive": 1.0,
            "neutral": 0.0,
            "negative": -0.5,
            "very_negative": -1.0,
            "corrected": 0.2
        }

        try:
            result = self.collection.get(ids=[case_id], include=["metadatas"])
            if result["metadatas"]:
                metadata = result["metadatas"][0]
                metadata["feedback"] = new_feedback
                metadata["feedback_score"] = feedback_scores.get(new_feedback, 0.0)
                if comment:
                    metadata["feedback_comment"] = comment[:500]
                self.collection.update(ids=[case_id], metadatas=[metadata])
                return True
        except Exception as e:
            print(f"Feedback Update Fehler: {e}")
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Gibt CBR Statistiken zurück"""
        self._ensure_collection()
        if not self.collection:
            return {}

        try:
            count = self.collection.count()

            # Alle Cases holen für Statistiken
            if count == 0:
                return {
                    "total_cases": 0,
                    "positive_cases": 0,
                    "negative_cases": 0,
                    "neutral_cases": 0,
                    "avg_feedback_score": 0,
                    "total_reuses": 0
                }

            all_data = self.collection.get(include=["metadatas"])
            metadatas = all_data["metadatas"]

            positive = sum(1 for m in metadatas if m.get("feedback_score", 0) > 0)
            negative = sum(1 for m in metadatas if m.get("feedback_score", 0) < 0)
            corrected = sum(1 for m in metadatas if m.get("feedback") == "corrected")
            neutral = count - positive - negative

            total_score = sum(m.get("feedback_score", 0) for m in metadatas)
            avg_score = total_score / count if count > 0 else 0

            total_reuses = sum(m.get("times_reused", 0) for m in metadatas)

            # Top wiederverwendete Cases
            reuse_data = [(m.get("question", "")[:50], m.get("times_reused", 0))
                         for m in metadatas if m.get("times_reused", 0) > 0]
            reuse_data.sort(key=lambda x: x[1], reverse=True)

            return {
                "total_cases": count,
                "positive_cases": positive,
                "negative_cases": negative,
                "corrected_cases": corrected,
                "neutral_cases": neutral,
                "positive_rate": positive / count if count > 0 else 0,
                "avg_feedback_score": avg_score,
                "total_reuses": total_reuses,
                "top_reused": reuse_data[:5]
            }

        except Exception as e:
            print(f"Statistik Fehler: {e}")
            return {}

    def get_all_cases(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Holt alle Cases für Admin-Ansicht"""
        self._ensure_collection()
        if not self.collection:
            return []

        try:
            result = self.collection.get(
                include=["metadatas"],
                limit=limit
            )

            cases = []
            for i, doc_id in enumerate(result["ids"]):
                metadata = result["metadatas"][i]
                cases.append({
                    "id": doc_id,
                    **metadata
                })

            # Nach Datum sortieren
            cases.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return cases

        except Exception:
            return []

    def delete_case(self, case_id: str) -> bool:
        """Löscht einen Case"""
        self._ensure_collection()
        if not self.collection:
            return False

        try:
            self.collection.delete(ids=[case_id])
            return True
        except Exception:
            return False

    def build_context_from_cases(self, cases: List[Dict[str, Any]]) -> str:
        """Baut Kontext-String aus ähnlichen Cases"""
        if not cases:
            return ""

        context_parts = ["### Ähnliche erfolgreiche Antworten aus der Vergangenheit:\n"]

        for i, case in enumerate(cases[:3], 1):
            context_parts.append(f"""
**Beispiel {i}** (Feedback: {case['feedback']}, Ähnlichkeit: {case['similarity']:.0%})
Frage: {case['question'][:200]}...
Erfolgreiche Antwort: {case['answer'][:500]}...
""")

        context_parts.append("\nNutze diese Beispiele als Orientierung für Stil und Struktur deiner Antwort.\n")

        return "\n".join(context_parts)

    # ==================== CLUSTERING / KATEGORISIERUNG ====================

    def classify_question(self, question: str) -> Tuple[str, float]:
        """
        Klassifiziert eine Frage in eine vordefinierte Kategorie.
        Verwendet Keyword-Matching mit Scoring.

        Returns:
            Tuple[category_name, confidence_score]
        """
        question_lower = question.lower()
        scores = {}

        for category, keywords in PREDEFINED_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in question_lower)
            if score > 0:
                scores[category] = score

        if not scores:
            return ("sonstiges", 0.0)

        best_category = max(scores.items(), key=lambda x: x[1])
        # Confidence basierend auf Anzahl der Treffer (max 1.0)
        confidence = min(best_category[1] / 3.0, 1.0)

        return (best_category[0], confidence)

    def auto_classify_cases(self) -> Dict[str, int]:
        """
        Klassifiziert alle Cases automatisch und aktualisiert ihre Cluster-Labels.
        Verwendet Hybrid-Ansatz: Keyword-Matching + optional K-Means.

        Returns:
            Dict mit Kategorie -> Anzahl
        """
        self._ensure_collection()
        if not self.collection:
            return {}

        try:
            all_data = self.collection.get(include=["metadatas"])
            if not all_data["ids"]:
                return {}

            category_counts = Counter()

            for i, doc_id in enumerate(all_data["ids"]):
                metadata = all_data["metadatas"][i]
                question = metadata.get("question", "")

                # Klassifiziere
                category, confidence = self.classify_question(question)
                category_counts[category] += 1

                # Update metadata mit Cluster-Info
                metadata["cluster_label"] = category
                metadata["cluster_confidence"] = confidence

                self.collection.update(ids=[doc_id], metadatas=[metadata])

            return dict(category_counts)

        except Exception as e:
            print(f"Auto-Classify Fehler: {e}")
            return {}

    def cluster_with_kmeans(self, n_clusters: int = 5) -> Dict[str, Any]:
        """
        Führt K-Means Clustering auf allen Cases durch.
        Verwendet TF-IDF Vektorisierung der Fragen.

        Args:
            n_clusters: Anzahl der Cluster

        Returns:
            Dict mit Cluster-Informationen
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "sklearn nicht installiert"}

        self._ensure_collection()
        if not self.collection:
            return {"error": "Keine Collection"}

        try:
            all_data = self.collection.get(include=["metadatas"])
            if not all_data["ids"] or len(all_data["ids"]) < n_clusters:
                return {"error": "Nicht genug Daten für Clustering"}

            # Fragen extrahieren
            questions = [m.get("question", "") for m in all_data["metadatas"]]
            doc_ids = all_data["ids"]

            # TF-IDF Vektorisierung
            vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words=None,  # Deutsch hat andere Stop-Words
                ngram_range=(1, 2)
            )
            tfidf_matrix = vectorizer.fit_transform(questions)

            # K-Means Clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(tfidf_matrix)

            # Cluster-Labels generieren (häufigste Wörter pro Cluster)
            feature_names = vectorizer.get_feature_names_out()
            cluster_labels = {}

            for cluster_id in range(n_clusters):
                # Dokumente in diesem Cluster
                cluster_indices = np.where(clusters == cluster_id)[0]
                if len(cluster_indices) == 0:
                    cluster_labels[cluster_id] = f"Cluster {cluster_id}"
                    continue

                # Durchschnittlicher TF-IDF Vektor
                cluster_center = kmeans.cluster_centers_[cluster_id]
                top_indices = cluster_center.argsort()[-3:][::-1]
                top_words = [feature_names[i] for i in top_indices]
                cluster_labels[cluster_id] = " / ".join(top_words)

            # Metadata aktualisieren
            cluster_counts = Counter()
            for i, doc_id in enumerate(doc_ids):
                cluster_id = int(clusters[i])
                cluster_label = cluster_labels[cluster_id]
                cluster_counts[cluster_label] += 1

                metadata = all_data["metadatas"][i]
                metadata["kmeans_cluster"] = cluster_id
                metadata["kmeans_label"] = cluster_label

                self.collection.update(ids=[doc_id], metadatas=[metadata])

            return {
                "n_clusters": n_clusters,
                "cluster_labels": cluster_labels,
                "cluster_counts": dict(cluster_counts),
                "total_classified": len(doc_ids)
            }

        except Exception as e:
            print(f"K-Means Fehler: {e}")
            return {"error": str(e)}

    def get_cases_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Holt alle Cases einer bestimmten Kategorie"""
        self._ensure_collection()
        if not self.collection:
            return []

        try:
            result = self.collection.get(include=["metadatas"], limit=500)

            cases = []
            for i, doc_id in enumerate(result["ids"]):
                metadata = result["metadatas"][i]
                case_category = metadata.get("cluster_label", "sonstiges")

                if case_category.lower() == category.lower():
                    cases.append({
                        "id": doc_id,
                        **metadata
                    })

            cases.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return cases[:limit]

        except Exception:
            return []

    def get_category_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken pro Kategorie zurück"""
        self._ensure_collection()
        if not self.collection:
            return {}

        try:
            all_data = self.collection.get(include=["metadatas"])
            if not all_data["metadatas"]:
                return {}

            category_stats = {}

            for metadata in all_data["metadatas"]:
                category = metadata.get("cluster_label", "sonstiges")
                feedback_score = metadata.get("feedback_score", 0)

                if category not in category_stats:
                    category_stats[category] = {
                        "total": 0,
                        "positive": 0,
                        "negative": 0,
                        "avg_score": 0,
                        "scores": []
                    }

                category_stats[category]["total"] += 1
                category_stats[category]["scores"].append(feedback_score)

                if feedback_score > 0:
                    category_stats[category]["positive"] += 1
                elif feedback_score < 0:
                    category_stats[category]["negative"] += 1

            # Durchschnitt berechnen
            for cat, stats in category_stats.items():
                if stats["scores"]:
                    stats["avg_score"] = sum(stats["scores"]) / len(stats["scores"])
                del stats["scores"]  # Nicht in Ausgabe

            return category_stats

        except Exception as e:
            print(f"Category Stats Fehler: {e}")
            return {}


# Singleton Instanz
cbr_engine = CBREngine()
