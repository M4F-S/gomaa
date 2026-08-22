import pytest
import tempfile
from mnemosyne.vault import VaultManager


class TestVaultManager:
    @pytest.fixture
    def vault(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield VaultManager(tmpdir)

    def test_write_and_read_note(self, vault):
        vault.write_note("Test Note", "This is a test", tags=["test"])
        note = vault.read_note("Test Note")
        assert note["title"] == "Test Note"
        assert note["content"] == "This is a test"

    def test_safe_filename_unicode(self):
        from mnemosyne.vault import safe_filename

        assert safe_filename("Hello World") == "Hello World.md"
        assert safe_filename("会议记录") == "会议记录.md"
        assert safe_filename("Запись") == "Запись.md"
        assert safe_filename("") == "untitled.md"

    def test_wiki_links_extraction(self, vault):
        content = "See [[Another Note]] and [[Third Note]]"
        links = vault._extract_wiki_links(content)
        assert links == ["Another Note", "Third Note"]
