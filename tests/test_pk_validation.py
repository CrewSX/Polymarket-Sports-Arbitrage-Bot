"""Tests for env private key validation."""
import pytest

from poly_sports.utils.pk_validation import get_env_private_key, require_valid_env_private_key

_VALID_TEST_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def test_get_env_private_key_prefers_pk(monkeypatch):
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.setenv("PK", _VALID_TEST_PK)
    assert get_env_private_key() == _VALID_TEST_PK


def test_get_env_private_key_falls_back_to_private_key(monkeypatch):
    monkeypatch.delenv("PK", raising=False)
    monkeypatch.setenv("PRIVATE_KEY", _VALID_TEST_PK)
    assert get_env_private_key() == _VALID_TEST_PK


def test_require_valid_accepts_good_key(monkeypatch):
    monkeypatch.setenv("PK", _VALID_TEST_PK)
    messages = []

    require_valid_env_private_key(log=messages.append, exit_code=99)
    assert messages == []


def test_require_valid_exits_when_missing(monkeypatch):
    monkeypatch.delenv("PK", raising=False)
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    messages = []

    with pytest.raises(SystemExit) as exc:
        require_valid_env_private_key(log=messages.append, exit_code=3)
    assert exc.value.code == 3
    assert any("No private key" in m for m in messages)


def test_require_valid_exits_on_placeholder(monkeypatch):
    monkeypatch.setenv("PK", "your_private_key")
    messages = []

    with pytest.raises(SystemExit) as exc:
        require_valid_env_private_key(log=messages.append, exit_code=2)
    assert exc.value.code == 2
    assert any("placeholder" in m for m in messages)


def test_require_valid_exits_on_invalid_hex(monkeypatch):
    monkeypatch.setenv("PK", "0xnotahex")
    messages = []

    with pytest.raises(SystemExit) as exc:
        require_valid_env_private_key(log=messages.append, exit_code=2)
    assert exc.value.code == 2
    assert messages
