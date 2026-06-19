import pytest

from app.config import get_settings


def test_get_settings_reads_env(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret-token")
    monkeypatch.setenv("UI_PASSWORD", "secret-pass")
    monkeypatch.setenv("DB_PATH", "/tmp/test.db")
    monkeypatch.setenv("RETENTION_DAYS", "3")

    settings = get_settings()

    assert settings.api_token == "secret-token"
    assert settings.ui_password == "secret-pass"
    assert settings.db_path == "/tmp/test.db"
    assert settings.retention_days == 3


def test_get_settings_defaults(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret-token")
    monkeypatch.setenv("UI_PASSWORD", "secret-pass")
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("RETENTION_DAYS", raising=False)

    settings = get_settings()

    assert settings.db_path == "dashboard.db"
    assert settings.retention_days == 7


def test_get_settings_requires_api_token(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("UI_PASSWORD", "secret-pass")

    with pytest.raises(ValueError):
        get_settings()
