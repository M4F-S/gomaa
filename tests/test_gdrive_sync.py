from unittest.mock import patch
from gomaa.sync.gdrive import GoogleDriveSyncManager, calculate_md5


class TestGDriveSync:
    def test_manager_initialization(self, tmp_path):
        manager = GoogleDriveSyncManager(vault_path=str(tmp_path), folder_name="Test-Vault", agent_name="test-agent")
        assert manager.vault_path == tmp_path
        assert manager.folder_name == "Test-Vault"
        assert manager.agent_name == "test-agent"

    def test_calculate_md5(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("Hello Gomaa GDrive", encoding="utf-8")
        md5 = calculate_md5(test_file)
        assert len(md5) == 32
        assert isinstance(md5, str)

    def test_sync_fails_gracefully_without_credentials(self, tmp_path):
        manager = GoogleDriveSyncManager(vault_path=str(tmp_path))
        with patch.dict("os.environ", {}, clear=True):
            res = manager.sync()
            assert res["success"] is False
            assert "unavailable" in res["error"].lower() or "credentials" in res["error"].lower()

    def test_sync_conflict_branch_preservation(self, tmp_path):
        manager = GoogleDriveSyncManager(vault_path=str(tmp_path))
        note_file = tmp_path / "general" / "test_note.md"
        note_file.parent.mkdir(parents=True, exist_ok=True)
        note_file.write_text("Local original content", encoding="utf-8")

        # Fake remote note that is newer and has different md5
        remote_notes = {
            "general___test_note.md": {
                "id": "remote_file_123",
                "name": "general___test_note.md",
                "md5Checksum": "different_md5_hash_from_remote",
                "modifiedTime": "2030-01-01T00:00:00Z",
            }
        }

        with patch.object(manager, "ensure_remote_structure", return_value=True), \
             patch.object(manager, "list_remote_notes", return_value=remote_notes), \
             patch.object(manager, "pull_note", side_effect=lambda fid, rname: (note_file.write_text("Remote updated content", encoding="utf-8"), True)[1]):

            res = manager.sync()
            assert res["success"] is True
            assert res["stats"]["conflicts"] == 1
            assert res["stats"]["pulled"] == 1

            # Check that conflict branch file was preserved
            conflict_files = list(note_file.parent.glob("test_note.conflict-*.md"))
            assert len(conflict_files) == 1
            assert conflict_files[0].read_text(encoding="utf-8") == "Local original content"
            # Main note updated to remote content
            assert note_file.read_text(encoding="utf-8") == "Remote updated content"

    def test_sync_skips_identical_md5(self, tmp_path):
        manager = GoogleDriveSyncManager(vault_path=str(tmp_path))
        note_file = tmp_path / "note.md"
        note_file.write_text("Identical content", encoding="utf-8")
        current_md5 = calculate_md5(note_file)

        remote_notes = {
            "note.md": {
                "id": "remote_file_456",
                "name": "note.md",
                "md5Checksum": current_md5,
                "modifiedTime": "2026-01-01T00:00:00Z",
            }
        }

        with patch.object(manager, "ensure_remote_structure", return_value=True), \
             patch.object(manager, "list_remote_notes", return_value=remote_notes), \
             patch.object(manager, "pull_note") as mock_pull, \
             patch.object(manager, "push_note") as mock_push:

            res = manager.sync()
            assert res["success"] is True
            assert res["stats"]["pushed"] == 0
            assert res["stats"]["pulled"] == 0
            assert res["stats"]["conflicts"] == 0
            mock_pull.assert_not_called()
            mock_push.assert_not_called()
