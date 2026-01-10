"""
KMU Knowledge Assistant - Web Scraper
Automatische Wissenssammlung aus Webquellen
Mit PDF/DOCX-Download und -Verarbeitung
"""

import time
import re
import hashlib
import tempfile
import random
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from app.config import config, KNOWLEDGE_BASES_DIR, UPLOADS_DIR

# Unterstützte Dokumenttypen für Download
SUPPORTED_DOC_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.xlsx', '.csv'}

# URL-Muster die auf Spider Traps hindeuten
TRAP_PATTERNS = [
    # Kalender-URLs
    r'/calendar[/-]',
    r'/kalender[/-]',
    r'/\d{4}/\d{2}/\d{2}',  # /2024/01/15
    r'/\d{4}-\d{2}-\d{2}',  # /2024-01-15
    r'/date[/-]\d',
    r'/datum[/-]',
    r'/termine[/-]\d',
    r'/events[/-]\d{4}',

    # Paginierung
    r'[?&]page=\d+',
    r'[?&]seite=\d+',
    r'[?&]p=\d+',
    r'[?&]offset=\d+',
    r'[?&]start=\d+',
    r'/page/\d+',
    r'/seite/\d+',

    # Archive
    r'/archiv[/-]\d',
    r'/archive[/-]\d',
    r'/news[/-]\d{4}',
    r'/blog[/-]\d{4}',
    r'/artikel[/-]\d{4}',

    # CMS-Detail-Seiten (Schweizer Gemeinde-Websites)
    r'/news/\d+',           # /news/4684
    r'/event/\d+',          # /event/3065
    r'/eventdate/\d+',      # /eventdate/7661
    r'/detailseite[^/]*/\d+/news/\d+',  # /aktuelles-detailseite.html/476/news/4684
    r'/veranstaltungen[^/]*/\d+/event', # Veranstaltungs-Details
    r'\.html/\d+/news/',    # CMS-Pattern mit IDs
    r'\.html/\d+/event/',   # Event-Details

    # Session/Tracking
    r'[?&]sid=',
    r'[?&]session',
    r'[?&]utm_',
    r'[?&]fbclid=',
    r'[?&]gclid=',

    # Sortierung/Filter (erzeugen viele Varianten)
    r'[?&]sort=',
    r'[?&]order=',
    r'[?&]filter=',

    # Login/Admin
    r'/login',
    r'/logout',
    r'/admin',
    r'/wp-admin',
    r'/user/',
    r'/profil/',
]

# Kompilierte Regex für Performance
import re as regex_module
TRAP_REGEX = regex_module.compile('|'.join(TRAP_PATTERNS), regex_module.IGNORECASE)


@dataclass
class ScrapedPage:
    """Eine gescrapte Webseite"""
    url: str
    title: str
    content: str
    links: List[str] = field(default_factory=list)
    doc_links: List[str] = field(default_factory=list)  # PDF/DOCX Links
    scraped_at: datetime = field(default_factory=datetime.now)

    @property
    def content_hash(self) -> str:
        """SHA256-Hash des Inhalts für Change-Detection"""
        return hashlib.sha256(self.content.encode()).hexdigest()

    @property
    def filename(self) -> str:
        """Generiert sicheren Dateinamen"""
        url_hash = hashlib.md5(self.url.encode()).hexdigest()[:8]
        safe_title = re.sub(r'[^\w\s-]', '', self.title)[:50]
        return f"{safe_title}_{url_hash}.txt"


@dataclass
class DownloadedDocument:
    """Ein heruntergeladenes Dokument (PDF, DOCX, etc.)"""
    url: str
    filename: str
    file_path: Path
    file_type: str
    file_size: int
    downloaded_at: datetime = field(default_factory=datetime.now)


@dataclass
class ScrapingJob:
    """Scraping-Auftrag"""
    id: str
    topic: str
    start_urls: List[str]
    max_depth: int
    max_pages: int
    status: str = "pending"
    pages_scraped: int = 0
    pages_found: int = 0  # Gesamtzahl gefundener Seiten (in Queue)
    docs_downloaded: int = 0
    docs_found: int = 0  # Gesamtzahl gefundener Dokumente
    download_documents: bool = True  # PDFs/DOCXs herunterladen?
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: List[ScrapedPage] = field(default_factory=list)
    remaining_urls: List[str] = field(default_factory=list)  # URLs die nicht gescrapt wurden
    remaining_doc_urls: List[str] = field(default_factory=list)  # Dokumente die nicht heruntergeladen wurden
    downloaded_docs: List[DownloadedDocument] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class WebScraper:
    """Web Scraper für automatische Wissenssammlung"""

    def __init__(self):
        self.config = config.scraping
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": self.config.user_agent}
        )

    def _is_trap_url(self, url: str) -> bool:
        """Prüft ob URL ein Spider Trap ist (Kalender, Paginierung, etc.)"""
        return bool(TRAP_REGEX.search(url))

    def _is_same_domain(self, url: str, base_domain: str) -> bool:
        """Prüft ob URL zur gleichen Domain gehört"""
        parsed = urlparse(url)
        url_domain = parsed.netloc.lower().replace('www.', '')
        base = base_domain.lower().replace('www.', '')
        return url_domain == base or url_domain.endswith('.' + base)

    def _can_scrape(self, url: str) -> bool:
        """Prüft ob URL gescrapt werden darf (robots.txt)"""
        if not self.config.respect_robots_txt:
            return True
        
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            response = self.client.get(robots_url)
            if response.status_code != 200:
                return True  # Kein robots.txt = erlaubt
            
            # Einfache robots.txt Analyse
            robots_content = response.text.lower()
            user_agent_section = False
            
            for line in robots_content.split('\n'):
                line = line.strip()
                if line.startswith('user-agent:'):
                    agent = line.split(':', 1)[1].strip()
                    user_agent_section = agent == '*' or 's&p' in agent.lower()
                elif user_agent_section and line.startswith('disallow:'):
                    path = line.split(':', 1)[1].strip()
                    if path and parsed.path.startswith(path):
                        return False
            
            return True
        except Exception:
            return True  # Im Zweifel erlauben
    
    def _extract_content(self, html: str, url: str) -> ScrapedPage:
        """Extrahiert Inhalt aus HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Unerwünschte Elemente entfernen
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        # Titel extrahieren
        title = ""
        if soup.title:
            title = soup.title.string or ""
        elif soup.h1:
            title = soup.h1.get_text(strip=True)
        else:
            title = urlparse(url).path.split('/')[-1] or "Untitled"
        
        # Hauptinhalt extrahieren
        main_content = soup.find('main') or soup.find('article') or soup.body
        if main_content:
            content = main_content.get_text(separator='\n', strip=True)
        else:
            content = soup.get_text(separator='\n', strip=True)
        
        # Links extrahieren
        links = []
        doc_links = []
        base_domain = urlparse(url).netloc

        for a in soup.find_all('a', href=True):
            href = a['href']
            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)

            # Nur HTTP(S)-Links
            if parsed.scheme not in ('http', 'https'):
                continue

            path_lower = parsed.path.lower()

            # Spider Trap Check - Kalender, Paginierung, Archive überspringen
            if self._is_trap_url(absolute_url):
                continue

            # Nur gleiche Domain folgen (verhindert Ausbreitung)
            if not self._is_same_domain(absolute_url, base_domain):
                continue

            # Dokument-Links (PDF, DOCX, etc.) separat sammeln
            if any(path_lower.endswith(ext) for ext in SUPPORTED_DOC_EXTENSIONS):
                if absolute_url not in doc_links:
                    doc_links.append(absolute_url)
            # Keine ZIP, EXE oder Anker-Links
            elif not any(ext in path_lower for ext in ['.zip', '.exe', '.tar', '.gz']):
                if absolute_url not in links:
                    links.append(absolute_url)

        return ScrapedPage(
            url=url,
            title=title,
            content=content,
            links=links,
            doc_links=doc_links
        )
    
    def scrape_url(self, url: str, max_retries: int = 3) -> Optional[ScrapedPage]:
        """
        Scrapt eine einzelne URL mit Exponential Backoff.

        Args:
            url: Die zu scrapende URL
            max_retries: Maximale Anzahl Wiederholungsversuche

        Returns:
            ScrapedPage oder None bei Fehler
        """
        if not self._can_scrape(url):
            return None

        for attempt in range(max_retries):
            try:
                response = self.client.get(url)
                response.raise_for_status()

                # Nur HTML verarbeiten
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type:
                    return None

                return self._extract_content(response.text, url)

            except Exception as e:
                # Exponential Backoff mit Jitter
                if attempt < max_retries - 1:
                    # Basis: 2^attempt Sekunden + zufälliger Jitter (0-1 Sek)
                    wait_time = (2 ** attempt) + random.random()
                    print(f"Retry {attempt + 1}/{max_retries} für {url} in {wait_time:.1f}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"Fehler beim Scrapen von {url} nach {max_retries} Versuchen: {e}")

        return None

    def download_document(self, url: str, output_dir: Path) -> Optional[DownloadedDocument]:
        """
        Lädt ein Dokument (PDF, DOCX, etc.) herunter.

        Args:
            url: URL des Dokuments
            output_dir: Zielverzeichnis

        Returns:
            DownloadedDocument oder None bei Fehler
        """
        try:
            # Dateiname aus URL extrahieren
            parsed = urlparse(url)
            original_filename = Path(parsed.path).name
            if not original_filename:
                original_filename = f"document_{hashlib.md5(url.encode()).hexdigest()[:8]}"

            # Dateiendung ermitteln
            file_ext = Path(original_filename).suffix.lower()
            if file_ext not in SUPPORTED_DOC_EXTENSIONS:
                return None

            # Eindeutigen Dateinamen generieren
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            safe_filename = re.sub(r'[^\w\s.-]', '', original_filename)
            final_filename = f"{Path(safe_filename).stem}_{url_hash}{file_ext}"

            output_path = output_dir / final_filename

            # Download mit Streaming für grosse Dateien
            with self.client.stream("GET", url) as response:
                response.raise_for_status()

                # Content-Type prüfen
                content_type = response.headers.get('content-type', '').lower()

                # Maximale Dateigrösse (50MB)
                content_length = int(response.headers.get('content-length', 0))
                if content_length > 50 * 1024 * 1024:
                    print(f"Datei zu gross: {url} ({content_length} bytes)")
                    return None

                # Datei schreiben
                output_dir.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

            file_size = output_path.stat().st_size

            return DownloadedDocument(
                url=url,
                filename=final_filename,
                file_path=output_path,
                file_type=file_ext,
                file_size=file_size
            )

        except Exception as e:
            print(f"Fehler beim Download von {url}: {e}")
            return None

    def scrape_topic(
        self,
        topic: str,
        start_urls: List[str],
        max_depth: int = None,
        max_pages: int = None,
        download_documents: bool = True,
        max_documents: int = 50,
        callback=None
    ) -> ScrapingJob:
        """
        Scrapt Seiten zu einem Thema und lädt optional Dokumente herunter.

        Args:
            topic: Thema/Name des Scraping-Jobs
            start_urls: Start-URLs
            max_depth: Maximale Crawl-Tiefe
            max_pages: Maximale Anzahl Seiten
            download_documents: PDFs/DOCXs herunterladen?
            max_documents: Maximale Anzahl Dokumente
            callback: Progress-Callback

        Returns:
            ScrapingJob mit Ergebnissen
        """
        if max_depth is None:
            max_depth = self.config.max_depth
        if max_pages is None:
            max_pages = self.config.max_pages

        job_id = hashlib.md5(f"{topic}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        # Ausgabeverzeichnis für Dokumente
        docs_output_dir = UPLOADS_DIR / f"scrape_{job_id}"

        job = ScrapingJob(
            id=job_id,
            topic=topic,
            start_urls=start_urls,
            max_depth=max_depth,
            max_pages=max_pages,
            download_documents=download_documents,
            status="running",
            started_at=datetime.now()
        )

        visited: Set[str] = set()
        visited_docs: Set[str] = set()
        all_found_urls: Set[str] = set(start_urls)  # Alle gefundenen URLs
        all_found_docs: Set[str] = set()  # Alle gefundenen Dokumente
        to_visit: List[tuple] = [(url, 0) for url in start_urls]  # (url, depth)

        job.pages_found = len(start_urls)

        while to_visit and len(job.results) < max_pages:
            url, depth = to_visit.pop(0)

            # Normalisiere URL
            parsed = urlparse(url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if normalized_url in visited:
                continue

            visited.add(normalized_url)

            # Callback für Progress
            if callback:
                callback(job)

            # Scrape
            page = self.scrape_url(url)

            if page:
                job.results.append(page)
                job.pages_scraped = len(job.results)

                # Dokument-Links zählen (auch wenn nicht heruntergeladen)
                for doc_url in page.doc_links:
                    if doc_url not in all_found_docs:
                        all_found_docs.add(doc_url)
                        job.docs_found = len(all_found_docs)

                # Dokumente herunterladen (wenn aktiviert)
                if download_documents and len(job.downloaded_docs) < max_documents:
                    for doc_url in page.doc_links:
                        if doc_url not in visited_docs and len(job.downloaded_docs) < max_documents:
                            visited_docs.add(doc_url)
                            doc = self.download_document(doc_url, docs_output_dir)
                            if doc:
                                job.downloaded_docs.append(doc)
                                job.docs_downloaded = len(job.downloaded_docs)
                                if callback:
                                    callback(job)

                # Links für nächste Ebene hinzufügen
                if depth < max_depth:
                    for link in page.links:
                        if link not in visited and link not in all_found_urls:
                            all_found_urls.add(link)
                            to_visit.append((link, depth + 1))
                            job.pages_found = len(all_found_urls)

            # Rate Limiting mit Jitter (verhindert Pattern-Erkennung)
            jitter = random.random() * 0.5  # 0-0.5 Sekunden zusätzlich
            time.sleep(self.config.rate_limit_seconds + jitter)

        # Restliche URLs speichern (für "Weiter scrapen" Feature)
        job.remaining_urls = [url for url, depth in to_visit if url not in visited]
        job.remaining_doc_urls = [url for url in all_found_docs if url not in visited_docs]

        job.status = "completed"
        job.completed_at = datetime.now()

        return job
    
    def save_job_results(self, job: ScrapingJob, output_dir: Path = None) -> List[Path]:
        """Speichert Scraping-Ergebnisse als Dateien"""
        if output_dir is None:
            output_dir = KNOWLEDGE_BASES_DIR / f"scrape_{job.id}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        for page in job.results:
            file_path = output_dir / page.filename

            content = f"""URL: {page.url}
Titel: {page.title}
Gescrapt am: {page.scraped_at.isoformat()}
Content-Hash: {page.content_hash}

---

{page.content}
"""

            file_path.write_text(content, encoding='utf-8')
            saved_files.append(file_path)
        
        # Übersichtsdatei
        summary_path = output_dir / "_summary.txt"
        summary = f"""Scraping-Job: {job.id}
Thema: {job.topic}
Start-URLs: {', '.join(job.start_urls)}
Gescrapte Seiten: {job.pages_scraped}
Gestartet: {job.started_at}
Beendet: {job.completed_at}

Dateien:
"""
        for f in saved_files:
            summary += f"- {f.name}\n"
        
        summary_path.write_text(summary, encoding='utf-8')
        
        return saved_files
    
    def close(self):
        """Schließt HTTP-Client"""
        self.client.close()


# Vordefinierte Quellen für Schweizer Behörden
SWISS_SOURCES = {
    "bundesrecht": [
        "https://www.fedlex.admin.ch/de/home",
        "https://www.admin.ch/gov/de/start.html"
    ],
    "gemeinden_zh": [
        "https://www.zh.ch/de/gemeinden.html"
    ],
    "bildung": [
        "https://www.zh.ch/de/bildung.html",
        "https://www.sbfi.admin.ch/sbfi/de/home.html"
    ],
    "finanzen_hrm2": [
        "https://www.srs-cspcp.ch/de/"
    ]
}


# Globale Instanz
web_scraper = WebScraper()
