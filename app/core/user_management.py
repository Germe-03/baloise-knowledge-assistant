"""
KMU Knowledge Assistant - User Management & Audit System
Muster KMU, Volketswil

DSG-konforme Benutzerverwaltung mit vollständigem Audit-Log
"""

import json
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path


class UserRole(Enum):
    """Benutzerrollen für Gemeindeverwaltung"""
    ADMIN = "admin"                        # Vollzugriff, System-Konfiguration
    ABTEILUNGSLEITER = "abteilungsleiter"  # Wissensbasen verwalten, Berichte
    SACHBEARBEITER = "sachbearbeiter"      # Chat, Upload, Suche
    LESEZUGRIFF = "lesezugriff"            # Nur Chat und Suche


class Department(Enum):
    """Standard-Abteilungen (erweiterbar über DepartmentManager)"""
    ALLGEMEIN = "allgemein"
    PERSONAL = "personal"
    FINANZEN = "finanzen"
    BAUAMT = "bauamt"
    EINWOHNERDIENSTE = "einwohnerdienste"
    SOZIALES = "soziales"
    BILDUNG = "bildung"
    IT = "it"


@dataclass
class CustomDepartment:
    """Benutzerdefinierte Abteilung"""
    id: str
    name: str
    description: str = ""
    allowed_knowledge_bases: List[str] = field(default_factory=list)  # KB-IDs
    created_at: str = ""
    is_active: bool = True


@dataclass
class User:
    """Benutzer-Modell"""
    id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    department: Department
    display_name: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    # Personalinfo
    first_name: str = ""
    last_name: str = ""
    phone: str = ""

    # Berechtigungen
    allowed_knowledge_bases: List[str] = field(default_factory=list)  # Leer = alle
    departments: List[str] = field(default_factory=list)  # Mehrere Abteilungen möglich
    can_upload: bool = True
    can_create_kb: bool = False
    can_scrape: bool = False
    can_manage_users: bool = False
    can_view_audit: bool = False

    # TODO: 2FA Implementation (Phase 2)
    # two_factor_enabled: bool = False
    # two_factor_secret: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary (ohne Passwort)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "department": self.department.value,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "allowed_knowledge_bases": self.allowed_knowledge_bases,
            "departments": self.departments,
            "can_upload": self.can_upload,
            "can_create_kb": self.can_create_kb,
            "can_scrape": self.can_scrape,
            "can_manage_users": self.can_manage_users,
            "can_view_audit": self.can_view_audit
        }


@dataclass
class AuditLogEntry:
    """Audit-Log Eintrag für DSG-Compliance"""
    id: str
    timestamp: datetime
    user_id: str
    username: str
    department: str
    action: str  # z.B. "chat_query", "document_upload", "kb_create", "search", "login"
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    
    # Für Chat-Queries
    query: Optional[str] = None
    response_summary: Optional[str] = None  # Erste 200 Zeichen
    knowledge_bases_used: List[str] = field(default_factory=list)
    
    # Für Dokument-Operationen
    document_name: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "username": self.username,
            "department": self.department,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "query": self.query,
            "response_summary": self.response_summary,
            "knowledge_bases_used": self.knowledge_bases_used,
            "document_name": self.document_name,
            "knowledge_base_id": self.knowledge_base_id
        }


class UserManager:
    """Benutzerverwaltung mit Persistenz"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.users_dir = data_dir / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.users_dir / "users.json"
        self.users: Dict[str, User] = {}
        self._load_users()
        self._ensure_default_admin()
    
    def _load_users(self):
        """Lädt Benutzer aus JSON-Datei"""
        if self.users_file.exists():
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_data in data:
                        user = User(
                            id=user_data["id"],
                            username=user_data["username"],
                            email=user_data.get("email", ""),
                            password_hash=user_data["password_hash"],
                            role=UserRole(user_data["role"]),
                            department=Department(user_data.get("department", "allgemein")),
                            display_name=user_data["display_name"],
                            is_active=user_data.get("is_active", True),
                            created_at=datetime.fromisoformat(user_data["created_at"]) if user_data.get("created_at") else datetime.now(),
                            last_login=datetime.fromisoformat(user_data["last_login"]) if user_data.get("last_login") else None,
                            first_name=user_data.get("first_name", ""),
                            last_name=user_data.get("last_name", ""),
                            phone=user_data.get("phone", ""),
                            allowed_knowledge_bases=user_data.get("allowed_knowledge_bases", []),
                            departments=user_data.get("departments", []),
                            can_upload=user_data.get("can_upload", True),
                            can_create_kb=user_data.get("can_create_kb", False),
                            can_scrape=user_data.get("can_scrape", False),
                            can_manage_users=user_data.get("can_manage_users", False),
                            can_view_audit=user_data.get("can_view_audit", False)
                        )
                        self.users[user.id] = user
            except Exception as e:
                print(f"Fehler beim Laden der Benutzer: {e}")
    
    def _save_users(self):
        """Speichert Benutzer in JSON-Datei"""
        data = []
        for user in self.users.values():
            data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "password_hash": user.password_hash,
                "role": user.role.value,
                "department": user.department.value,
                "display_name": user.display_name,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "allowed_knowledge_bases": user.allowed_knowledge_bases,
                "departments": user.departments,
                "can_upload": user.can_upload,
                "can_create_kb": user.can_create_kb,
                "can_scrape": user.can_scrape,
                "can_manage_users": user.can_manage_users,
                "can_view_audit": user.can_view_audit
            })

        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _ensure_default_admin(self):
        """Erstellt Standard-Admin falls keine Benutzer existieren"""
        if not self.users:
            self.create_user(
                username="admin",
                email="admin@muster-kmu.ch",
                password="admin123",  # Sollte beim ersten Login geändert werden!
                role=UserRole.ADMIN,
                department=Department.IT,
                display_name="Administrator"
            )
            print("Standard-Admin erstellt (admin/admin123) - Bitte Passwort ändern!")
    
    def _hash_password(self, password: str) -> str:
        """Hasht Passwort mit Salt"""
        salt = "sp_knowledge_2024"  # In Produktion: zufälliger Salt pro User
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole,
        department: Department,
        display_name: str,
        first_name: str = "",
        last_name: str = "",
        phone: str = "",
        allowed_knowledge_bases: Optional[List[str]] = None,
        departments: Optional[List[str]] = None
    ) -> User:
        """Erstellt neuen Benutzer"""
        # Prüfen ob Username bereits existiert
        for user in self.users.values():
            if user.username.lower() == username.lower():
                raise ValueError(f"Benutzername '{username}' existiert bereits")

        user_id = secrets.token_hex(8)
        password_hash = self._hash_password(password)

        # Berechtigungen basierend auf Rolle
        can_create_kb = role in [UserRole.ADMIN, UserRole.ABTEILUNGSLEITER]
        can_scrape = role == UserRole.ADMIN
        can_manage_users = role == UserRole.ADMIN
        can_view_audit = role in [UserRole.ADMIN, UserRole.ABTEILUNGSLEITER]
        can_upload = role != UserRole.LESEZUGRIFF

        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            department=department,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            allowed_knowledge_bases=allowed_knowledge_bases or [],
            departments=departments or [department.value],
            can_upload=can_upload,
            can_create_kb=can_create_kb,
            can_scrape=can_scrape,
            can_manage_users=can_manage_users,
            can_view_audit=can_view_audit
        )

        self.users[user.id] = user
        self._save_users()
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authentifiziert Benutzer"""
        password_hash = self._hash_password(password)
        
        for user in self.users.values():
            if user.username.lower() == username.lower() and user.password_hash == password_hash:
                if user.is_active:
                    user.last_login = datetime.now()
                    self._save_users()
                    return user
                else:
                    return None  # Benutzer deaktiviert
        return None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Holt Benutzer nach ID"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Holt Benutzer nach Username"""
        for user in self.users.values():
            if user.username.lower() == username.lower():
                return user
        return None
    
    def list_users(self, include_inactive: bool = False) -> List[User]:
        """Listet alle Benutzer"""
        users = list(self.users.values())
        if not include_inactive:
            users = [u for u in users if u.is_active]
        return sorted(users, key=lambda u: u.display_name)
    
    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Aktualisiert Benutzer"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and key != "id" and key != "password_hash":
                if key == "role":
                    value = UserRole(value) if isinstance(value, str) else value
                elif key == "department":
                    value = Department(value) if isinstance(value, str) else value
                setattr(user, key, value)
        
        self._save_users()
        return user
    
    def change_password(self, user_id: str, new_password: str) -> bool:
        """Ändert Passwort"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.password_hash = self._hash_password(new_password)
        self._save_users()
        return True
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deaktiviert Benutzer (statt löschen)"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.is_active = False
        self._save_users()
        return True
    
    def can_access_knowledge_base(self, user: User, kb_id: str) -> bool:
        """Prüft Zugriffsberechtigung auf Wissensbank"""
        if user.role == UserRole.ADMIN:
            return True
        if not user.allowed_knowledge_bases:  # Leer = alle
            return True
        return kb_id in user.allowed_knowledge_bases


class AuditLogger:
    """Audit-Logging für DSG-Compliance"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.log_dir = data_dir / "audit_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self, date: datetime) -> Path:
        """Gibt Log-Datei für Datum zurück (täglich rotiert)"""
        return self.log_dir / f"audit_{date.strftime('%Y-%m-%d')}.jsonl"
    
    def log(
        self,
        user: User,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        response_summary: Optional[str] = None,
        knowledge_bases_used: Optional[List[str]] = None,
        document_name: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Schreibt Audit-Log Eintrag"""
        entry = AuditLogEntry(
            id=secrets.token_hex(8),
            timestamp=datetime.now(),
            user_id=user.id,
            username=user.username,
            department=user.department.value,
            action=action,
            details=details or {},
            ip_address=ip_address,
            query=query,
            response_summary=response_summary[:200] if response_summary else None,
            knowledge_bases_used=knowledge_bases_used or [],
            document_name=document_name,
            knowledge_base_id=knowledge_base_id
        )
        
        log_file = self._get_log_file(entry.timestamp)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
    
    def log_login(self, user: User, success: bool, ip_address: Optional[str] = None):
        """Loggt Login-Versuch"""
        self.log(
            user=user,
            action="login_success" if success else "login_failed",
            details={"success": success},
            ip_address=ip_address
        )
    
    def log_chat(
        self,
        user: User,
        query: str,
        response: str,
        knowledge_bases: List[str],
        provider: str
    ):
        """Loggt Chat-Anfrage"""
        self.log(
            user=user,
            action="chat_query",
            details={"provider": provider},
            query=query,
            response_summary=response,
            knowledge_bases_used=knowledge_bases
        )
    
    def log_upload(
        self,
        user: User,
        filename: str,
        kb_id: str,
        success: bool
    ):
        """Loggt Dokument-Upload"""
        self.log(
            user=user,
            action="document_upload",
            details={"success": success},
            document_name=filename,
            knowledge_base_id=kb_id
        )
    
    def log_search(
        self,
        user: User,
        query: str,
        result_count: int,
        knowledge_bases: List[str]
    ):
        """Loggt Suche"""
        self.log(
            user=user,
            action="search",
            details={"result_count": result_count},
            query=query,
            knowledge_bases_used=knowledge_bases
        )
    
    def get_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        department: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Ruft Audit-Logs für Zeitraum ab"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()
        
        entries = []
        current = start_date
        
        while current <= end_date:
            log_file = self._get_log_file(current)
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            data = json.loads(line)
                            
                            # Filter anwenden
                            if user_id and data["user_id"] != user_id:
                                continue
                            if action and data["action"] != action:
                                continue
                            if department and data["department"] != department:
                                continue
                            
                            entries.append(AuditLogEntry(
                                id=data["id"],
                                timestamp=datetime.fromisoformat(data["timestamp"]),
                                user_id=data["user_id"],
                                username=data["username"],
                                department=data["department"],
                                action=data["action"],
                                details=data.get("details", {}),
                                ip_address=data.get("ip_address"),
                                query=data.get("query"),
                                response_summary=data.get("response_summary"),
                                knowledge_bases_used=data.get("knowledge_bases_used", []),
                                document_name=data.get("document_name"),
                                knowledge_base_id=data.get("knowledge_base_id")
                            ))
                except Exception as e:
                    print(f"Fehler beim Lesen von {log_file}: {e}")
            
            current = current + timedelta(days=1)
        
        # Nach Zeitstempel sortieren (neueste zuerst) und limitieren
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]
    
    def get_user_activity(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Gibt Aktivitäts-Zusammenfassung für Benutzer zurück"""
        start_date = datetime.now() - timedelta(days=days)
        logs = self.get_logs(start_date=start_date, user_id=user_id, limit=1000)
        
        actions = {}
        for log in logs:
            actions[log.action] = actions.get(log.action, 0) + 1
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_actions": len(logs),
            "actions_breakdown": actions,
            "last_activity": logs[0].timestamp.isoformat() if logs else None
        }
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generiert DSG-Compliance-Bericht"""
        logs = self.get_logs(start_date=start_date, end_date=end_date, limit=10000)
        
        # Statistiken sammeln
        actions_count = {}
        users_active = set()
        departments_active = set()
        queries_count = 0
        documents_uploaded = 0
        failed_logins = 0
        
        for log in logs:
            actions_count[log.action] = actions_count.get(log.action, 0) + 1
            users_active.add(log.user_id)
            departments_active.add(log.department)
            
            if log.action == "chat_query":
                queries_count += 1
            elif log.action == "document_upload":
                documents_uploaded += 1
            elif log.action == "login_failed":
                failed_logins += 1
        
        return {
            "report_type": "DSG-Compliance",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_actions": len(logs),
                "unique_users": len(users_active),
                "active_departments": list(departments_active),
                "chat_queries": queries_count,
                "documents_uploaded": documents_uploaded,
                "failed_logins": failed_logins
            },
            "actions_breakdown": actions_count,
            "generated_at": datetime.now().isoformat(),
            "generated_by": "KMU Knowledge Assistant"
        }


class DepartmentManager:
    """Verwaltet benutzerdefinierte Abteilungen"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.departments_file = data_dir / "departments.json"
        self.departments: Dict[str, CustomDepartment] = {}
        self._load_departments()
        self._ensure_default_departments()

    def _load_departments(self):
        """Lädt Abteilungen aus JSON"""
        if self.departments_file.exists():
            try:
                with open(self.departments_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for dept_data in data:
                        dept = CustomDepartment(
                            id=dept_data["id"],
                            name=dept_data["name"],
                            description=dept_data.get("description", ""),
                            allowed_knowledge_bases=dept_data.get("allowed_knowledge_bases", []),
                            created_at=dept_data.get("created_at", ""),
                            is_active=dept_data.get("is_active", True)
                        )
                        self.departments[dept.id] = dept
            except Exception as e:
                print(f"Fehler beim Laden der Abteilungen: {e}")

    def _save_departments(self):
        """Speichert Abteilungen in JSON"""
        data = []
        for dept in self.departments.values():
            data.append({
                "id": dept.id,
                "name": dept.name,
                "description": dept.description,
                "allowed_knowledge_bases": dept.allowed_knowledge_bases,
                "created_at": dept.created_at,
                "is_active": dept.is_active
            })
        with open(self.departments_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _ensure_default_departments(self):
        """Erstellt Standard-Abteilungen falls keine existieren"""
        if not self.departments:
            default_depts = [
                ("personal", "Personal", "Personalvermittlung und HR"),
                ("finanzen", "Finanzen", "Buchhaltung und Lohnwesen"),
                ("vertrieb", "Vertrieb", "Kundenakquise und Sales"),
                ("backoffice", "Backoffice", "Administration und Support"),
            ]
            for dept_id, name, desc in default_depts:
                self.create_department(dept_id, name, desc)

    def create_department(
        self,
        dept_id: str,
        name: str,
        description: str = "",
        allowed_knowledge_bases: Optional[List[str]] = None
    ) -> CustomDepartment:
        """Erstellt neue Abteilung"""
        if dept_id in self.departments:
            raise ValueError(f"Abteilung '{dept_id}' existiert bereits")

        dept = CustomDepartment(
            id=dept_id,
            name=name,
            description=description,
            allowed_knowledge_bases=allowed_knowledge_bases or [],
            created_at=datetime.now().isoformat(),
            is_active=True
        )
        self.departments[dept.id] = dept
        self._save_departments()
        return dept

    def update_department(
        self,
        dept_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        allowed_knowledge_bases: Optional[List[str]] = None
    ) -> Optional[CustomDepartment]:
        """Aktualisiert eine Abteilung"""
        dept = self.departments.get(dept_id)
        if not dept:
            return None

        if name is not None:
            dept.name = name
        if description is not None:
            dept.description = description
        if allowed_knowledge_bases is not None:
            dept.allowed_knowledge_bases = allowed_knowledge_bases

        self._save_departments()
        return dept

    def delete_department(self, dept_id: str) -> bool:
        """Löscht (deaktiviert) eine Abteilung"""
        dept = self.departments.get(dept_id)
        if not dept:
            return False
        dept.is_active = False
        self._save_departments()
        return True

    def get_department(self, dept_id: str) -> Optional[CustomDepartment]:
        """Holt eine Abteilung"""
        return self.departments.get(dept_id)

    def list_departments(self, include_inactive: bool = False) -> List[CustomDepartment]:
        """Listet alle Abteilungen"""
        depts = list(self.departments.values())
        if not include_inactive:
            depts = [d for d in depts if d.is_active]
        return sorted(depts, key=lambda d: d.name)

    def get_all_department_names(self) -> List[str]:
        """Gibt alle Abteilungsnamen zurück (Standard + Custom)"""
        names = [d.value for d in Department]  # Enum-Werte
        names.extend([d.name for d in self.departments.values() if d.is_active])
        return sorted(set(names))

    def assign_knowledge_base(self, dept_id: str, kb_id: str) -> bool:
        """Weist einer Abteilung eine Wissensbasis zu"""
        dept = self.departments.get(dept_id)
        if not dept:
            return False
        if kb_id not in dept.allowed_knowledge_bases:
            dept.allowed_knowledge_bases.append(kb_id)
            self._save_departments()
        return True

    def remove_knowledge_base(self, dept_id: str, kb_id: str) -> bool:
        """Entfernt Wissensbasis-Zugriff von Abteilung"""
        dept = self.departments.get(dept_id)
        if not dept:
            return False
        if kb_id in dept.allowed_knowledge_bases:
            dept.allowed_knowledge_bases.remove(kb_id)
            self._save_departments()
        return True


# Globale Instanzen
from app.config import DATA_DIR

user_manager = UserManager(DATA_DIR)
audit_logger = AuditLogger(DATA_DIR)
department_manager = DepartmentManager(DATA_DIR)
