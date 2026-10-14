"""
Backup, Export, and Cloud Drive Synchronization for Gomaa Vaults and Stores.

Supports:
- Zero-config archives (.tar.gz, .zip) of Obsidian vault and SQLite database.
- Safe restores with path traversal protection.
- Direct synchronization with local cloud-drive folders (Google Drive for Desktop,
  iCloud Drive, Dropbox, OneDrive, or external backup volumes).
"""

import io
import json
import logging
import os
import shutil
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("gomaa-backup")


def _is_safe_tar_member(member: tarfile.TarInfo, target_dir: Path) -> bool:
    """Ensure tar member does not escape target directory (Tar-Slip defense)."""
    target_resolved = target_dir.resolve()
    dest = (target_dir / member.name).resolve()
    return dest.is_relative_to(target_resolved)


def _is_safe_zip_member(name: str, target_dir: Path) -> bool:
    """Ensure zip member does not escape target directory (Zip-Slip defense)."""
    target_resolved = target_dir.resolve()
    dest = (target_dir / name).resolve()
    return dest.is_relative_to(target_resolved)


class BackupManager:
    """Handles universal backups and folder sync for Gomaa vaults and databases."""

    def __init__(self, vault_path: Optional[str] = None, db_path: Optional[str] = None):
        self.vault_path = Path(
            os.path.expanduser(vault_path or os.environ.get("MEMORY_VAULT_PATH", "~/.gomaa/vault"))
        )
        default_db = os.environ.get("MEMORY_SQLITE_PATH", "~/.gomaa/gomaa.db")
        self.db_path = Path(os.path.expanduser(db_path or default_db))

    def create_backup(
        self,
        dest_dir: Optional[str] = None,
        archive_format: str = "tar.gz",
    ) -> Dict[str, Any]:
        """
        Create a timestamped compressed backup containing the vault and database.
        Returns backup metadata.
        """
        out_dir = Path(os.path.expanduser(dest_dir or "~/.gomaa/backups"))
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.vault_path.mkdir(parents=True, exist_ok=True)

        note_count = len(list(self.vault_path.rglob("*.md")))
        manifest = {
            "gomaa_version": "4.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vault_path": str(self.vault_path),
            "note_count": note_count,
            "has_sqlite_db": self.db_path.exists() if self.db_path else False,
        }

        if archive_format in ("zip", ".zip"):
            archive_path = out_dir / f"gomaa-backup-{timestamp}.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add manifest
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
                # Add vault files
                for file_path in self.vault_path.rglob("*"):
                    if file_path.is_file():
                        rel = file_path.relative_to(self.vault_path)
                        zf.write(file_path, arcname=f"vault/{rel}")
                # Add database if present
                if self.db_path and self.db_path.exists() and self.db_path.is_file():
                    zf.write(self.db_path, arcname="database/gomaa.db")
        else:
            archive_path = out_dir / f"gomaa-backup-{timestamp}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tf:
                # Add manifest
                manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
                tar_info = tarfile.TarInfo(name="manifest.json")
                tar_info.size = len(manifest_bytes)
                tar_info.mtime = int(datetime.now(timezone.utc).timestamp())
                tf.addfile(tar_info, io.BytesIO(manifest_bytes))

                # Add vault files
                for file_path in self.vault_path.rglob("*"):
                    if file_path.is_file():
                        rel = file_path.relative_to(self.vault_path)
                        tf.add(file_path, arcname=f"vault/{rel}")

                # Add database if present
                if self.db_path and self.db_path.exists() and self.db_path.is_file():
                    tf.add(self.db_path, arcname="database/gomaa.db")

        size_bytes = archive_path.stat().st_size
        logger.info(f"Backup created successfully: {archive_path} ({size_bytes} bytes, {note_count} notes)")
        return {
            "success": True,
            "archive_path": str(archive_path),
            "size_bytes": size_bytes,
            "note_count": note_count,
            "has_sqlite_db": manifest["has_sqlite_db"],
            "timestamp": timestamp,
        }

    def restore_backup(
        self,
        archive_path: str,
        dest_vault: Optional[str] = None,
        dest_db: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Safely restore a vault and optional SQLite database from a backup archive.
        """
        src_path = Path(os.path.expanduser(archive_path))
        if not src_path.exists():
            return {"success": False, "error": f"Backup archive not found: {src_path}"}

        target_vault = Path(os.path.expanduser(dest_vault or self.vault_path))
        target_db = Path(os.path.expanduser(dest_db or self.db_path))
        target_vault.mkdir(parents=True, exist_ok=True)

        notes_restored = 0
        db_restored = False

        if src_path.name.endswith(".zip"):
            with zipfile.ZipFile(src_path, "r") as zf:
                for member_name in zf.namelist():
                    if member_name.startswith("vault/"):
                        rel = member_name[len("vault/") :]
                        if not rel or rel.endswith("/"):
                            continue
                        if not _is_safe_zip_member(rel, target_vault):
                            raise ValueError(f"Security Alert: Zip-Slip attempt detected: {member_name}")
                        dest_file = target_vault / rel
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member_name) as source, open(dest_file, "wb") as target:
                            shutil.copyfileobj(source, target)
                        if dest_file.suffix == ".md":
                            notes_restored += 1
                    elif member_name == "database/gomaa.db" and target_db:
                        target_db.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member_name) as source, open(target_db, "wb") as target:
                            shutil.copyfileobj(source, target)
                        db_restored = True
        else:
            with tarfile.open(src_path, "r:*") as tf:
                for member in tf.getmembers():
                    if member.name.startswith("vault/"):
                        rel = member.name[len("vault/") :]
                        if not rel:
                            continue
                        if not _is_safe_tar_member(member, target_vault):
                            raise ValueError(f"Security Alert: Tar-Slip attempt detected: {member.name}")
                        dest_file = target_vault / rel
                        if member.isdir():
                            dest_file.mkdir(parents=True, exist_ok=True)
                        elif member.isfile():
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            source = tf.extractfile(member)
                            if source:
                                with open(dest_file, "wb") as target:
                                    shutil.copyfileobj(source, target)
                                if dest_file.suffix == ".md":
                                    notes_restored += 1
                    elif member.name == "database/gomaa.db" and target_db and member.isfile():
                        target_db.parent.mkdir(parents=True, exist_ok=True)
                        source = tf.extractfile(member)
                        if source:
                            with open(target_db, "wb") as target:
                                shutil.copyfileobj(source, target)
                            db_restored = True

        logger.info(f"Restored {notes_restored} notes to {target_vault}")
        return {
            "success": True,
            "vault_path": str(target_vault),
            "db_path": str(target_db) if db_restored else None,
            "notes_restored": notes_restored,
            "db_restored": db_restored,
        }

    def sync_to_folder(
        self,
        dest_folder: str,
        bidirectional: bool = True,
    ) -> Dict[str, Any]:
        """
        Synchronize local vault markdown files with a local folder (e.g. Google Drive
        for Desktop, Dropbox, iCloud, or external USB drive).
        Preserves conflicts as .conflict-YYYYMMDD-HHMMSS.md.
        """
        dest_path = Path(os.path.expanduser(dest_folder))
        dest_path.mkdir(parents=True, exist_ok=True)
        self.vault_path.mkdir(parents=True, exist_ok=True)

        stats = {"synced_to_dest": 0, "synced_from_dest": 0, "conflicts": 0, "identical": 0}

        local_files = {p.relative_to(self.vault_path): p for p in self.vault_path.rglob("*.md")}
        remote_files = {p.relative_to(dest_path): p for p in dest_path.rglob("*.md")}

        # 1. Sync from local to dest
        for rel, local_p in local_files.items():
            dest_p = dest_path / rel
            if not dest_p.exists():
                dest_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_p, dest_p)
                stats["synced_to_dest"] += 1
            else:
                # Compare modified times and content
                l_mtime = local_p.stat().st_mtime
                d_mtime = dest_p.stat().st_mtime
                if local_p.read_bytes() == dest_p.read_bytes():
                    stats["identical"] += 1
                elif l_mtime > d_mtime:
                    shutil.copy2(local_p, dest_p)
                    stats["synced_to_dest"] += 1
                elif bidirectional and d_mtime > l_mtime:
                    # Remote is newer: preserve local as conflict branch
                    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                    conflict_p = local_p.with_name(f"{local_p.stem}.conflict-{ts}{local_p.suffix}")
                    shutil.copy2(local_p, conflict_p)
                    stats["conflicts"] += 1
                    shutil.copy2(dest_p, local_p)
                    stats["synced_from_dest"] += 1

        # 2. Sync from dest to local for files that only exist in dest
        if bidirectional:
            for rel, dest_p in remote_files.items():
                local_p = self.vault_path / rel
                if not local_p.exists():
                    local_p.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest_p, local_p)
                    stats["synced_from_dest"] += 1

        return {"success": True, "stats": stats, "dest_folder": str(dest_path)}
