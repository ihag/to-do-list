import secrets

import pytest

from app import config


def test_settings_load_from_dotenv(tmp_path, monkeypatch):
    secret = secrets.token_hex(32)
    (tmp_path / ".env").write_text(
        "JWT_SECRET=" + secret + "\nACCESS_TOKEN_EXPIRE_MINUTES=15\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    settings = config.load_settings()
    assert settings.jwt_secret == secret
    assert settings.access_token_expire_minutes == 15
    # dotenv가 직접 넣은 환경 변수도 테스트 종료 시 제거한다.
    monkeypatch.setenv("JWT_SECRET", secret)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")


@pytest.mark.parametrize("secret", ["", "short"])
def test_secret_required(tmp_path, monkeypatch, secret):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setenv("JWT_SECRET", secret)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        config.load_settings()


@pytest.mark.parametrize("minutes", ["0", "-1", "not-an-integer"])
def test_invalid_token_lifetime(tmp_path, monkeypatch, minutes):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setenv("JWT_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", minutes)
    with pytest.raises(RuntimeError, match="ACCESS_TOKEN_EXPIRE_MINUTES"):
        config.load_settings()
