import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("CLOUDRU_API_KEY", "k")
    monkeypatch.setenv("ACCESS_CODE", "code-1234")
    s = Settings(_env_file=None)
    assert s.cloudru_base_url == "https://foundation-models.api.cloud.ru/v1"
    assert s.embed_model == "BAAI/bge-m3"
    assert s.rerank_model == "BAAI/bge-reranker-v2-m3"
    assert s.chat_model == "ai-sage/GigaChat3.5-432B-A28B"
    assert (s.max_files, s.max_file_mb, s.max_questions) == (10, 20, 60)
    assert s.session_ttl_seconds == 3600
    assert s.cookie_secure is True


@pytest.mark.parametrize("code", ["", "short"])
def test_weak_access_code_rejected(code):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cloudru_api_key="k", access_code=code)
