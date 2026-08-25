"""GoogleDrive remote_name -> local vault path sanitization.

A remote Drive file name is encoded with `___` in place of `/` to represent
subdirectories. Before it is joined to the vault root it MUST be validated so a
malicious/accidental name like `..___..___evil.md` cannot traverse outside the
vault (PATH TRAVERSAL).
"""
import pathlib

import pytest

from mnemosyne.sync.gdrive import safe_pull_dest_path


@pytest.fixture
def vault_root(tmp_path):
    return tmp_path / "vault"


def test_normal_remote_name_stays_inside(vault_root):
    dest = safe_pull_dest_path(vault_root, "notes___science___readme.md")
    assert dest.is_relative_to(vault_root)
    # The ___ should translate to path separators.
    assert dest.name == "readme.md"
    assert str(dest).endswith("notes/science/readme.md")


def test_traversal_dotdot_rejected(vault_root):
    with pytest.raises(ValueError):
        safe_pull_dest_path(vault_root, "..___..___evil.md")


def test_absolute_remote_name_rejected(vault_root):
    # `___` at the start decodes to a leading `/` => absolute path.
    with pytest.raises(ValueError):
        safe_pull_dest_path(vault_root, "___tmp___evil.md")


def test_single_component_allowed(vault_root):
    dest = safe_pull_dest_path(vault_root, "plain.md")
    assert dest == vault_root / "plain.md"


def test_leading_slashes_rejected(vault_root):
    with pytest.raises(ValueError):
        safe_pull_dest_path(vault_root, "___etc___passwd")