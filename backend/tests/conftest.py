import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import alphavantage
from app.services.openai_client import get_client


@pytest.fixture(autouse=True)
def entorno_hermetico(monkeypatch):
    """Ningún test puede depender de un .env real ni salir a internet.

    Anula las claves del proceso (aunque el desarrollador tenga un .env con claves
    reales), y limpia la caché de AlphaVantage, su transporte y el cliente de OpenAI.
    """
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "alphavantage_api_key", None)
    monkeypatch.setattr(alphavantage, "_transport", None)
    alphavantage._cache.clear()
    get_client.cache_clear()
    yield
    alphavantage._cache.clear()
    get_client.cache_clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
