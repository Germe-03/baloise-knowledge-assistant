"""
KMU Knowledge Assistant - Microsoft Graph Client
Für SharePoint, Lists, OneDrive Integration
"""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class MSGraphClient:
    """Microsoft Graph API Client"""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, client_id: str, tenant_id: str, client_secret: str):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _get_token(self) -> str:
        """Holt oder erneuert Access Token"""
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token

        try:
            from msal import ConfidentialClientApplication

            app = ConfidentialClientApplication(
                client_id=self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret
            )

            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )

            if "access_token" in result:
                self._token = result["access_token"]
                # Token gilt normalerweise 1 Stunde
                self._token_expires = datetime.now() + timedelta(minutes=55)
                return self._token
            else:
                raise Exception(f"Token-Fehler: {result.get('error_description', 'Unbekannt')}")

        except ImportError:
            raise ImportError("MSAL nicht installiert. Führe aus: pip install msal")

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Führt API Request aus"""
        token = await self._get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"{self.BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unbekannte Methode: {method}")

            response.raise_for_status()

            if response.status_code == 204:
                return {}
            return response.json()

    # ============== SITES ==============

    async def list_sites(self) -> List[Dict]:
        """Listet alle SharePoint Sites"""
        result = await self._request("GET", "/sites?search=*")
        return result.get("value", [])

    async def get_site(self, site_id: str) -> Dict:
        """Holt Site Details"""
        return await self._request("GET", f"/sites/{site_id}")

    async def search_sites(self, query: str) -> List[Dict]:
        """Sucht SharePoint Sites"""
        result = await self._request("GET", f"/sites?search={query}")
        return result.get("value", [])

    # ============== LISTS ==============

    async def get_lists(self, site_id: str) -> List[Dict]:
        """Holt alle Listen einer Site"""
        result = await self._request("GET", f"/sites/{site_id}/lists")
        return result.get("value", [])

    async def get_list(self, site_id: str, list_id: str) -> Dict:
        """Holt List Details"""
        return await self._request("GET", f"/sites/{site_id}/lists/{list_id}")

    async def read_list_items(self, site_id: str, list_id: str, top: int = 100) -> List[Dict]:
        """Liest List Items"""
        result = await self._request(
            "GET",
            f"/sites/{site_id}/lists/{list_id}/items?expand=fields&$top={top}"
        )
        return result.get("value", [])

    async def create_list_item(self, site_id: str, list_id: str, fields: Dict) -> Dict:
        """Erstellt neues List Item"""
        data = {"fields": fields}
        return await self._request(
            "POST",
            f"/sites/{site_id}/lists/{list_id}/items",
            data=data
        )

    async def update_list_item(self, site_id: str, list_id: str, item_id: str, fields: Dict) -> Dict:
        """Aktualisiert List Item"""
        return await self._request(
            "PATCH",
            f"/sites/{site_id}/lists/{list_id}/items/{item_id}/fields",
            data=fields
        )

    async def delete_list_item(self, site_id: str, list_id: str, item_id: str) -> bool:
        """Löscht List Item"""
        await self._request(
            "DELETE",
            f"/sites/{site_id}/lists/{list_id}/items/{item_id}"
        )
        return True

    # ============== DRIVE / FILES ==============

    async def get_drive_files(self, site_id: str, folder_path: str = "root") -> List[Dict]:
        """Holt Dateien aus SharePoint/OneDrive"""
        result = await self._request(
            "GET",
            f"/sites/{site_id}/drive/{folder_path}/children"
        )
        return result.get("value", [])

    async def download_file(self, site_id: str, item_id: str) -> bytes:
        """Lädt Datei herunter"""
        token = await self._get_token()

        url = f"{self.BASE_URL}/sites/{site_id}/drive/items/{item_id}/content"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True
            )
            response.raise_for_status()
            return response.content

    async def upload_file(self, site_id: str, folder_path: str, filename: str, content: bytes) -> Dict:
        """Lädt Datei hoch"""
        token = await self._get_token()

        url = f"{self.BASE_URL}/sites/{site_id}/drive/root:/{folder_path}/{filename}:/content"

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/octet-stream"
                },
                content=content
            )
            response.raise_for_status()
            return response.json()

    # ============== USERS ==============

    async def get_me(self) -> Dict:
        """Holt aktuellen User (nur mit delegierter Auth)"""
        return await self._request("GET", "/me")

    async def list_users(self) -> List[Dict]:
        """Listet alle User"""
        result = await self._request("GET", "/users")
        return result.get("value", [])

    # ============== HELPER ==============

    async def test_connection(self) -> Dict:
        """Testet die Verbindung"""
        try:
            sites = await self.list_sites()
            return {
                "status": "connected",
                "sites_found": len(sites),
                "message": "Verbindung erfolgreich!"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
