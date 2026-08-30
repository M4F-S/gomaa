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
                room="docker",
            )
            assert filepath.exists()
            assert "Atomic Architecture Decision" in filepath.read_text()
            tmp_files = list(filepath.parent.glob(".*.tmp"))
            assert len(tmp_files) == 0

    def test_rollback_preserves_existing_file_on_db_error(self):
        from unittest.mock import MagicMock
        from gomaa.core import UnifiedMemorySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"sqlite://{tmpdir}/test.db"
            mem = UnifiedMemorySystem(vault_path=tmpdir, dsn=db_path)
            # Create initial note
            res1 = mem.remember("Important Note", "Original pristine content", tags=["v1"])
            assert res1["success"] is True

            # Verify on disk
            note_path = get_safe_note_path(Path(tmpdir), "general", "general", "Important Note")
            assert "Original pristine content" in note_path.read_text(encoding="utf-8")

            # Mock DB to fail on subsequent upsert
            mem.db.upsert_note = MagicMock(side_effect=RuntimeError("Database write error"))
            res2 = mem.remember("Important Note", "Corrupted overwrite attempt", tags=["v2"])
            assert res2["success"] is False

            # Note MUST still exist and contain the original pristine content
            assert note_path.exists()
            assert "Original pristine content" in note_path.read_text(encoding="utf-8")

    def test_concurrent_atomic_writes_no_collision(self):
        import concurrent.futures
        from gomaa.vault import _atomic_write_text

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "concurrent_note.md"

            def writer(idx):
                _atomic_write_text(target, f"Thread {idx} content")
                return True

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(writer, i) for i in range(50)]
                results = [f.result() for f in futures]
            assert all(results)
            assert target.exists()
            assert "Thread" in target.read_text(encoding="utf-8")
