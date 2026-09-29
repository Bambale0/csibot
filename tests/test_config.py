import pytest

from csibot.config import Settings


def test_settings_from_env_uses_documented_glm_defaults(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("NEIRONYCH_API_KEY", "api-key")
    monkeypatch.delenv("NEIRONYCH_MODEL", raising=False)
    monkeypatch.delenv("NEIRONYCH_API_BASE", raising=False)

    settings = Settings.from_env()

    assert settings.model == "glm-5.3-flash"
    assert settings.api_base == "https://api.xn--e1aikcel5c5a.online"
    assert settings.reasoning_effort == "high"


def test_settings_require_secrets(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("NEIRONYCH_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Settings.from_env()
