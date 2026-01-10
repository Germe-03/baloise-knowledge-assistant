"""
Baloise Fuzzy Risk Scoring Engine
Bewertet Schadensmeldungen mit Fuzzy-Logik für Risiko-Analyse
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime, date


class RiskLevel(Enum):
    """Risikostufen"""
    SEHR_NIEDRIG = "Sehr niedrig"
    NIEDRIG = "Niedrig"
    MITTEL = "Mittel"
    HOCH = "Hoch"
    SEHR_HOCH = "Sehr hoch"


@dataclass
class FuzzyResult:
    """Ergebnis der Fuzzy-Risikobewertung"""
    score: float  # 0-100
    level: RiskLevel
    faktoren: List[Dict[str, any]] = field(default_factory=list)
    erklaerung: str = ""
    empfehlung: str = ""

    @property
    def farbe(self) -> str:
        """Farbe basierend auf Risikostufe"""
        colors = {
            RiskLevel.SEHR_NIEDRIG: "#22c55e",  # Grün
            RiskLevel.NIEDRIG: "#84cc16",       # Hellgrün
            RiskLevel.MITTEL: "#eab308",        # Gelb
            RiskLevel.HOCH: "#f97316",          # Orange
            RiskLevel.SEHR_HOCH: "#ef4444"      # Rot
        }
        return colors.get(self.level, "#6b7280")


class FuzzyMembershipFunctions:
    """
    Fuzzy Zugehörigkeitsfunktionen
    Definiert wie crisp Werte zu fuzzy Mengen gehören
    """

    @staticmethod
    def triangular(x: float, a: float, b: float, c: float) -> float:
        """
        Dreieckige Zugehörigkeitsfunktion
        a = linker Fuss, b = Spitze, c = rechter Fuss
        """
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        else:  # b < x < c
            return (c - x) / (c - b)

    @staticmethod
    def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
        """
        Trapezförmige Zugehörigkeitsfunktion
        a = linker Fuss, b = linke Schulter, c = rechte Schulter, d = rechter Fuss
        """
        if x <= a or x >= d:
            return 0.0
        elif a < x < b:
            return (x - a) / (b - a)
        elif b <= x <= c:
            return 1.0
        else:  # c < x < d
            return (d - x) / (d - c)

    @staticmethod
    def left_shoulder(x: float, a: float, b: float) -> float:
        """Linke Schulter - hoch links, fällt nach rechts"""
        if x <= a:
            return 1.0
        elif x >= b:
            return 0.0
        else:
            return (b - x) / (b - a)

    @staticmethod
    def right_shoulder(x: float, a: float, b: float) -> float:
        """Rechte Schulter - niedrig links, steigt nach rechts"""
        if x <= a:
            return 0.0
        elif x >= b:
            return 1.0
        else:
            return (x - a) / (b - a)


class FuzzyRiskEngine:
    """
    Fuzzy-Logik Engine für Risikobewertung von Schadensmeldungen

    Eingabe-Variablen:
    - Schadenshöhe (CHF)
    - Tage seit Vertragsabschluss
    - Anzahl vorheriger Schäden
    - Schadenszeitpunkt (Stunde)
    - Vollständigkeit der Angaben (%)

    Ausgabe:
    - Risiko-Score (0-100)
    """

    def __init__(self):
        self.mf = FuzzyMembershipFunctions()

    def fuzzify_schadenshoehe(self, betrag: float) -> Dict[str, float]:
        """
        Fuzzifizierung der Schadenshöhe

        Linguistische Variablen:
        - niedrig: 0 - 2000 CHF
        - mittel: 1000 - 10000 CHF
        - hoch: 5000 - 50000 CHF
        - sehr_hoch: > 30000 CHF
        """
        return {
            "niedrig": self.mf.left_shoulder(betrag, 1000, 3000),
            "mittel": self.mf.triangular(betrag, 2000, 7000, 15000),
            "hoch": self.mf.triangular(betrag, 10000, 30000, 60000),
            "sehr_hoch": self.mf.right_shoulder(betrag, 40000, 80000)
        }

    def fuzzify_vertragsdauer(self, tage: int) -> Dict[str, float]:
        """
        Fuzzifizierung der Vertragsdauer

        Linguistische Variablen:
        - sehr_kurz: < 30 Tage (verdächtig)
        - kurz: 30 - 180 Tage
        - mittel: 90 - 365 Tage
        - lang: > 180 Tage (weniger verdächtig)
        """
        return {
            "sehr_kurz": self.mf.left_shoulder(tage, 14, 45),
            "kurz": self.mf.triangular(tage, 30, 90, 180),
            "mittel": self.mf.triangular(tage, 120, 270, 400),
            "lang": self.mf.right_shoulder(tage, 300, 500)
        }

    def fuzzify_vorherige_schaeden(self, anzahl: int) -> Dict[str, float]:
        """
        Fuzzifizierung der Anzahl vorheriger Schäden

        Linguistische Variablen:
        - keine: 0
        - wenige: 1-2
        - mehrere: 2-4
        - viele: > 3
        """
        return {
            "keine": self.mf.left_shoulder(anzahl, 0.5, 1.5),
            "wenige": self.mf.triangular(anzahl, 0.5, 1.5, 3),
            "mehrere": self.mf.triangular(anzahl, 2, 3.5, 5),
            "viele": self.mf.right_shoulder(anzahl, 3.5, 6)
        }

    def fuzzify_zeitpunkt(self, stunde: int) -> Dict[str, float]:
        """
        Fuzzifizierung des Schadenszeitpunkts

        Linguistische Variablen:
        - normal: Geschäftszeiten (8-18 Uhr)
        - randzeit: Früh/Spät (6-8, 18-22 Uhr)
        - nacht: Nachtzeit (22-6 Uhr)
        """
        # Normalisiere auf 0-24
        stunde = stunde % 24

        # Nachtzeit (22-6) ist verdächtiger für gewisse Schäden
        if stunde >= 22 or stunde < 6:
            nacht = 1.0
            randzeit = 0.0
            normal = 0.0
        elif 6 <= stunde < 8 or 18 <= stunde < 22:
            nacht = 0.0
            randzeit = 1.0
            normal = 0.3
        else:  # 8-18 Uhr
            nacht = 0.0
            randzeit = 0.0
            normal = 1.0

        return {
            "normal": normal,
            "randzeit": randzeit,
            "nacht": nacht
        }

    def fuzzify_vollstaendigkeit(self, prozent: float) -> Dict[str, float]:
        """
        Fuzzifizierung der Angaben-Vollständigkeit

        Linguistische Variablen:
        - lueckenhaft: < 50%
        - teilweise: 40-80%
        - vollstaendig: > 70%
        """
        return {
            "lueckenhaft": self.mf.left_shoulder(prozent, 40, 60),
            "teilweise": self.mf.triangular(prozent, 50, 70, 90),
            "vollstaendig": self.mf.right_shoulder(prozent, 80, 95)
        }

    def apply_rules(self,
                    hoehe: Dict[str, float],
                    dauer: Dict[str, float],
                    vorherige: Dict[str, float],
                    zeitpunkt: Dict[str, float],
                    vollstaendigkeit: Dict[str, float]) -> List[Tuple[float, str, str]]:
        """
        Wendet Fuzzy-Regeln an und gibt aktivierte Regeln zurück

        Returns:
            List of (activation_strength, risk_level, rule_description)
        """
        regeln = []

        # === HOHE RISIKO REGELN ===

        # Regel 1: Sehr hoher Schaden + sehr kurze Vertragsdauer = SEHR HOHES Risiko
        activation = min(hoehe["sehr_hoch"], dauer["sehr_kurz"])
        if activation > 0:
            regeln.append((activation, "sehr_hoch",
                "Sehr hoher Schaden kurz nach Vertragsabschluss"))

        # Regel 2: Hoher Schaden + kurze Vertragsdauer = HOHES Risiko
        activation = min(hoehe["hoch"], dauer["kurz"])
        if activation > 0:
            regeln.append((activation, "hoch",
                "Hoher Schaden in kurzer Vertragsdauer"))

        # Regel 3: Viele vorherige Schäden + hoher aktueller Schaden = HOHES Risiko
        activation = min(vorherige["viele"], hoehe["hoch"])
        if activation > 0:
            regeln.append((activation, "hoch",
                "Häufige Schadensmeldungen mit hohen Beträgen"))

        # Regel 4: Lückenhafte Angaben + hoher Schaden = HOHES Risiko
        activation = min(vollstaendigkeit["lueckenhaft"], hoehe["hoch"])
        if activation > 0:
            regeln.append((activation, "hoch",
                "Unvollständige Angaben bei hohem Schaden"))

        # Regel 5: Nachtzeit + hoher Schaden = MITTLERES-HOHES Risiko
        activation = min(zeitpunkt["nacht"], hoehe["hoch"])
        if activation > 0:
            regeln.append((activation, "mittel_hoch",
                "Hoher Schaden zur Nachtzeit"))

        # === MITTLERE RISIKO REGELN ===

        # Regel 6: Mittlerer Schaden + kurze Vertragsdauer
        activation = min(hoehe["mittel"], dauer["kurz"])
        if activation > 0:
            regeln.append((activation, "mittel",
                "Mittlerer Schaden bei kurzer Vertragsdauer"))

        # Regel 7: Mehrere vorherige Schäden
        activation = vorherige["mehrere"]
        if activation > 0:
            regeln.append((activation, "mittel",
                "Mehrere vorherige Schadensmeldungen"))

        # Regel 8: Teilweise vollständige Angaben + mittlerer Schaden
        activation = min(vollstaendigkeit["teilweise"], hoehe["mittel"])
        if activation > 0:
            regeln.append((activation * 0.7, "mittel",
                "Teilweise unvollständige Angaben"))

        # === NIEDRIGE RISIKO REGELN ===

        # Regel 9: Niedriger Schaden + lange Vertragsdauer = NIEDRIGES Risiko
        activation = min(hoehe["niedrig"], dauer["lang"])
        if activation > 0:
            regeln.append((activation, "niedrig",
                "Niedriger Schaden bei langjährigem Kunden"))

        # Regel 10: Vollständige Angaben + normale Zeit = positiver Faktor
        activation = min(vollstaendigkeit["vollstaendig"], zeitpunkt["normal"])
        if activation > 0:
            regeln.append((activation, "sehr_niedrig",
                "Vollständige Angaben, normaler Zeitpunkt"))

        # Regel 11: Keine vorherigen Schäden + mittlerer/niedriger Schaden
        activation = min(vorherige["keine"], max(hoehe["niedrig"], hoehe["mittel"]))
        if activation > 0:
            regeln.append((activation, "niedrig",
                "Erster Schaden, moderate Höhe"))

        return regeln

    def defuzzify(self, activated_rules: List[Tuple[float, str, str]]) -> float:
        """
        Defuzzifizierung: Konvertiert Fuzzy-Ausgabe zu crisp Score
        Verwendet gewichteten Durchschnitt (Center of Gravity)
        """
        if not activated_rules:
            return 25.0  # Default: niedriges Risiko

        # Risiko-Level zu numerischen Werten
        level_values = {
            "sehr_niedrig": 10,
            "niedrig": 25,
            "mittel": 50,
            "mittel_hoch": 65,
            "hoch": 75,
            "sehr_hoch": 95
        }

        numerator = 0.0
        denominator = 0.0

        for activation, level, _ in activated_rules:
            value = level_values.get(level, 50)
            numerator += activation * value
            denominator += activation

        if denominator == 0:
            return 25.0

        return numerator / denominator

    def score_to_level(self, score: float) -> RiskLevel:
        """Konvertiert Score zu Risikostufe"""
        if score < 20:
            return RiskLevel.SEHR_NIEDRIG
        elif score < 40:
            return RiskLevel.NIEDRIG
        elif score < 60:
            return RiskLevel.MITTEL
        elif score < 80:
            return RiskLevel.HOCH
        else:
            return RiskLevel.SEHR_HOCH

    def generate_empfehlung(self, level: RiskLevel) -> str:
        """Generiert Handlungsempfehlung basierend auf Risikostufe"""
        empfehlungen = {
            RiskLevel.SEHR_NIEDRIG: "Standardbearbeitung. Automatische Freigabe möglich.",
            RiskLevel.NIEDRIG: "Standardbearbeitung. Stichprobenartige Prüfung empfohlen.",
            RiskLevel.MITTEL: "Manuelle Prüfung empfohlen. Dokumentation vervollständigen.",
            RiskLevel.HOCH: "Detailprüfung erforderlich. Senior-Sachbearbeiter einbeziehen.",
            RiskLevel.SEHR_HOCH: "Sofortige Eskalation. Betrugsprüfung durch Spezialteam."
        }
        return empfehlungen.get(level, "Manuelle Prüfung empfohlen.")

    def berechne_vollstaendigkeit(self, meldung_dict: Dict) -> float:
        """Berechnet Vollständigkeit der Angaben in Prozent"""
        wichtige_felder = [
            "schadenstyp",
            "schadensdatum",
            "schadensort",
            "schadensbeschreibung",
            "kontakt_telefon",
            "kontakt_email"
        ]

        optionale_felder = [
            "polizennummer",
            "schadenszeit",
            "schadensursache",
            "geschaetzter_betrag"
        ]

        # Wichtige Felder zählen doppelt
        score = 0
        max_score = len(wichtige_felder) * 2 + len(optionale_felder)

        for feld in wichtige_felder:
            if meldung_dict.get(feld):
                score += 2

        for feld in optionale_felder:
            if meldung_dict.get(feld):
                score += 1

        return (score / max_score) * 100

    def analyse(self,
                schadenshoehe: float,
                vertragsdauer_tage: int = 365,
                vorherige_schaeden: int = 0,
                schadenszeitpunkt_stunde: int = 12,
                vollstaendigkeit_prozent: float = 80.0,
                schadenstyp: str = "") -> FuzzyResult:
        """
        Hauptmethode: Analysiert eine Schadensmeldung

        Args:
            schadenshoehe: Geschätzter Schaden in CHF
            vertragsdauer_tage: Tage seit Vertragsabschluss
            vorherige_schaeden: Anzahl vorheriger Schadensmeldungen
            schadenszeitpunkt_stunde: Stunde des Schadens (0-23)
            vollstaendigkeit_prozent: Vollständigkeit der Angaben (0-100)
            schadenstyp: Art des Schadens

        Returns:
            FuzzyResult mit Score, Level, Faktoren und Empfehlung
        """

        # 1. Fuzzifizierung
        hoehe = self.fuzzify_schadenshoehe(schadenshoehe)
        dauer = self.fuzzify_vertragsdauer(vertragsdauer_tage)
        vorherige = self.fuzzify_vorherige_schaeden(vorherige_schaeden)
        zeitpunkt = self.fuzzify_zeitpunkt(schadenszeitpunkt_stunde)
        vollstaendigkeit = self.fuzzify_vollstaendigkeit(vollstaendigkeit_prozent)

        # 2. Regelauswertung
        activated_rules = self.apply_rules(hoehe, dauer, vorherige, zeitpunkt, vollstaendigkeit)

        # 3. Defuzzifizierung
        score = self.defuzzify(activated_rules)

        # 4. Risikostufe bestimmen
        level = self.score_to_level(score)

        # 5. Faktoren für Erklärung aufbereiten
        faktoren = []

        # Schadenshöhe
        max_hoehe = max(hoehe.items(), key=lambda x: x[1])
        faktoren.append({
            "name": "Schadenshöhe",
            "wert": f"{schadenshoehe:,.0f} CHF",
            "bewertung": max_hoehe[0].replace("_", " ").title(),
            "zugehoerigkeit": max_hoehe[1],
            "einfluss": "hoch" if schadenshoehe > 20000 else "mittel"
        })

        # Vertragsdauer
        max_dauer = max(dauer.items(), key=lambda x: x[1])
        faktoren.append({
            "name": "Vertragsdauer",
            "wert": f"{vertragsdauer_tage} Tage",
            "bewertung": max_dauer[0].replace("_", " ").title(),
            "zugehoerigkeit": max_dauer[1],
            "einfluss": "hoch" if vertragsdauer_tage < 60 else "niedrig"
        })

        # Vorherige Schäden
        max_vorherige = max(vorherige.items(), key=lambda x: x[1])
        faktoren.append({
            "name": "Vorherige Schäden",
            "wert": str(vorherige_schaeden),
            "bewertung": max_vorherige[0].replace("_", " ").title(),
            "zugehoerigkeit": max_vorherige[1],
            "einfluss": "hoch" if vorherige_schaeden > 2 else "niedrig"
        })

        # Vollständigkeit
        max_vollst = max(vollstaendigkeit.items(), key=lambda x: x[1])
        faktoren.append({
            "name": "Angaben-Vollständigkeit",
            "wert": f"{vollstaendigkeit_prozent:.0f}%",
            "bewertung": max_vollst[0].replace("_", " ").title(),
            "zugehoerigkeit": max_vollst[1],
            "einfluss": "mittel" if vollstaendigkeit_prozent < 70 else "niedrig"
        })

        # 6. Erklärung generieren
        if activated_rules:
            # Top 3 aktivierte Regeln
            top_rules = sorted(activated_rules, key=lambda x: x[0], reverse=True)[:3]
            erklaerung_parts = [f"• {rule[2]} (Gewicht: {rule[0]:.1%})" for rule in top_rules]
            erklaerung = "Hauptfaktoren:\n" + "\n".join(erklaerung_parts)
        else:
            erklaerung = "Keine auffälligen Muster erkannt."

        # 7. Empfehlung
        empfehlung = self.generate_empfehlung(level)

        return FuzzyResult(
            score=round(score, 1),
            level=level,
            faktoren=faktoren,
            erklaerung=erklaerung,
            empfehlung=empfehlung
        )

    def analyse_schadensmeldung(self, meldung) -> FuzzyResult:
        """
        Analysiert eine Schadensmeldung-Instanz

        Args:
            meldung: Schadensmeldung Objekt

        Returns:
            FuzzyResult
        """
        # Schadenshöhe
        schadenshoehe = getattr(meldung, 'geschaetzter_betrag', 0) or 0

        # Vertragsdauer (simuliert - in Produktion aus CRM)
        # Für Demo: zufällig basierend auf Policennummer
        polizennummer = getattr(meldung, 'polizennummer', '') or ''
        if polizennummer and polizennummer != 'unbekannt':
            # Simuliere Vertragsdauer basierend auf Policennummer
            vertragsdauer = hash(polizennummer) % 1000 + 30
        else:
            vertragsdauer = 180  # Default: 6 Monate

        # Vorherige Schäden (simuliert - in Produktion aus Datenbank)
        vorherige_schaeden = 0  # Default für neue Analyse

        # Schadenszeitpunkt
        schadenszeit = getattr(meldung, 'schadenszeit', '') or ''
        try:
            if ':' in schadenszeit:
                stunde = int(schadenszeit.split(':')[0])
            elif 'nacht' in schadenszeit.lower():
                stunde = 2
            elif 'morgen' in schadenszeit.lower():
                stunde = 7
            elif 'mittag' in schadenszeit.lower():
                stunde = 12
            elif 'abend' in schadenszeit.lower():
                stunde = 20
            else:
                stunde = 12
        except:
            stunde = 12

        # Vollständigkeit berechnen
        meldung_dict = meldung.to_dict() if hasattr(meldung, 'to_dict') else {}
        vollstaendigkeit = self.berechne_vollstaendigkeit(meldung_dict)

        # Schadenstyp
        schadenstyp = getattr(meldung, 'schadenstyp', '') or ''

        return self.analyse(
            schadenshoehe=schadenshoehe,
            vertragsdauer_tage=vertragsdauer,
            vorherige_schaeden=vorherige_schaeden,
            schadenszeitpunkt_stunde=stunde,
            vollstaendigkeit_prozent=vollstaendigkeit,
            schadenstyp=schadenstyp
        )


# Singleton-Instanz
fuzzy_risk_engine = FuzzyRiskEngine()


# === DEMO / TEST ===
if __name__ == "__main__":
    engine = FuzzyRiskEngine()

    print("=" * 60)
    print("FUZZY RISK ENGINE - TEST")
    print("=" * 60)

    # Testfälle
    testcases = [
        {
            "name": "Normaler Fall",
            "schadenshoehe": 3000,
            "vertragsdauer_tage": 730,
            "vorherige_schaeden": 0,
            "schadenszeitpunkt_stunde": 14,
            "vollstaendigkeit_prozent": 90
        },
        {
            "name": "Verdächtiger Fall",
            "schadenshoehe": 50000,
            "vertragsdauer_tage": 20,
            "vorherige_schaeden": 3,
            "schadenszeitpunkt_stunde": 3,
            "vollstaendigkeit_prozent": 45
        },
        {
            "name": "Mittleres Risiko",
            "schadenshoehe": 15000,
            "vertragsdauer_tage": 90,
            "vorherige_schaeden": 1,
            "schadenszeitpunkt_stunde": 19,
            "vollstaendigkeit_prozent": 70
        }
    ]

    for tc in testcases:
        print(f"\n--- {tc['name']} ---")
        result = engine.analyse(
            schadenshoehe=tc["schadenshoehe"],
            vertragsdauer_tage=tc["vertragsdauer_tage"],
            vorherige_schaeden=tc["vorherige_schaeden"],
            schadenszeitpunkt_stunde=tc["schadenszeitpunkt_stunde"],
            vollstaendigkeit_prozent=tc["vollstaendigkeit_prozent"]
        )

        print(f"Score: {result.score}/100")
        print(f"Level: {result.level.value}")
        print(f"Empfehlung: {result.empfehlung}")
        print(f"\n{result.erklaerung}")
