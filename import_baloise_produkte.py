"""
Baloise Produktinformationen Import
Lädt alle Versicherungsprodukte in die Wissensbasis
"""

import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.rag_engine import rag_engine
from app.core.document_processor import ProcessedDocument, DocumentChunk
from app.config import config
from datetime import datetime

# Baloise Versicherungsprodukte - gesammelte Informationen
BALOISE_PRODUKTE = [
    {
        "titel": "Haftpflichtversicherung",
        "kategorie": "Wohnen & Recht",
        "inhalt": """# Baloise Haftpflichtversicherung

## Übersicht
Die Haftpflichtversicherung der Baloise schützt Sie vor den finanziellen Folgen, wenn Sie versehentlich Dritten oder deren Eigentum Schaden zufügen.

## Deckungen & Leistungen

**Versicherungssumme:** Bis zu 10 Millionen Franken für Personen- und Sachschäden.

**Weltweiter Schutz:** Die Versicherung gilt weltweit.

### Abgedeckte Fälle:
- Versehentlich verursachte Schäden an Dritten oder deren Eigentum
- Abwehr ungerechtfertigter Ansprüche (passiver Rechtsschutz)
- Schäden durch Haustiere (Hunde, Katzen, etc.)
- Schäden an gelegentlich genutzten fremden Fahrzeugen
- Drohnen und Modellluftfahrzeuge (ohne BAZL-Bewilligung)
- Schäden als Mieter an der gemieteten Wohnung

### Familienversicherung:
Bei einer Familienpolice sind alle Personen mitversichert, die im selben Haushalt wohnen - einschliesslich Kinder, auch wenn sie auswärts studieren.

## Optionale Sicherheitsbausteine

### Sorglos-Baustein
Deckt Grobfahrlässigkeit ab. Relevant für Unfälle durch Unachtsamkeit, z.B.:
- Bei Rot über die Ampel fahren mit dem Velo
- Handy-Nutzung während des Fahrens
- Unaufmerksamkeit im Strassenverkehr

### Protection-Baustein
Cyber-Deckung für:
- Kreditkartenmissbrauch
- Datenraub und Identitätsdiebstahl
- Cyber-Mobbing
- Online-Betrug

## Nicht gedeckt
- Absichtlich oder vorhersehbar verursachte Schäden
- Schäden am eigenen Eigentum oder dem von Haushaltsmitgliedern
- Beruflich verursachte Schäden (dafür: Berufshaftpflicht)

## Kundenbewertung
4.8 von 5 Sternen (basierend auf über 5'000 Bewertungen)

## Abschluss
Online-Abschluss möglich unter baloise.ch
Zahlung bequem per eBill"""
    },
    {
        "titel": "Hausratversicherung",
        "kategorie": "Wohnen & Recht",
        "inhalt": """# Baloise Hausratversicherung

## Übersicht
Die Hausratversicherung schützt Ihr Hab und Gut gegen Schäden durch Feuer, Wasser, Einbruch und mehr. Laut Kassensturz bietet Baloise die günstigste Haushaltsversicherung.

## Deckungen

### Feuer & Blitz
- Ersatz des beschädigten Hausrats zum Neuwert
- Aufräumungs- und Entsorgungskosten
- Schlossänderungskosten nach Einbruch

### Elementarereignisse
- Hagel und Sturm
- Hochwasser und Überschwemmungen
- Lawinen und Erdrutsche

### Erdbeben
Schutz für beschädigte oder zerstörte Gegenstände bei Erdbeben.

### Diebstahl
- Einbruchdiebstahl
- Beraubung
- Einfacher Diebstahl (weltweit)

### Wasserschäden
- Leitungswasser
- Heizungswasser
- Eindringendes Wasser durch Fenster/Türen

### Glasbruch
An Gebäude- und Mobiliarverglasungen.

## Zusätzliche Leistungen
- Kosten für Aufräumarbeiten
- Entsorgungskosten
- Schlossänderungen nach Einbruch
- Hotelkosten bei Unbewohnbarkeit

## Optionen

### Hausratkasko Basis
Schutz gegen selbstverschuldete Beschädigungen, z.B.:
- Verschütteter Kaffee auf dem Laptop
- Heruntergefallenes Smartphone
- Beschädigte Möbel beim Umzug

### Hausratkasko Plus
Erweiterte Elektronik-Deckung für:
- Smartphones und Tablets
- E-Bikes und Elektrovelos
- TV-Geräte und Computer
- Kameras und Drohnen

### Sicherheitsbaustein Sorglos
- Deckung bei Grobfahrlässigkeit
- Grossschadenservice

### Sicherheitsbaustein Protection
- Cyber-Deckung
- Home Assistance

## Preise

### younGo (unter 30 Jahren)
Ab CHF 160 pro Jahr für:
- Einzelhaushalte
- Wohngemeinschaften
- Junge Familien

### Standard
Individuelle Berechnung über Online-Prämienrechner

## Geltungsbereich
- Weltweit (ausser Glasbruch und einfacher Diebstahl: nur am Versicherungsort)

## Kundenbewertung
4.8 von 5 Sternen - Comparis-Siegel Silber für beste Bewertungen"""
    },
    {
        "titel": "Autoversicherung",
        "kategorie": "Fahrzeuge",
        "inhalt": """# Baloise Autoversicherung

## Übersicht
Umfassender Versicherungsschutz für Ihr Fahrzeug mit schneller Schadensabwicklung und attraktiven Zusatzleistungen.

## Deckungsarten

### Haftpflichtversicherung (obligatorisch)
Die gesetzlich vorgeschriebene Versicherung übernimmt:
- Personenschäden an anderen Verkehrsteilnehmern
- Sachschäden an fremdem Eigentum
- Schäden an Tieren

### Teilkasko
Kombiniert Haftpflicht mit Schutz vor externen Ereignissen:
- Hagelschäden
- Steinschlag und Glasbruch
- Marderbiss und Folgeschäden
- Wildtierkollisionen
- Diebstahl des Fahrzeugs
- Elementarschäden (Sturm, Überschwemmung)

### Vollkasko
Umfassendster Schutz inklusive:
- Haftpflichtversicherung
- Teilkaskoversicherung
- Kollisionsversicherung (selbstverschuldete Unfälle)
- Parkschäden

## Besondere Leistungen

### Kaufpreisgarantie
100% Kaufpreisentschädigung bis zum 7. Betriebsjahr bei Totalschaden.

### EasyRepair-Services
- Hol- und Bringservice
- Glasreparatur vor Ort
- Ersatzfahrzeug während der Reparatur
- Zertifizierte Reparaturpartner

### Vergünstigungen
- Rabatte auf Fahrsicherheitstrainings
- Bonusschutz bei langjähriger Schadenfreiheit

## Zusatzoptionen

### Parkschadenversicherung
Schutz bei Schäden durch unbekannte Verursacher auf Parkplätzen.

### Leuchten- und Assistenzsystemschutz
Deckung für teure LED-Scheinwerfer und Fahrassistenzsysteme.

### Persönliche Gegenstände
Schutz für Gegenstände im Fahrzeug (Laptop, Sportausrüstung, etc.)

### Pannenhilfe & Assistance
- 24/7 Pannendienst
- Abschleppdienst
- Weiterreise oder Rücktransport
- Hotel bei Panne auf Reisen

### Innenraumschutz
Deckung für Schäden am Fahrzeuginnenraum.

### Unfallversicherung für Insassen
Schutz für Fahrer und Mitfahrende bei Unfällen.

## Sicherheitsbausteine

### Eigenschäden
Deckung für selbstverschuldete Schäden am eigenen Fahrzeug.

### Sorglos
- Deckung bei Grobfahrlässigkeit
- Kein Bonus-Verlust bei erstem Schaden

## Prämienberechnung
Individuelle Berechnung über Online-Prämienrechner basierend auf:
- Fahrzeugtyp und -alter
- Kilometerleistung
- Schadenfreiheitsrabatt
- Wohnort"""
    },
    {
        "titel": "Lebensversicherung",
        "kategorie": "Personen",
        "inhalt": """# Baloise Lebensversicherungen

## Übersicht
Baloise bietet verschiedene Lebensversicherungsprodukte für Vorsorge, Absicherung und Vermögensaufbau.

## Produktpalette

### 1. Baloise Safe Plan & Safe Plan 100
**Die flexible Lebensversicherung mit Garantie**
- Kombination aus Vorsorge und Renditechancen
- Anpassbar an wechselnde Lebenssituationen
- Garantierte Mindestauszahlung
- Flexible Laufzeiten und Prämien

### 2. Baloise Fonds Plan
**Anteilgebundene Lebensversicherung**
- Selbstbestimmte Geldanlage in Fonds
- Garantierte Leistungen bei Todesfall
- Garantierte Leistungen bei Erwerbsunfähigkeit
- Höhere Renditechancen durch Fondsanlage

### 3. Baloise Fonds Plan Kids
**Kinderversicherung mit Vermögensaufbau**
- Schutz und Geldanlage für Kinder
- Vermögensaufbau bis zur Volljährigkeit
- Flexible Verwendung des angesparten Kapitals
- Absicherung bei Invalidität des Kindes

### 4. Baloise Safe Invest
**Lebensversicherung mit Einmalprämie**
- Einmalige Prämienzahlung
- Garantierte Mindestauszahlung nach 10-15 Jahren
- Partizipation an Marktchancen
- Ideale Ergänzung zur Altersvorsorge

## Kernleistungen aller Produkte

### Finanzielle Absicherung
- Todesfallkapital für Hinterbliebene
- Einmalzahlung oder Rente wählbar

### Erwerbsunfähigkeitsschutz
- Prämienbefreiung bei Erwerbsunfähigkeit
- Optionale Erwerbsunfähigkeitsrente

### Steuervorteile
- Besonders attraktiv in der Säule 3a
- Steuerlich begünstigte Vorsorge

### Flexibilität
- Anpassbare Vertragslaufzeiten
- Änderung der Prämienhöhe möglich
- Teilrückkauf bei Bedarf

## Zusätzliche Sicherheitsbausteine

### Life Coach
Unterstützung für Hinterbliebene im Wert von max. CHF 10'000:
- Hilfe bei Beerdigungsorganisation
- Betreuung und psychologische Vermittlung
- Administrative Unterstützung
- Juristische Erstberatung
- Finanzielle Beratung

### Sofortzahlung
Bis CHF 10'000 sofort verfügbar im Todesfall für:
- Beerdigungskosten
- Laufende Rechnungen
- Überbrückung bis zur regulären Auszahlung

### Versicherbarkeitsgarantie
- Erhöhung der Versicherungssumme ohne erneute Gesundheitsprüfung
- Bei wichtigen Lebensereignissen (Heirat, Geburt, Hauskauf)"""
    },
    {
        "titel": "Rechtsschutzversicherung",
        "kategorie": "Wohnen & Recht",
        "inhalt": """# Baloise Rechtsschutzversicherung

## Übersicht
Die Rechtsschutzversicherung wird in Zusammenarbeit mit Assista Rechtsschutz AG angeboten - dem grössten Schweizer Anbieter von Rechtsschutzversicherungen für Privatpersonen.

## Leistungen

### Analyse der Rechtslage
Experten prüfen Ihren Fall und schätzen die Erfolgsaussichten ein.

### Beratung
Juristische Beratung durch Fachspezialisten.

### Vertretung
Vertretung Ihrer Interessen vor Gericht durch erfahrene Anwälte.

### Kostenübernahme
- Anwaltskosten
- Gerichtskosten
- Gutachterkosten
- Zeugenentschädigungen
- Gegnerische Kosten bei Niederlage

## Versicherte Bereiche

### Privatrechtsschutz
- Vertragsstreitigkeiten
- Nachbarschaftskonflikte
- Konsumentenrecht
- Mietrecht
- Arbeitsrecht (als Arbeitnehmer)

### Verkehrsrechtsschutz
- Unfallstreitigkeiten
- Führerscheinentzug
- Bussenverfahren
- Schadenersatzforderungen

### Rechtsschutz für Hauseigentümer
- Streitigkeiten mit Mietern
- Baunachbarrecht
- Werkverträge
- Stockwerkeigentum

## Geltungsbereich
Die Versicherung gilt für alle im Haushalt wohnenden Personen, unabhängig von:
- Alter
- Erwerbsstatus
- Verwandtschaftsverhältnis

## Abschlussmöglichkeiten
- Einzelversicherung
- Im Paket mit Haushaltsversicherung (BaloiseCombi)

## Partner
Assista Rechtsschutz AG - Schweizer Marktführer für Rechtsschutzversicherungen"""
    },
    {
        "titel": "Reiseversicherung",
        "kategorie": "Reisen & Ferien",
        "inhalt": """# Baloise Reiseversicherung

## Übersicht
Mit der Baloise Reiseversicherung sind Sie, Ihr Gepäck und Ihr Fahrzeug während der Ferien rundum geschützt - ob Wandertrip in der Schweiz, Strandferien in Italien oder Städtereise nach New York.

## Versicherungsoptionen

### Jahresversicherung
- Ganzjähriger Schutz für alle Reisen
- Ideal für Vielreisende
- Einmalige Jahresprämie

### Einzelreiseversicherung
- Für einzelne Reisen buchbar
- Reisedauer: 2 bis 92 Tage
- Flexible Buchung

## Deckungen

### Reiseannullierung
- Stornokosten bei Krankheit oder Unfall
- Berufliche Verhinderung
- Todesfall in der Familie
- Arbeitsplatzverlust

### Reiseabbruch
- Vorzeitige Rückreisekosten
- Nicht genutzte Reiseleistungen

### Gepäckversicherung
- Diebstahl von Gepäck
- Beschädigung von Gepäck
- Verspätetes Gepäck (Ersatzkäufe)

### Personen-Assistance
- 24/7 Notfall-Hotline
- Medizinische Beratung
- Rücktransport bei Krankheit/Unfall
- Überführung im Todesfall

### SOS-Bargeld
Soforthilfe bei Diebstahl von Geld und Dokumenten.

## Spezialversicherungen

### Mietfahrzeug-Versicherung
- Schutz bei Schäden am Mietwagen
- Selbstbehalt-Ausschluss
- Weltweite Geltung

### Ferienversicherung
Umfassendes Paket für unbeschwerte Ferien mit:
- Reiseschutz
- Gepäckschutz
- Assistance-Leistungen

## Reiseversicherung Drive
Speziell für Autoreisen mit zusätzlichen Leistungen:
- Pannenhilfe im Ausland
- Fahrzeugrücktransport
- Weiterreise oder Hotelkosten"""
    },
    {
        "titel": "Motorradversicherung",
        "kategorie": "Fahrzeuge",
        "inhalt": """# Baloise Motorradversicherung

## Übersicht
Versicherungsschutz für Motorräder, Roller und Mopeds - für ein sicheres Fahrvergnügen auf zwei Rädern.

## Deckungsarten

### Haftpflichtversicherung (obligatorisch)
- Personenschäden an Dritten
- Sachschäden an fremdem Eigentum
- Gesetzlich vorgeschrieben

### Teilkasko
Schutz vor:
- Diebstahl des Motorrads
- Feuer und Explosion
- Elementarschäden (Hagel, Sturm)
- Glasbruch
- Marderbiss
- Wildtierkollisionen

### Vollkasko
Zusätzlich zur Teilkasko:
- Selbstverschuldete Unfälle
- Kollisionsschäden
- Umfallschäden

## Zusatzleistungen

### Pannenhilfe
- 24/7 Pannendienst
- Abschleppdienst
- Weiterreise oder Rücktransport

### Zubehör & Bekleidung
Optionale Deckung für:
- Motorradbekleidung (Helm, Jacke, Hose)
- Tankrucksack und Koffer
- Navigationssysteme

### Schutz für Fahrer
- Unfallversicherung für den Fahrer
- Invaliditätskapital
- Todesfallkapital

## Saisonkennzeichen
Möglichkeit für Saisonversicherung mit reduzierten Prämien.

## Online-Abschluss
Versicherung kann online berechnet und abgeschlossen werden."""
    },
    {
        "titel": "Wertsachenversicherung",
        "kategorie": "Wohnen & Recht",
        "inhalt": """# Baloise Wertsachenversicherung

## Übersicht
Umfassender Schutz für Ihr wertvollstes Hab und Gut - von Schmuck über Uhren bis zu Kunstwerken.

## Versicherte Gegenstände

### Schmuck & Uhren
- Ringe, Ketten, Armbänder
- Luxusuhren
- Edelsteine

### Kunst & Antiquitäten
- Gemälde und Skulpturen
- Antiquitäten
- Sammlerstücke

### Elektronik
- Hochwertige Kameras
- Musikinstrumente
- Sammlungen

### Pelze & Designer-Mode
- Pelzmäntel
- Designer-Handtaschen
- Luxusmode

## Deckungen

### Allgefahrendeckung
Schutz gegen praktisch alle Risiken:
- Diebstahl (auch ohne Einbruch)
- Verlust
- Beschädigung
- Zerstörung

### Weltweiter Schutz
Die Versicherung gilt weltweit - auch auf Reisen.

### Neuwertentschädigung
Ersatz zum aktuellen Wiederbeschaffungswert.

## Besonderheiten
- Keine Unterversicherung
- Schnelle Schadensregulierung
- Individuelle Bewertung durch Experten"""
    },
    {
        "titel": "E-Bike-Versicherung",
        "kategorie": "Fahrzeuge",
        "inhalt": """# Baloise E-Bike-Versicherung

## Übersicht
Idealer Schutz für Ihr E-Bike oder Elektrovelo - als Teil der Hausratversicherung oder separat.

## Deckungen

### Diebstahl
- Diebstahl des gesamten E-Bikes
- Diebstahl von fest montierten Teilen
- Weltweit geschützt

### Beschädigung
- Unfallschäden
- Vandalismus
- Sturzschäden

### Elektronik-Schutz
- Defekte am Motor
- Akkuschäden
- Displayschäden

## Versicherung über Hausratkasko Plus
Die E-Bike-Versicherung ist Teil der Hausratkasko Plus und deckt:
- Smartphones und Tablets
- E-Bikes und Elektrovelos
- TV-Geräte und Computer
- Kameras und Drohnen

## Voraussetzungen
- E-Bike muss mit einem zugelassenen Schloss gesichert sein
- Bei Diebstahl: Anzeige bei der Polizei erforderlich

## Preis
Inklusive in der Hausratkasko Plus - keine separate Prämie."""
    },
    {
        "titel": "BaloiseCombi Haushalt",
        "kategorie": "Pakete",
        "inhalt": """# BaloiseCombi Haushalt

## Übersicht
Das Kombi-Paket von Baloise vereint mehrere Versicherungen in einem Vertrag mit attraktiven Paketvorteilen.

## Enthaltene Versicherungen

### Hausratversicherung
- Schutz für Ihr Hab und Gut
- Feuer, Wasser, Einbruch
- Elementarschäden

### Privathaftpflichtversicherung
- Personen- und Sachschäden bis 10 Mio. CHF
- Weltweiter Schutz
- Inklusive Tierhalter-Haftpflicht

### Gebäudeversicherung (optional)
Für Hauseigentümer:
- Feuer und Elementarschäden
- Wasserschäden
- Glasbruch

## Zusatzoptionen

### Reiseversicherung Drive
- Ferienassistance
- Gepäckschutz
- Mietfahrzeugschutz

### Rechtsschutzmodule
- Privatrechtsschutz
- Verkehrsrechtsschutz
- Rechtsschutz für Hauseigentümer

### Spezialdeckungen
- Haftpflicht für Benutzer fremder Motorfahrzeuge
- Reiterhaftpflicht
- Jägerhaftpflicht

## Vorteile des Kombi-Pakets
- Ein Vertrag für alles
- Prämienrabatt durch Bündelung
- Ein Ansprechpartner
- Vereinfachte Administration

## Produktinformationen
Ausgabe 2025 - Aktuelle Vertragsbedingungen unter baloise.ch"""
    },
    {
        "titel": "Baloise Plus Bonusprogramm",
        "kategorie": "Services",
        "inhalt": """# Baloise Plus - Das Bonusprogramm

## Übersicht
Baloise Plus belohnt Ihre Treue. Je mehr Versicherungen Sie bei Baloise haben, desto mehr Vorteile geniessen Sie.

## So funktioniert's
Ergänzen Sie Ihr Baloise Versicherungsportfolio mit weiteren Verträgen und profitieren Sie von kostenlosen Zusatzleistungen.

## Vorteile

### Selbstbehalt-Verzicht
Bei einem Schaden entfällt der Selbstbehalt.
**Beispiel:** Bei einem Schaden von CHF 250 mit CHF 200 Selbstbehalt erhalten Sie normalerweise nur CHF 50. Mit Baloise Plus erhalten Sie die volle Schadenssumme von CHF 250.

### Kostenlose Zusatzleistungen
- Erweiterte Deckungen
- Zusatzservices
- Exklusive Angebote

### Für die ganze Familie
Die Vorteile gelten für alle Familienmitglieder im gleichen Haushalt.

## Teilnahme
- Automatisch mit mehreren Baloise-Verträgen
- Keine separate Anmeldung nötig
- Sofortige Aktivierung der Vorteile

## Partnerangebote
Zusätzliche Vergünstigungen bei ausgewählten Partnern."""
    },
    {
        "titel": "Schadensmeldung - So melden Sie einen Schaden",
        "kategorie": "Services",
        "inhalt": """# Schadensmeldung bei Baloise

## Online Schadensmeldung
Der schnellste Weg: Melden Sie Ihren Schaden online unter baloise.ch oder über die Baloise App.

## Telefonische Meldung
24/7 Schadenhotline: 00800 24 800 800 (kostenlos)

## Benötigte Angaben

### Bei allen Schäden
- Policennummer
- Schadensdatum und -zeit
- Schadensort
- Beschreibung des Hergangs
- Geschätzte Schadenshöhe
- Kontaktdaten

### Bei Fahrzeugschäden zusätzlich
- Fahrzeugkennzeichen
- Angaben zum Unfallgegner (falls vorhanden)
- Polizeirapport-Nummer (falls Polizei involviert)
- Fotos der Schäden

### Bei Einbruch/Diebstahl
- Polizeianzeige (zwingend)
- Liste der entwendeten Gegenstände
- Kaufbelege wenn vorhanden

### Bei Personenschäden
- Ärztliche Berichte
- Arbeitsunfähigkeitszeugnis

## Wichtige Hinweise

### Fristen
- Melden Sie Schäden möglichst sofort
- Spätestens innert 5 Tagen

### Schadensminderung
- Ergreifen Sie zumutbare Massnahmen zur Schadensminderung
- Dokumentieren Sie den Schaden mit Fotos

### Reparaturen
- Warten Sie mit grösseren Reparaturen bis zur Freigabe
- Notmassnahmen sind erlaubt und werden erstattet

## Schadenservice
- Schnelle Bearbeitung innert 48 Stunden
- Persönlicher Schadenberater
- Direktabrechnung mit Partnerwerkstätten
- EasyRepair-Service für Fahrzeugschäden"""
    }
]


def create_knowledge_base_if_not_exists(kb_id: str, name: str, description: str):
    """Erstellt Wissensbasis falls nicht vorhanden"""
    existing = rag_engine.list_knowledge_bases()
    if not any(kb.id == kb_id for kb in existing):
        rag_engine.create_knowledge_base(
            kb_id=kb_id,
            name=name,
            description=description
        )
        print(f"✅ Wissensbasis '{name}' erstellt")
    else:
        print(f"ℹ️  Wissensbasis '{name}' existiert bereits")


def text_to_chunks(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    """Teilt Text in Chunks auf"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        if chunk_text.strip():
            chunks.append(chunk_text)
        start = end - overlap
    return chunks


def import_produkte():
    """Importiert alle Baloise Produkte in die Wissensbasis"""

    # Wissensbasis erstellen
    create_knowledge_base_if_not_exists(
        kb_id="produkte",
        name="Produktinformationen",
        description="Baloise Versicherungsprodukte, Deckungen, Leistungen"
    )

    print(f"\n📥 Importiere {len(BALOISE_PRODUKTE)} Produkte...\n")

    total_chunks = 0

    for i, produkt in enumerate(BALOISE_PRODUKTE, 1):
        titel = produkt["titel"]
        kategorie = produkt["kategorie"]
        inhalt = produkt["inhalt"]

        print(f"[{i}/{len(BALOISE_PRODUKTE)}] {titel}...")

        try:
            # Text in Chunks aufteilen
            chunk_texts = text_to_chunks(inhalt)
            doc_id = str(uuid.uuid4())[:8]

            # DocumentChunk-Objekte erstellen
            chunks = []
            for j, chunk_text in enumerate(chunk_texts):
                chunk = DocumentChunk(
                    id=f"{doc_id}_{j}",
                    content=chunk_text,
                    metadata={
                        "knowledge_base": "produkte",
                        "filename": f"{titel.lower().replace(' ', '_')}.md",
                        "titel": titel,
                        "kategorie": kategorie,
                        "quelle": "baloise.ch",
                        "chunk_index": j
                    }
                )
                chunks.append(chunk)

            # ProcessedDocument erstellen
            doc = ProcessedDocument(
                id=doc_id,
                filename=f"{titel.lower().replace(' ', '_')}.md",
                file_type="text/markdown",
                chunks=chunks,
                metadata={
                    "knowledge_base": "produkte",
                    "titel": titel,
                    "kategorie": kategorie,
                    "quelle": "baloise.ch",
                    "stand": datetime.now().strftime("%Y-%m-%d")
                },
                raw_text=inhalt
            )

            # In ChromaDB indexieren
            result = rag_engine.add_document(doc)

            if result.get("openai") or result.get("local"):
                print(f"   ✅ {len(chunks)} Chunks indexiert")
                total_chunks += len(chunks)
            else:
                print(f"   ⚠️  Keine Embeddings erstellt (API-Key prüfen)")

        except Exception as e:
            print(f"   ❌ Fehler: {e}")

    print(f"\n✅ Import abgeschlossen!")
    print(f"📊 Total: {total_chunks} Chunks indexiert")


if __name__ == "__main__":
    print("=" * 50)
    print("Baloise Produktinformationen Import")
    print("=" * 50)
    import_produkte()
