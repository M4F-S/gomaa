import pytest
import tempfile
from gomaa.vault import VaultManager


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
        from gomaa.vault import safe_filename

        assert safe_filename("Hello World") == "Hello World.md"
        assert safe_filename("会议记录") == "会议记录.md"
        assert safe_filename("Запись") == "Запись.md"
        assert safe_filename("") == "untitled.md"

    def test_wiki_links_extraction(self, vault):
        content = "See [[Another Note]] and [[Third Note]]"
        links = vault.extract_wiki_links(content)
        assert links == ["Another Note", "Third Note"]

    def test_piped_and_section_wiki_links(self, vault):
        content = "Check [[Architecture#Database|DB Schema]] and [[DevOps/Deployment#Staging]]"
        links = vault.extract_wiki_links(content)
        assert links == ["Architecture", "DevOps/Deployment"]

    def test_wiki_links_ignores_code_blocks(self, vault):
        content = """
Here is a normal link: [[ValidNote]].
And here is a code block:
```python
matrix = [[1, 2], [3, 4]]
val = matrix[[0]]
```
And inline code `array[[1]]`.
"""
        links = vault.extract_wiki_links(content)
        assert links == ["ValidNote"]
