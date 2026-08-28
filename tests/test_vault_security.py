import pytest
import tempfile
from pathlib import Path
from gomaa.vault import VaultManager, get_safe_note_path


class TestVaultSecurity:
    def test_path_traversal_wing_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            with pytest.raises(ValueError, match="Path traversal attempt detected"):
                get_safe_note_path(vault_root, wing="../../etc", room="general", title="malicious")

    def test_path_traversal_title_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            with pytest.raises(ValueError, match="Path traversal attempt detected"):
                get_safe_note_path(vault_root, wing="general", room="general", title="../../../etc/cron.d/hack")

    def test_atomic_write_creates_valid_note(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vm = VaultManager(vault_path=tmpdir)
            filepath = vm.write_note(
                title="Atomic Architecture Decision",
                content="Critical system state.",
                tags=["infra"],
                wing="devops",
                room="docker"
            )
            assert filepath.exists()
            assert "Atomic Architecture Decision" in filepath.read_text()
            tmp_files = list(filepath.parent.glob(".*.tmp"))
            assert len(tmp_files) == 0
