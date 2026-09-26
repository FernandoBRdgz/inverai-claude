from app.api.v1.endpoints import chat as chat_endpoint
from app.core.errors import ProveedorError
from app.services.saludos import SALUDOS


def test_chat_en_modo_demostracion_devuelve_saludo_valido(client):
    # Sin OPENAI_API_KEY (ver conftest) el asistente responde con un saludo, como siempre.
    respuesta = client.post("/api/v1/chat", json={"mensaje": "hola"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["respuesta"] in SALUDOS


def test_chat_rechaza_mensaje_vacio(client):
    respuesta = client.post("/api/v1/chat", json={"mensaje": ""})
    assert respuesta.status_code == 422


def test_chat_devuelve_lo_que_genera_el_asistente(client, monkeypatch):
    recibidos = []

    async def asistente_falso(mensaje: str) -> str:
        recibidos.append(mensaje)
        return "Apple diseña y vende dispositivos y servicios."

    monkeypatch.setattr(chat_endpoint, "generar_respuesta", asistente_falso)

    respuesta = client.post("/api/v1/chat", json={"mensaje": "¿Qué hace Apple?"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"respuesta": "Apple diseña y vende dispositivos y servicios."}
    assert recibidos == ["¿Qué hace Apple?"]


def test_chat_responde_502_si_falla_un_proveedor_sin_filtrar_detalles(client, monkeypatch):
    async def asistente_roto(_mensaje: str) -> str:
        raise ProveedorError("OpenAI no respondió correctamente (RateLimitError)")

    monkeypatch.setattr(chat_endpoint, "generar_respuesta", asistente_roto)

    respuesta = client.post("/api/v1/chat", json={"mensaje": "hola"})

    assert respuesta.status_code == 502
    assert "RateLimitError" not in respuesta.text
