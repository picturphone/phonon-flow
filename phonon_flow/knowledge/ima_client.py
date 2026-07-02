"""IMA Knowledge Base client for calculation result archival."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


class IMAClient:
    """Client for Tencent IMA OpenAPI — knowledge base and notes.

    Provides a Pythonic interface to IMA's knowledge management:
    - Create/search notes
    - Upload files to knowledge bases
    - Sync calculation results
    """

    BASE_URL = "https://ima.qq.com"

    def __init__(
        self,
        client_id: Optional[str] = None,
        api_key: Optional[str] = None,
        config_dir: str = "~/.config/ima",
    ):
        """Initialize IMA client.

        Credentials are resolved in order:
        1. Explicit parameters
        2. Environment variables (IMA_OPENAPI_CLIENTID, IMA_OPENAPI_APIKEY)
        3. Config files (~/.config/ima/client_id, ~/.config/ima/api_key)

        Args:
            client_id: IMA API client ID.
            api_key: IMA API key.
            config_dir: Directory for credential files.
        """
        self.client_id = client_id or self._read_credential("IMA_OPENAPI_CLIENTID", "client_id", config_dir)
        self.api_key = api_key or self._read_credential("IMA_OPENAPI_APIKEY", "api_key", config_dir)

        if not self.client_id or not self.api_key:
            raise ValueError(
                "IMA credentials not found. Set IMA_OPENAPI_CLIENTID and IMA_OPENAPI_APIKEY "
                "environment variables, or store them in ~/.config/ima/"
            )

    def _read_credential(self, env_var: str, file_name: str, config_dir: str) -> Optional[str]:
        """Read credential from env or file."""
        # Try environment variable first
        val = os.environ.get(env_var)
        if val:
            return val

        # Try config file
        config_path = os.path.expanduser(os.path.join(config_dir, file_name))
        if os.path.exists(config_path):
            with open(config_path) as f:
                return f.read().strip()

        return None

    def _headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "X-Client-Id": self.client_id,
            "X-Api-Key": self.api_key,
        }

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to IMA API."""
        import requests

        url = f"{self.BASE_URL}{path}"
        response = requests.post(url, headers=self._headers(), json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("code", -1) != 0:
            raise RuntimeError(f"IMA API error: {result.get('msg', 'Unknown error')}")

        return result.get("data", {})

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to IMA API."""
        import requests

        url = f"{self.BASE_URL}{path}"
        response = requests.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("code", -1) != 0:
            raise RuntimeError(f"IMA API error: {result.get('msg', 'Unknown error')}")

        return result.get("data", {})

    # ── Notes ──────────────────────────────────────────

    def list_notes(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """List user notes."""
        data = self._post("/openapi/list_docs", {"limit": limit, "offset": offset})
        return data.get("docs", [])

    def search_notes(self, query: str, limit: int = 10) -> List[Dict]:
        """Search notes by keyword."""
        data = self._post("/openapi/search_docs", {"query": query, "limit": limit})
        return data.get("docs", [])

    def get_note(self, note_id: str) -> Dict[str, Any]:
        """Get full note content."""
        return self._post("/openapi/get_doc", {"doc_id": note_id})

    def create_note(
        self,
        title: str,
        content: str,
        content_format: int = 1,  # 1 = Markdown
    ) -> str:
        """Create a new note.

        Args:
            title: Note title.
            content: Note content (Markdown format).
            content_format: 1 = Markdown, 2 = plain text.

        Returns:
            Note ID.
        """
        data = self._post("/openapi/import_doc", {
            "title": title,
            "content": content,
            "content_format": content_format,
        })
        return data.get("doc_id", "")

    def append_note(self, note_id: str, content: str) -> bool:
        """Append content to an existing note.

        Args:
            note_id: Note ID.
            content: Content to append.

        Returns:
            True on success.
        """
        self._post("/openapi/append_doc", {
            "doc_id": note_id,
            "content": content,
        })
        return True

    # ── Knowledge Base ──────────────────────────────────

    def list_knowledge_bases(self) -> List[Dict]:
        """List all available knowledge bases."""
        data = self._get("/openapi/knowledge_base_list")
        return data.get("knowledge_bases", [])

    def search_knowledge(self, kb_id: str, query: str, limit: int = 10) -> List[Dict]:
        """Search within a knowledge base.

        Args:
            kb_id: Knowledge base ID.
            query: Search query.
            limit: Max results.

        Returns:
            List of matching knowledge items.
        """
        data = self._post("/openapi/search_knowledge", {
            "knowledge_base_id": kb_id,
            "query": query,
            "limit": limit,
        })
        return data.get("items", [])

    def upload_file(self, file_path: str, kb_id: str) -> str:
        """Upload a file to a knowledge base.

        Args:
            file_path: Local file path.
            kb_id: Knowledge base ID.

        Returns:
            Media ID of the uploaded file.
        """
        # This is a simplified version — actual implementation
        # would need COS upload steps (see ima-skill for full flow)

        import requests

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Step 1: Create media entry
        data = self._post("/openapi/create_media", {
            "knowledge_base_id": kb_id,
            "file_name": file_name,
            "file_size": file_size,
        })

        media_id = data.get("media_id", "")
        upload_url = data.get("upload_url", "")

        if upload_url and media_id:
            # Step 2: Upload to COS
            with open(file_path, "rb") as f:
                upload_resp = requests.put(upload_url, data=f, timeout=60)
                upload_resp.raise_for_status()

            # Step 3: Add to knowledge base
            self._post("/openapi/add_knowledge", {
                "knowledge_base_id": kb_id,
                "media_id": media_id,
                "media_type": 2,  # 2 = file
            })

        return media_id

    def add_knowledge(self, kb_id: str, media_id: str, media_type: int = 2) -> bool:
        """Add an existing media item to a knowledge base.

        Args:
            kb_id: Knowledge base ID.
            media_id: Media ID.
            media_type: 2 = file, 11 = note.

        Returns:
            True on success.
        """
        self._post("/openapi/add_knowledge", {
            "knowledge_base_id": kb_id,
            "media_id": media_id,
            "media_type": media_type,
        })
        return True

    # ── High-level Workflow Methods ─────────────────────

    def sync_calculation_report(
        self,
        title: str,
        report_md: str,
        kb_id: Optional[str] = None,
    ) -> str:
        """Sync a calculation report to IMA.

        Creates a note and optionally adds it to a knowledge base.

        Args:
            title: Report title.
            report_md: Report content in Markdown.
            kb_id: Optional knowledge base to add the note to.

        Returns:
            Note ID.
        """
        note_id = self.create_note(title, report_md)

        if kb_id:
            self.add_knowledge(kb_id, note_id, media_type=11)  # 11 = note

        return note_id

    def sync_config(self, config_path: str, kb_id: str) -> str:
        """Upload a calculation config YAML to knowledge base.

        Args:
            config_path: Path to YAML config file.
            kb_id: Knowledge base ID.

        Returns:
            Media ID.
        """
        return self.upload_file(config_path, kb_id)
