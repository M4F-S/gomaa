import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from gomaa.sync.gdrive import GoogleDriveSyncManager, calculate_md5


class TestGDriveSync:
    def test_manager_initialization(self, tmp_path):
        manager = GoogleDriveSyncManager(vault_path=str(tmp_path), folder_name="Test-Vault", agent_name="test-agent")
        assert manager.vault_path == tmp_path
        assert manager.folder_name == "Test-Vault"
        assert manager.agent_name == "test-agent"

    def test_calculate_md5(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("Hello Mnemosyne GDrive", encoding="utf-8")
        md5 = calculate_md5(test_file)
        assert len(md5) == 32
        assert isinstance(md5, str)

    def test_sync_fails_gracefully_without_credentials(self, tmp_path):
        manager = GoogleDriveSyncManager(vault_path=str(tmp_path))
        with patch.dict("os.environ", {}, clear=True):
            res = manager.sync()
            assert res["success"] is False
            assert "unavailable" in res["error"].lower() or "credentials" in res["error"].lower()
