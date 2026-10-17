import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.handoff import StubChannel
from app.llm_client import FakeLLM
from app.main import create_app, require_local
from app.store import Store
from tests.helpers import Script, make_content, service

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Harness:
    http: TestClient
    app: FastAPI
    llm: FakeLLM | None
    script: Script | None
    channel: StubChannel
    store: Store

    def start(self) -> str:
        return self.http.post("/api/conversations").json()["conversation_id"]

    def say(self, cid: str, text: str, mid: str | None = None) -> httpx.Response:
        return self.http.post("/api/chat", json={"conversation_id": cid, "client_message_id": mid or uuid.uuid4().hex,
                                                 "text": text})


@pytest.fixture
def make_client(tmp_path):
    def factory(script: Script | None = None, *, services: list[dict] | None = None, policy: dict | None = None,
                channel: StubChannel | None = None, admin: bool = False, rate: int = 100,
                demo: bool = False) -> Harness:
        root = tmp_path / uuid.uuid4().hex
        content = make_content(root / "content", services or [service()], policy=policy)
        settings = Settings(_env_file=None, cloudru_api_key="" if demo else "test-key",
                            db_path=str(root / "sales.db"), content_dir=str(content),
                            skills_dir=str(ROOT / "skills"), rate_limit_per_minute=rate)
        script = None if demo else (script or Script())
        llm = FakeLLM(script) if script else None
        channel = channel or StubChannel()
        app = create_app(settings, llm=llm, channel=channel)
        if admin:
            app.dependency_overrides[require_local] = lambda: None
        return Harness(TestClient(app), app, llm, script, channel, app.state.store)

    return factory
