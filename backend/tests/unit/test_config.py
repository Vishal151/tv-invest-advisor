from app.core.config import Settings


def test_cors_origins_list_single():
    s = Settings(cors_origins="http://localhost:3000")
    assert s.cors_origins_list == ["http://localhost:3000"]


def test_cors_origins_list_multiple():
    s = Settings(cors_origins="http://localhost:3000,https://example.com")
    assert s.cors_origins_list == ["http://localhost:3000", "https://example.com"]


def test_is_production_false_by_default():
    s = Settings()
    assert not s.is_production


def test_is_production_true():
    s = Settings(app_env="production")
    assert s.is_production


def test_langfuse_enabled_when_both_keys_set():
    s = Settings(langfuse_public_key="pk-lf-abc", langfuse_secret_key="sk-lf-abc")
    assert s.langfuse_enabled


def test_langfuse_disabled_when_keys_missing(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    s = Settings(langfuse_public_key="", langfuse_secret_key="", _env_file=None)
    assert not s.langfuse_enabled


def test_valid_sectors_contains_expected_values():
    s = Settings()
    assert "FMCG" in s.valid_sectors
    assert "Retail" in s.valid_sectors


def test_valid_budget_tiers_contains_expected_values():
    s = Settings()
    assert "under-100k" in s.valid_budget_tiers
    assert "2m-plus" in s.valid_budget_tiers
