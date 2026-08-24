import pytest
from mnemosyne.core import UnifiedMemorySystem, SecurityCheckError


class TestSecurityExpanded:
    def test_sanitize_anthropic_key_blocked(self, tmp_path):
        mem = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
        anthropic_payload = "Here is my key: sk-ant-api03-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        with pytest.raises(SecurityCheckError):
            mem._sanitize_for_shared(anthropic_payload)

    def test_sanitize_gemini_key_blocked(self, tmp_path):
        mem = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
        gemini_payload = "Configured AIzaSyABC12345def67890GHIJKLMNopqrstuv"
        with pytest.raises(SecurityCheckError):
            mem._sanitize_for_shared(gemini_payload)

    def test_sanitize_huggingface_token_blocked(self, tmp_path):
        mem = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
        hf_payload = "My token is hf_abcdefghijklmnopqrstuvwxyz12345678"
        with pytest.raises(SecurityCheckError):
            mem._sanitize_for_shared(hf_payload)

    def test_sanitize_openai_proj_key_blocked(self, tmp_path):
        mem = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
        openai_payload = "Key: sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        with pytest.raises(SecurityCheckError):
            mem._sanitize_for_shared(openai_payload)

    def test_sanitize_safe_text_allowed(self, tmp_path):
        mem = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
        safe_payload = "This is an architectural note on how to use API keys safely in documentation."
        mem._sanitize_for_shared(safe_payload)  # Should not raise
