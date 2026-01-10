"""
Query Enhancement Module
=========================
Verbessert RAG-Suchanfragen durch:
1. Query Expansion - Erweitert Anfragen mit Fachbegriffen
2. Re-Ranking - Bewertet Ergebnisse nach Relevanz neu

Implementiert gemäss Wissenschaftliche Notizen v2.1
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


# =============================================================================
# QUERY EXPANSION
# =============================================================================

# Juristische Synonyme und Fachbegriffe (Deutsch/Schweiz)
LEGAL_EXPANSIONS = {
    # Vertragsrecht
    "vertrag": ["Kontrakt", "Vereinbarung", "Obligationenrecht", "OR"],
    "vertrag entsteht": ["Entstehung durch Vertrag", "Vertragsschluss", "Willensäusserung", "Antrag Annahme"],
    "kündigung": ["Kündigungsfrist", "Beendigung", "Auflösung", "Art. 335"],
    "kündigungsfrist": ["Probezeit", "Dienstjahr", "Art. 335c OR"],
    "arbeitsvertrag": ["Einzelarbeitsvertrag", "Arbeitsverhältnis", "Art. 319 OR"],
    "miete": ["Mietvertrag", "Mietzins", "Vermieter", "Mieter", "VMWG"],
    "kauf": ["Kaufvertrag", "Käufer", "Verkäufer", "Kaufpreis"],
    "schaden": ["Schadenersatz", "Haftung", "Art. 41 OR", "unerlaubte Handlung"],
    "gewährleistung": ["Mängel", "Sachmangel", "Wandelung", "Minderung"],

    # Allgemeines Recht
    "gesetz": ["Bundesgesetz", "Verordnung", "SR", "Rechtsnorm"],
    "artikel": ["Art.", "Absatz", "Buchstabe", "Ziffer"],
    "recht": ["Anspruch", "Berechtigung", "Pflicht"],
    "pflicht": ["Obligation", "Verpflichtung", "Schuld"],
    "frist": ["Termin", "Zeitraum", "Verjährung"],

    # Personenrecht
    "person": ["natürliche Person", "juristische Person", "Rechtsfähigkeit"],
    "firma": ["Gesellschaft", "AG", "GmbH", "Einzelunternehmen"],
    "ehe": ["Eheschliessung", "Ehevertrag", "Güterstand", "ZGB"],
    "erbe": ["Erbschaft", "Nachlass", "Testament", "Erbfolge"],

    # Datenschutz
    "datenschutz": ["DSG", "Personendaten", "Datenbearbeitung", "Einwilligung"],
    "daten": ["Personendaten", "besonders schützenswerte Personendaten", "Profiling"],

    # Strafrecht
    "strafe": ["Sanktion", "Busse", "Freiheitsstrafe", "StGB"],
    "betrug": ["Arglist", "Täuschung", "Vermögensschaden"],
    "diebstahl": ["Entwendung", "Aneignung", "Art. 139 StGB"],

    # Arbeitsrecht
    "arbeit": ["Arbeitsrecht", "Arbeitnehmer", "Arbeitgeber", "ArG"],
    "lohn": ["Gehalt", "Entgelt", "Vergütung", "Saläir"],
    "ferien": ["Urlaub", "Ferienanspruch", "Art. 329a OR"],
    "überstunden": ["Überzeit", "Mehrarbeit", "Kompensation"],
}

# Mapping von Wissensbasen zu Expansion-Dictionaries
KB_EXPANSIONS = {
    "bundesrecht": LEGAL_EXPANSIONS,
    # Weitere Wissensbasen können hier hinzugefügt werden
    # "medizin": MEDICAL_EXPANSIONS,
    # "technik": TECHNICAL_EXPANSIONS,
}


def expand_query(query: str, knowledge_base_ids: Optional[List[str]] = None) -> str:
    """
    Erweitert eine Suchanfrage mit domänenspezifischen Fachbegriffen.

    Args:
        query: Ursprüngliche Suchanfrage
        knowledge_base_ids: Liste der Wissensbank-IDs

    Returns:
        Erweiterte Suchanfrage
    """
    if not knowledge_base_ids:
        return query

    expanded_terms = []
    query_lower = query.lower()

    # Prüfe welche Expansions relevant sind
    for kb_id in knowledge_base_ids:
        if kb_id in KB_EXPANSIONS:
            expansions = KB_EXPANSIONS[kb_id]

            # Suche nach passenden Begriffen
            for term, synonyms in expansions.items():
                if term in query_lower:
                    # Füge Synonyme hinzu (max 3 pro Begriff)
                    expanded_terms.extend(synonyms[:3])

    if expanded_terms:
        # Deduplizieren und zur Query hinzufügen
        unique_terms = list(dict.fromkeys(expanded_terms))
        expansion = " ".join(unique_terms[:6])  # Max 6 zusätzliche Terme
        return f"{query} {expansion}"

    return query


def get_expansion_info(query: str, knowledge_base_ids: Optional[List[str]] = None) -> Dict:
    """
    Gibt Informationen über die Query-Expansion zurück (für Debugging/Logging).
    """
    original = query
    expanded = expand_query(query, knowledge_base_ids)

    return {
        "original_query": original,
        "expanded_query": expanded,
        "was_expanded": original != expanded,
        "added_terms": expanded.replace(original, "").strip() if original != expanded else ""
    }


# =============================================================================
# RE-RANKING
# =============================================================================

@dataclass
class RankedResult:
    """Ein neu bewertetes Suchergebnis"""
    content: str
    original_score: float
    rerank_score: float
    final_score: float
    metadata: Dict
    chunk_id: str
    boost_reasons: List[str]


# Boost-Faktoren für verschiedene Kriterien
RERANK_BOOSTS = {
    # Artikel-Referenzen (wichtig für Rechtstexte)
    "has_article_ref": 0.15,      # Enthält "Art. X"
    "has_sr_number": 0.10,        # Enthält SR-Nummer

    # Strukturelle Qualität
    "has_definition": 0.10,       # Enthält "ist" oder "bedeutet"
    "is_paragraph_start": 0.05,   # Beginnt mit Ziffer oder Buchstabe

    # Keyword-Matches (exakt)
    "exact_keyword_match": 0.20,  # Query-Wort exakt enthalten

    # Länge (zu kurz = wenig Kontext, zu lang = verwässert)
    "optimal_length": 0.05,       # 200-600 Zeichen
}

# Patterns für Boost-Erkennung
ARTICLE_PATTERN = re.compile(r'Art\.\s*\d+[a-z]?', re.IGNORECASE)
SR_PATTERN = re.compile(r'SR\s*\d+\.?\d*', re.IGNORECASE)
DEFINITION_PATTERNS = [" ist ", " sind ", " bedeutet ", " bezeichnet ", " gilt als "]


def rerank_results(
    results: List,  # List[SearchResult]
    query: str,
    boost_legal: bool = True
) -> List:
    """
    Bewertet Suchergebnisse neu basierend auf zusätzlichen Kriterien.

    Args:
        results: Liste von SearchResult-Objekten
        query: Ursprüngliche Suchanfrage
        boost_legal: Ob juristische Boosts angewendet werden sollen

    Returns:
        Neu sortierte Liste von SearchResult-Objekten
    """
    if not results:
        return results

    query_words = set(query.lower().split())
    ranked = []

    for result in results:
        content = result.content
        content_lower = content.lower()
        boost = 0.0
        reasons = []

        # 1. Artikel-Referenz Boost
        if boost_legal and ARTICLE_PATTERN.search(content):
            boost += RERANK_BOOSTS["has_article_ref"]
            reasons.append("Artikel-Referenz")

        # 2. SR-Nummer Boost
        if boost_legal and SR_PATTERN.search(content):
            boost += RERANK_BOOSTS["has_sr_number"]
            reasons.append("SR-Nummer")

        # 3. Definition Boost
        if any(pattern in content_lower for pattern in DEFINITION_PATTERNS):
            boost += RERANK_BOOSTS["has_definition"]
            reasons.append("Definition")

        # 4. Exakter Keyword-Match
        matches = sum(1 for word in query_words if word in content_lower and len(word) > 3)
        if matches >= 2:
            boost += RERANK_BOOSTS["exact_keyword_match"] * min(matches / 3, 1.0)
            reasons.append(f"Keywords ({matches})")

        # 5. Optimale Länge
        length = len(content)
        if 200 <= length <= 600:
            boost += RERANK_BOOSTS["optimal_length"]
            reasons.append("Optimale Länge")

        # Finalen Score berechnen
        original_score = result.score
        final_score = min(1.0, original_score + boost)  # Cap bei 1.0

        # Score im Result aktualisieren
        result.score = final_score
        result._rerank_boost = boost
        result._rerank_reasons = reasons

        ranked.append(result)

    # Nach finalem Score sortieren
    ranked.sort(key=lambda x: x.score, reverse=True)

    return ranked


def get_rerank_stats(results: List) -> Dict:
    """
    Gibt Statistiken über das Re-Ranking zurück (für Debugging).
    """
    if not results:
        return {"count": 0}

    boosts = [getattr(r, '_rerank_boost', 0) for r in results]
    reasons_all = []
    for r in results:
        reasons_all.extend(getattr(r, '_rerank_reasons', []))

    from collections import Counter
    reason_counts = Counter(reasons_all)

    return {
        "count": len(results),
        "avg_boost": sum(boosts) / len(boosts) if boosts else 0,
        "max_boost": max(boosts) if boosts else 0,
        "boost_reasons": dict(reason_counts),
    }


# =============================================================================
# COMBINED ENHANCEMENT
# =============================================================================

def enhance_search(
    query: str,
    knowledge_base_ids: Optional[List[str]] = None,
    enable_expansion: bool = True,
    enable_rerank: bool = True
) -> Tuple[str, Dict]:
    """
    Kombinierte Query-Enhancement Funktion.

    Args:
        query: Ursprüngliche Suchanfrage
        knowledge_base_ids: Liste der Wissensbank-IDs
        enable_expansion: Query Expansion aktivieren
        enable_rerank: Re-Ranking aktivieren (Flag für spätere Verwendung)

    Returns:
        Tuple von (erweiterter Query, Enhancement-Info)
    """
    info = {
        "expansion_enabled": enable_expansion,
        "rerank_enabled": enable_rerank,
    }

    if enable_expansion:
        expansion_info = get_expansion_info(query, knowledge_base_ids)
        info["expansion"] = expansion_info
        query = expansion_info["expanded_query"]

    return query, info
