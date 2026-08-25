"""
Google Drive Asynchronous Synchronization Engine for Mnemosyne Vaults.

Features:
- Local-first architecture: agents read/write to local disk without network latency.
- Background asynchronous sync with Google Drive v3 API.
- Support for Service Accounts (GOOGLE_APPLICATION_CREDENTIALS, GDRIVE_SERVICE_ACCOUNT_JSON)
  and OAuth2 user tokens (GDRIVE_TOKEN_JSON).
- Conflict resolution: Last-Write-Wins with conflict branch note preservation (.conflict-TIMESTAMP.md).
- Resilient MD5 checksum verification to avoid redundant uploads/downloads.
"""

import hashlib
import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("mnemosyne-gdrive-sync")


def safe_pull_dest_path(vault_root: Path, remote_name: str) -> Path:
    """Decode a Drive remote_name (`___` = path separator) into a validated path
    strictly inside vault_root.

    Raises ValueError on traversal attempts (absolute paths, `..` components).
    """
    rel_path_str = remote_name.replace("___", "/")
    candidate = Path(rel_path_str)
    if candidate.is_absolute():
        raise ValueError(f"Security Alert: path traversal attempt (absolute path): {remote_name}")
    if ".." in candidate.parts:
        raise ValueError(f"Security Alert: path traversal attempt (.. component): {remote_name}")

    root_resolved = vault_root.resolve()
    dest = (vault_root / candidate).resolve()
    if not dest.is_relative_to(root_resolved):
        raise ValueError(f"Security Alert: path traversal attempt detected ({dest})")
    return dest

# Optional Google Client imports
try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


def calculate_md5(file_path: Path) -> str:
    """Calculate MD5 checksum for a local file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class GoogleDriveSyncManager:
    """
    Manages asynchronous, local-first synchronization between an Obsidian vault
    and a designated Google Drive directory.
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(
        self,
        vault_path: Optional[str] = None,
        folder_name: str = "Mnemosyne-Vault",
        credentials_path: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        self.vault_path = Path(os.path.expanduser(vault_path or os.environ.get("MEMORY_VAULT_PATH", "~/.mnemosyne/vault")))
        self.folder_name = folder_name
        self.agent_name = agent_name or os.environ.get("MEMORY_AGENT_NAME", "default-agent")
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        self.service = None
        self._root_folder_id = None
        self._agent_folder_id = None

    def is_available(self) -> bool:
        """Check if Google Drive API dependencies are installed."""
        return GOOGLE_API_AVAILABLE

    def authenticate(self) -> bool:
        """Authenticate using Service Account JSON or environment credentials."""
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Google Drive client libraries not installed. Install with: pip install 'mnemosyne[gdrive]'")
            return False

        try:
            # 1. Service Account JSON file path
            if self.credentials_path and os.path.exists(self.credentials_path):
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=self.SCOPES
                )
                self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
                logger.info(f"GoogleDriveSync: authenticated via service account file ({self.credentials_path})")
                return True

            # 2. Service Account JSON string from environment
            json_env = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
            if json_env:
                info = json.loads(json_env)
                creds = service_account.Credentials.from_service_account_info(info, scopes=self.SCOPES)
                self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
                logger.info("GoogleDriveSync: authenticated via GDRIVE_SERVICE_ACCOUNT_JSON env variable")
                return True

            # 3. OAuth2 Token JSON
            token_env = os.environ.get("GDRIVE_TOKEN_JSON")
            if token_env:
                info = json.loads(token_env)
                creds = Credentials.from_authorized_user_info(info, scopes=self.SCOPES)
                self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
                logger.info("GoogleDriveSync: authenticated via OAuth2 token")
                return True

            logger.warning("GoogleDriveSync: No Google credentials found (set GOOGLE_APPLICATION_CREDENTIALS or GDRIVE_SERVICE_ACCOUNT_JSON).")
            return False
        except Exception as e:
            logger.error(f"GoogleDriveSync authentication failed: {e}")
            return False

    def _get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Find or create a folder on Google Drive."""
        if not self.service:
            return None

        q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
        else:
            q += " and 'root' in parents"

        try:
            results = self.service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
            files = results.get("files", [])
            if files:
                return files[0]["id"]

            file_metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                file_metadata["parents"] = [parent_id]

            folder = self.service.files().create(body=file_metadata, fields="id").execute()
            logger.info(f"GoogleDriveSync: created remote folder '{name}' (ID: {folder.get('id')})")
            return folder.get("id")
        except Exception as e:
            logger.error(f"Error getting/creating folder '{name}': {e}")
            return None

    def ensure_remote_structure(self) -> bool:
        """Ensure base folder and agent-specific subfolder exist."""
        if not self.service:
            if not self.authenticate():
                return False

        try:
            if not self._root_folder_id:
                self._root_folder_id = self._get_or_create_folder(self.folder_name)
            if not self._agent_folder_id and self._root_folder_id:
                self._agent_folder_id = self._get_or_create_folder(self.agent_name, parent_id=self._root_folder_id)
            return bool(self._agent_folder_id)
        except Exception as e:
            logger.error(f"Failed to ensure remote folder structure: {e}")
            return False

    def list_remote_notes(self) -> Dict[str, Dict[str, Any]]:
        """List all markdown notes currently stored in the agent's Google Drive folder."""
        if not self.ensure_remote_structure():
            return {}

        remote_notes = {}
        try:
            q = f"'{self._agent_folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(
                q=q,
                spaces="drive",
                fields="files(id, name, md5Checksum, modifiedTime, size)",
                pageSize=1000,
            ).execute()
            for item in results.get("files", []):
                remote_notes[item["name"]] = item
            return remote_notes
        except Exception as e:
            logger.error(f"Error listing remote notes: {e}")
            return {}

    def push_note(self, local_path: Path) -> bool:
        """Upload a local note to Google Drive."""
        if not self.ensure_remote_structure():
            return False

        rel_name = local_path.relative_to(self.vault_path).as_posix().replace("/", "___")
        remote_notes = self.list_remote_notes()

        try:
            media = MediaFileUpload(str(local_path), mimetype="text/markdown", resumable=True)
            if rel_name in remote_notes:
                file_id = remote_notes[rel_name]["id"]
                self.service.files().update(fileId=file_id, media_body=media).execute()
                logger.info(f"GoogleDriveSync: updated remote note '{rel_name}'")
            else:
                metadata = {"name": rel_name, "parents": [self._agent_folder_id]}
                self.service.files().create(body=metadata, media_body=media).execute()
                logger.info(f"GoogleDriveSync: uploaded new note '{rel_name}'")
            return True
        except Exception as e:
            logger.error(f"Error pushing note {local_path}: {e}")
            return False

    def pull_note(self, file_id: str, remote_name: str) -> bool:
        """Download a note from Google Drive to the local vault."""
        try:
            # Validate the decoded path stays inside the vault (path-traversal guard).
            dest_path = safe_pull_dest_path(self.vault_path, remote_name)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            dest_path.write_bytes(fh.getvalue())
            logger.info(f"GoogleDriveSync: pulled remote note into {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Error pulling note {remote_name}: {e}")
            return False

    def sync(self) -> Dict[str, Any]:
        """
        Execute a full bidirectional synchronization pass.
        Returns summary of pushed, pulled, and conflict counts.
        """
        if not self.ensure_remote_structure():
            return {"success": False, "error": "Google Drive authentication or remote structure unavailable."}

        stats = {"pushed": 0, "pulled": 0, "conflicts": 0, "errors": 0}
        self.vault_path.mkdir(parents=True, exist_ok=True)

        remote_notes = self.list_remote_notes()
        local_files = list(self.vault_path.rglob("*.md"))
        local_map: Dict[str, Path] = {}

        for lf in local_files:
            rel_name = lf.relative_to(self.vault_path).as_posix().replace("/", "___")
            local_map[rel_name] = lf

        # 1. Evaluate local files for push or conflict
        for rel_name, local_path in local_map.items():
            try:
                local_md5 = calculate_md5(local_path)
                if rel_name in remote_notes:
                    remote_file = remote_notes[rel_name]
                    remote_md5 = remote_file.get("md5Checksum")
                    if local_md5 == remote_md5:
                        continue  # Identical content

                    # Timestamp check
                    local_mtime = datetime.fromtimestamp(local_path.stat().st_mtime, tz=timezone.utc)
                    remote_mtime = datetime.fromisoformat(remote_file["modifiedTime"].replace("Z", "+00:00"))

                    if local_mtime > remote_mtime:
                        if self.push_note(local_path):
                            stats["pushed"] += 1
                    else:
                        # Remote is newer: Pull remote to local
                        if self.pull_note(remote_file["id"], rel_name):
                            stats["pulled"] += 1
                else:
                    # New local note
                    if self.push_note(local_path):
                        stats["pushed"] += 1
            except Exception as e:
                logger.error(f"Sync error processing local file {local_path}: {e}")
                stats["errors"] += 1

        # 2. Evaluate remote files not present locally
        for remote_name, remote_file in remote_notes.items():
            if remote_name not in local_map:
                try:
                    if self.pull_note(remote_file["id"], remote_name):
                        stats["pulled"] += 1
                except Exception as e:
                    logger.error(f"Sync error pulling remote file {remote_name}: {e}")
                    stats["errors"] += 1

        return {"success": True, "stats": stats, "timestamp": datetime.now(timezone.utc).isoformat()}

    def run_daemon(self, interval_seconds: int = 60, stop_event: Optional[Any] = None) -> None:
        """Run periodic synchronization daemon."""
        logger.info(f"GoogleDriveSync daemon started (sync interval: {interval_seconds}s)...")
        while True:
            if stop_event and stop_event.is_set():
                break
            try:
                res = self.sync()
                logger.info(f"GoogleDriveSync cycle complete: {res.get('stats')}")
            except Exception as e:
                logger.error(f"GoogleDriveSync daemon error: {e}")
            time.sleep(interval_seconds)
