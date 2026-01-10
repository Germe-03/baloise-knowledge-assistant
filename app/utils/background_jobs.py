"""
KMU Knowledge Assistant - Background Job Manager
Führt Scraping-Jobs im Hintergrund aus
"""

import json
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

from app.config import DATA_DIR


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundJob:
    """Ein Hintergrund-Job"""
    id: str
    type: str  # "scraping", "indexing", etc.
    title: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0  # 0.0 - 1.0
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    params: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "params": self.params
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BackgroundJob":
        data["status"] = JobStatus(data.get("status", "pending"))
        return cls(**data)


class BackgroundJobManager:
    """Manager für Hintergrund-Jobs"""

    def __init__(self):
        self.jobs: Dict[str, BackgroundJob] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.jobs_file = DATA_DIR / "background_jobs.json"
        self._lock = threading.Lock()
        self._load_jobs()

    def _load_jobs(self):
        """Lädt Jobs aus Datei"""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job_data in data:
                        job = BackgroundJob.from_dict(job_data)
                        # Laufende Jobs als fehlgeschlagen markieren (nach Neustart)
                        if job.status == JobStatus.RUNNING:
                            job.status = JobStatus.FAILED
                            job.error = "Server wurde neu gestartet"
                        self.jobs[job.id] = job
            except Exception as e:
                print(f"Fehler beim Laden der Jobs: {e}")

    def _save_jobs(self):
        """Speichert Jobs in Datei"""
        try:
            with self._lock:
                jobs_data = [job.to_dict() for job in self.jobs.values()]
                with open(self.jobs_file, 'w', encoding='utf-8') as f:
                    json.dump(jobs_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Jobs: {e}")

    def create_job(
        self,
        job_id: str,
        job_type: str,
        title: str,
        params: Dict = None
    ) -> BackgroundJob:
        """Erstellt einen neuen Job"""
        job = BackgroundJob(
            id=job_id,
            type=job_type,
            title=title,
            params=params or {}
        )
        self.jobs[job_id] = job
        self._save_jobs()
        return job

    def start_job(
        self,
        job_id: str,
        worker_func: Callable,
        *args,
        **kwargs
    ):
        """Startet einen Job im Hintergrund"""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} existiert nicht")

        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()
        job.message = "Wird gestartet..."
        self._save_jobs()

        def run_worker():
            try:
                result = worker_func(job, *args, **kwargs)
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                job.result = result
                job.completed_at = datetime.now().isoformat()
                job.message = "Abgeschlossen"
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.now().isoformat()
                job.message = f"Fehler: {e}"
            finally:
                self._save_jobs()

        thread = threading.Thread(target=run_worker, daemon=True)
        self.threads[job_id] = thread
        thread.start()

    def update_progress(
        self,
        job_id: str,
        progress: float,
        message: str = ""
    ):
        """Aktualisiert den Fortschritt eines Jobs"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.progress = min(max(progress, 0.0), 1.0)
            if message:
                job.message = message
            self._save_jobs()

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Holt einen Job"""
        return self.jobs.get(job_id)

    def get_all_jobs(self, job_type: str = None) -> List[BackgroundJob]:
        """Holt alle Jobs (optional gefiltert nach Typ)"""
        jobs = list(self.jobs.values())
        if job_type:
            jobs = [j for j in jobs if j.type == job_type]
        # Nach Erstellungsdatum sortieren (neueste zuerst)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return jobs

    def get_active_jobs(self, job_type: str = None) -> List[BackgroundJob]:
        """Holt alle laufenden Jobs"""
        jobs = self.get_all_jobs(job_type)
        return [j for j in jobs if j.status in (JobStatus.PENDING, JobStatus.RUNNING)]

    def cancel_job(self, job_id: str) -> bool:
        """Bricht einen Job ab (nur Status-Änderung)"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                job.status = JobStatus.CANCELLED
                job.message = "Abgebrochen"
                job.completed_at = datetime.now().isoformat()
                self._save_jobs()
                return True
        return False

    def delete_job(self, job_id: str) -> bool:
        """Löscht einen Job"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            return True
        return False

    def cleanup_old_jobs(self, days: int = 7):
        """Löscht alte abgeschlossene Jobs"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        to_delete = []

        for job_id, job in self.jobs.items():
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                try:
                    job_time = datetime.fromisoformat(job.created_at).timestamp()
                    if job_time < cutoff:
                        to_delete.append(job_id)
                except:
                    pass

        for job_id in to_delete:
            del self.jobs[job_id]

        if to_delete:
            self._save_jobs()

        return len(to_delete)


# Singleton Instanz
job_manager = BackgroundJobManager()
