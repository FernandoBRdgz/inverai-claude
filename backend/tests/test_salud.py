from pydantic import SecretStr

from app.core.config import settings


def test_health_trae_el_shape_esperado_sin_claves_configuradas(client):
    # Bajo entorno_hermetico (conftest.py) no hay claves reales: ambos booleanos dan False.
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo == {
        "status": "ok",
        "openai_configurado": False,
        "alphavantage_configurado": False,
        "modelo": settings.openai_model,
    }


def test_health_refleja_claves_configuradas(client, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("sk-de-prueba"))
    monkeypatch.setattr(settings, "alphavantage_api_key", SecretStr("av-de-prueba"))

    cuerpo = client.get("/health").json()

    assert cuerpo["openai_configurado"] is True
    assert cuerpo["alphavantage_configurado"] is True


def test_health_no_filtra_las_claves(client, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("sk-secreta-123"))

    texto = client.get("/health").text

    assert "sk-secreta-123" not in texto
