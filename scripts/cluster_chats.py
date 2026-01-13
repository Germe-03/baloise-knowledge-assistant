"""
Cluster user chat messages from data/chat_history.

Run: python scripts/cluster_chats.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer


BASE_DIR = Path(__file__).resolve().parents[1]
CHAT_HISTORY_DIR = BASE_DIR / "data" / "chat_history"
OUTPUT_DIR = BASE_DIR / "data" / "chat_clusters"
OUTPUT_FILE = OUTPUT_DIR / "clusters.json"


@dataclass
class UserMessage:
    content: str
    conversation_id: str
    timestamp: str


def load_user_messages() -> List[UserMessage]:
    messages: List[UserMessage] = []
    if not CHAT_HISTORY_DIR.exists():
        return messages

    for user_dir in CHAT_HISTORY_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        for file_path in user_dir.glob("*.json"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            conv_id = data.get("id", file_path.stem)
            for msg in data.get("messages", []):
                if msg.get("role") != "user":
                    continue
                content = (msg.get("content") or "").strip()
                if not content:
                    continue
                messages.append(
                    UserMessage(
                        content=content,
                        conversation_id=conv_id,
                        timestamp=msg.get("timestamp", "")
                    )
                )
    return messages


def build_clusters(
    texts: List[str],
    distance_threshold: float,
    max_features: int
) -> Dict[str, Any]:
    if not texts:
        return {"labels": [], "vectorizer": None, "matrix": None}

    vectorizer = TfidfVectorizer(
        lowercase=True,
        max_df=0.9,
        min_df=1,
        ngram_range=(1, 2),
        max_features=max_features
    )
    matrix = vectorizer.fit_transform(texts)

    if matrix.shape[0] < 2 or matrix.shape[1] == 0:
        labels = list(range(matrix.shape[0]))
        return {"labels": labels, "vectorizer": vectorizer, "matrix": matrix}

    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average"
    )
    labels = model.fit_predict(matrix.toarray()).tolist()
    return {"labels": labels, "vectorizer": vectorizer, "matrix": matrix}


def top_terms_for_cluster(
    feature_names: List[str],
    cluster_vectors: np.ndarray,
    top_n: int
) -> List[str]:
    if cluster_vectors.size == 0:
        return []
    centroid = cluster_vectors.mean(axis=0)
    if centroid.ndim != 1:
        centroid = centroid.ravel()
    top_idx = np.argsort(centroid)[::-1]
    terms: List[str] = []
    for idx in top_idx:
        if centroid[idx] <= 0:
            break
        terms.append(feature_names[idx])
        if len(terms) >= top_n:
            break
    return terms


def example_sentences(
    texts: List[str],
    cluster_vectors: np.ndarray,
    centroid: np.ndarray,
    count: int
) -> List[str]:
    if cluster_vectors.size == 0:
        return []
    scores = cluster_vectors @ centroid
    top_idx = np.argsort(scores)[::-1][:count]
    return [texts[i] for i in top_idx]


def write_output(payload: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for file_path in OUTPUT_DIR.glob("*.json"):
        try:
            file_path.unlink()
        except Exception:
            continue
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster user chat messages.")
    parser.add_argument("--distance-threshold", type=float, default=0.7)
    parser.add_argument("--max-features", type=int, default=5000)
    parser.add_argument("--examples", type=int, default=4)
    parser.add_argument("--top-terms", type=int, default=6)
    args = parser.parse_args()

    messages = load_user_messages()
    texts = [m.content for m in messages]

    cluster_data = build_clusters(
        texts=texts,
        distance_threshold=args.distance_threshold,
        max_features=args.max_features
    )

    labels = cluster_data["labels"]
    vectorizer = cluster_data["vectorizer"]
    matrix = cluster_data["matrix"]

    clusters: List[Dict[str, Any]] = []

    if labels:
        feature_names = vectorizer.get_feature_names_out().tolist() if vectorizer else []
        dense_matrix = matrix.toarray() if matrix is not None else np.array([])
        label_set = sorted(set(labels))

        for label in label_set:
            idx = [i for i, l in enumerate(labels) if l == label]
            cluster_texts = [texts[i] for i in idx]
            cluster_vectors = dense_matrix[idx] if dense_matrix.size else np.array([])

            if cluster_vectors.size:
                centroid = cluster_vectors.mean(axis=0)
                samples = example_sentences(cluster_texts, cluster_vectors, centroid, args.examples)
                terms = top_terms_for_cluster(feature_names, cluster_vectors, args.top_terms)
            else:
                centroid = np.array([])
                samples = cluster_texts[: args.examples]
                terms = []

            clusters.append(
                {
                    "id": int(label),
                    "size": len(cluster_texts),
                    "examples": samples,
                    "top_terms": terms
                }
            )

    clusters.sort(key=lambda c: c["size"], reverse=True)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "total_messages": len(texts),
        "cluster_count": len(clusters),
        "clusters": clusters
    }
    write_output(payload)


if __name__ == "__main__":
    main()
