import os
import subprocess
import sys
import pytest


def test_cli_init_command(tmp_path):
    vault_dir = str(tmp_path / "test_vault")
    cmd = [
        sys.executable,
        "-m",
        "gomaa.cli",
        "init",
        "--path",
        vault_dir,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Gomaa Initialized Successfully" in res.stdout
    assert os.path.exists(vault_dir)
    assert os.path.exists(os.path.join(vault_dir, "general"))
    assert os.path.exists(os.path.join(vault_dir, "projects"))


def test_cli_assemble_context_command(tmp_path):
    vault_dir = str(tmp_path / "test_vault")
    # First init
    subprocess.run([sys.executable, "-m", "gomaa.cli", "init", "--path", vault_dir], check=True)

    # Run assemble-context
    cmd = [
        sys.executable,
        "-m",
        "gomaa.cli",
        "--vault-path",
        vault_dir,
        "assemble-context",
        "Welcome",
        "--max-tokens",
        "500",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "<memory_context>" in res.stdout
    assert "Welcome to Gomaa" in res.stdout
