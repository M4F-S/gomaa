"""Tests for BackupManager (backup, restore, and local cloud-folder sync)."""

from pathlib import Path
from gomaa.backup import BackupManager


def test_backup_and_restore_tar_gz(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "general").mkdir()
    (vault_dir / "general" / "note1.md").write_text("# Note 1\nContent 1", encoding="utf-8")
    (vault_dir / "projects").mkdir()
    (vault_dir / "projects" / "note2.md").write_text("# Note 2\nContent 2", encoding="utf-8")

    db_file = tmp_path / "gomaa.db"
    db_file.write_text("MOCK SQLITE DB DATA", encoding="utf-8")

    dest_backup_dir = tmp_path / "backups"
    manager = BackupManager(vault_path=str(vault_dir), db_path=str(db_file))

    # 1. Create backup
    res = manager.create_backup(dest_dir=str(dest_backup_dir), archive_format="tar.gz")
    assert res["success"] is True
    assert res["note_count"] == 2
    assert res["has_sqlite_db"] is True
    archive_path = Path(res["archive_path"])
    assert archive_path.exists()
    assert archive_path.stat().st_size > 0

    # 2. Restore to clean locations
    restore_vault = tmp_path / "restored_vault"
    restore_db = tmp_path / "restored.db"
    rest_res = manager.restore_backup(
        archive_path=str(archive_path),
        dest_vault=str(restore_vault),
        dest_db=str(restore_db),
    )
    assert rest_res["success"] is True
    assert rest_res["notes_restored"] == 2
    assert rest_res["db_restored"] is True

    # 3. Verify content
    assert (restore_vault / "general" / "note1.md").read_text(encoding="utf-8") == "# Note 1\nContent 1"
    assert (restore_vault / "projects" / "note2.md").read_text(encoding="utf-8") == "# Note 2\nContent 2"
    assert restore_db.read_text(encoding="utf-8") == "MOCK SQLITE DB DATA"


def test_backup_and_restore_zip(tmp_path):
    vault_dir = tmp_path / "vault_zip"
    vault_dir.mkdir()
    (vault_dir / "test.md").write_text("# Test Zip", encoding="utf-8")

    dest_backup_dir = tmp_path / "backups_zip"
    manager = BackupManager(vault_path=str(vault_dir))

    res = manager.create_backup(dest_dir=str(dest_backup_dir), archive_format="zip")
    assert res["success"] is True
    assert res["note_count"] == 1
    archive_path = Path(res["archive_path"])
    assert archive_path.name.endswith(".zip")
    assert archive_path.exists()

    restore_vault = tmp_path / "restored_vault_zip"
    rest_res = manager.restore_backup(archive_path=str(archive_path), dest_vault=str(restore_vault))
    assert rest_res["success"] is True
    assert rest_res["notes_restored"] == 1
    assert (restore_vault / "test.md").read_text(encoding="utf-8") == "# Test Zip"


def test_restore_missing_archive():
    manager = BackupManager()
    res = manager.restore_backup("definitely_nonexistent_archive.tar.gz")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_sync_to_folder_and_conflicts(tmp_path):
    vault_dir = tmp_path / "local_vault"
    vault_dir.mkdir()
    cloud_folder = tmp_path / "google_drive_folder"
    cloud_folder.mkdir()

    local_note = vault_dir / "doc.md"
    local_note.write_text("Local version 1", encoding="utf-8")

    manager = BackupManager(vault_path=str(vault_dir))

    # Initial sync to folder
    res1 = manager.sync_to_folder(str(cloud_folder))
    assert res1["success"] is True
    assert res1["stats"]["synced_to_dest"] == 1
    assert (cloud_folder / "doc.md").read_text(encoding="utf-8") == "Local version 1"

    # Second sync: identical content
    res2 = manager.sync_to_folder(str(cloud_folder))
    assert res2["stats"]["identical"] == 1

    # Simulate conflict: remote modified with newer timestamp
    remote_note = cloud_folder / "doc.md"
    remote_note.write_text("Remote newer edit from cloud", encoding="utf-8")
    import time
    time.sleep(0.05)
    # Ensure remote mtime is strictly greater
    remote_mtime = local_note.stat().st_mtime + 20
    import os
    os.utime(str(remote_note), (remote_mtime, remote_mtime))

    res3 = manager.sync_to_folder(str(cloud_folder), bidirectional=True)
    assert res3["success"] is True
    assert res3["stats"]["conflicts"] == 1
    assert res3["stats"]["synced_from_dest"] == 1

    # Verify conflict branch preserved
    conflict_files = list(vault_dir.glob("doc.conflict-*.md"))
    assert len(conflict_files) == 1
    assert conflict_files[0].read_text(encoding="utf-8") == "Local version 1"
    # Main local note updated to remote
    assert local_note.read_text(encoding="utf-8") == "Remote newer edit from cloud"
