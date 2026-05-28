import pytest
from fastapi import HTTPException


def test_verify_api_key_rejects_wrong_key(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "api_key", "correct-key-32chars-abcdefghijkl")
    from app.api.routes import verify_api_key

    with pytest.raises(HTTPException) as exc:
        verify_api_key("wrong-key")
    assert exc.value.status_code == 401


def test_verify_api_key_accepts_correct_key(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "api_key", "correct-key-32chars-abcdefghijkl")
    from app.api.routes import verify_api_key

    result = verify_api_key("correct-key-32chars-abcdefghijkl")
    assert result == "correct-key-32chars-abcdefghijkl"
