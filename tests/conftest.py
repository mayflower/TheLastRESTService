from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, TYPE_CHECKING

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:  # pragma: no cover - hints only
    from fastapi.testclient import TestClient


@pytest.fixture
def make_client(monkeypatch: pytest.MonkeyPatch) -> Callable[[Dict[str, str] | None], "TestClient"]:
    """Factory fixture to build a TestClient with optional environment overrides."""

    def factory(env: Dict[str, str] | None = None) -> "TestClient":
        from fastapi.testclient import TestClient
        from app import api as app_api
        from app import config as app_config
        from app.main import create_app
        from app.sandbox import SandboxManager

        overrides = env or {}
        if "LARS_AUTH_TOKEN" in overrides:
            monkeypatch.setenv("LARS_AUTH_TOKEN", overrides["LARS_AUTH_TOKEN"])
        else:
            monkeypatch.delenv("LARS_AUTH_TOKEN", raising=False)

        app_config.get_settings.cache_clear()
        app_api.sandbox_manager = SandboxManager()

        app = create_app()
        return TestClient(app)

    return factory
