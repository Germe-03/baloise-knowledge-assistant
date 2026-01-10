"""
KMU Knowledge Assistant - File Handlers
Hilfsfunktionen für Dateiverarbeitung
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple, BinaryIO
from datetime import datetime
import mimetypes

from app.config import (
    UPLOADS_DIR, 
    KNOWLEDGE_BASES_DIR, 
    ALL_EXTENSIONS,
    SUPPORTED_FORMATS
)


def get_file_extension(filename: str) -> str:
    """Gibt die Dateierweiterung zurück (lowercase)"""
    return Path(filename).suffix.lower()


def is_supported_file(filename: str) -> bool:
    """Prüft ob Dateiformat unterstützt wird"""
    ext = get_file_extension(filename)
    return ext in ALL_EXTENSIONS


def get_file_category(filename: str) -> Optional[str]:
    """Gibt die Kategorie einer Datei zurück"""
    ext = get_file_extension(filename)
    for category, info in SUPPORTED_FORMATS.items():
        if ext in info["extensions"]:
            return category
    return None


def get_mime_type(filename: str) -> str:
    """Ermittelt MIME-Type einer Datei"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def save_uploaded_file(
    file_content: bytes,
    filename: str,
    subdirectory: Optional[str] = None
) -> Path:
    """Speichert eine hochgeladene Datei"""
    if subdirectory:
        target_dir = UPLOADS_DIR / subdirectory
    else:
        target_dir = UPLOADS_DIR
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Eindeutigen Dateinamen generieren falls vorhanden
    target_path = target_dir / filename
    if target_path.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    
    target_path.write_bytes(file_content)
    return target_path


def list_uploaded_files(subdirectory: Optional[str] = None) -> List[dict]:
    """Listet hochgeladene Dateien"""
    if subdirectory:
        target_dir = UPLOADS_DIR / subdirectory
    else:
        target_dir = UPLOADS_DIR
    
    if not target_dir.exists():
        return []
    
    files = []
    for file_path in target_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith('.'):
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "size_human": format_file_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "category": get_file_category(file_path.name),
                "supported": is_supported_file(file_path.name)
            })
    
    return sorted(files, key=lambda x: x["modified"], reverse=True)


def delete_uploaded_file(filename: str, subdirectory: Optional[str] = None) -> bool:
    """Löscht eine hochgeladene Datei"""
    if subdirectory:
        target_path = UPLOADS_DIR / subdirectory / filename
    else:
        target_path = UPLOADS_DIR / filename
    
    if target_path.exists():
        target_path.unlink()
        return True
    return False


def format_file_size(size_bytes: int) -> str:
    """Formatiert Dateigröße menschenlesbar"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def create_knowledge_base_export(kb_id: str, output_path: Path) -> Path:
    """Erstellt ZIP-Export einer Wissensbank"""
    # Hier würden wir die Dokumente und Embeddings exportieren
    # Für MVP: Einfacher ZIP der zugehörigen Dateien
    
    export_dir = KNOWLEDGE_BASES_DIR / kb_id
    if not export_dir.exists():
        raise FileNotFoundError(f"Wissensbank nicht gefunden: {kb_id}")
    
    zip_path = output_path / f"{kb_id}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in export_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(export_dir)
                zipf.write(file_path, arcname)
    
    return zip_path


def import_knowledge_base_export(zip_path: Path, kb_id: str) -> int:
    """Importiert ZIP-Export in eine Wissensbank"""
    target_dir = KNOWLEDGE_BASES_DIR / kb_id
    target_dir.mkdir(parents=True, exist_ok=True)
    
    file_count = 0
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for file_info in zipf.filelist:
            if not file_info.is_dir():
                zipf.extract(file_info, target_dir)
                file_count += 1
    
    return file_count


def scan_directory_for_documents(
    directory: Path,
    recursive: bool = True
) -> List[Path]:
    """Scannt Verzeichnis nach unterstützten Dokumenten"""
    documents = []
    
    if recursive:
        iterator = directory.rglob('*')
    else:
        iterator = directory.glob('*')
    
    for file_path in iterator:
        if file_path.is_file() and is_supported_file(file_path.name):
            documents.append(file_path)
    
    return sorted(documents)


def cleanup_temp_files(max_age_hours: int = 24):
    """Bereinigt temporäre Dateien älter als max_age_hours"""
    temp_dir = UPLOADS_DIR / "temp"
    if not temp_dir.exists():
        return 0
    
    cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
    deleted_count = 0
    
    for file_path in temp_dir.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff:
            file_path.unlink()
            deleted_count += 1
    
    return deleted_count


def get_storage_stats() -> dict:
    """Gibt Speicherstatistiken zurück"""
    def get_dir_size(path: Path) -> int:
        total = 0
        if path.exists():
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total += file_path.stat().st_size
        return total
    
    uploads_size = get_dir_size(UPLOADS_DIR)
    kb_size = get_dir_size(KNOWLEDGE_BASES_DIR)
    
    return {
        "uploads": {
            "size_bytes": uploads_size,
            "size_human": format_file_size(uploads_size),
            "file_count": sum(1 for _ in UPLOADS_DIR.rglob('*') if _.is_file()) if UPLOADS_DIR.exists() else 0
        },
        "knowledge_bases": {
            "size_bytes": kb_size,
            "size_human": format_file_size(kb_size),
            "file_count": sum(1 for _ in KNOWLEDGE_BASES_DIR.rglob('*') if _.is_file()) if KNOWLEDGE_BASES_DIR.exists() else 0
        },
        "total": {
            "size_bytes": uploads_size + kb_size,
            "size_human": format_file_size(uploads_size + kb_size)
        }
    }
