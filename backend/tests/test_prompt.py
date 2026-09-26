import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.services import prompt
from app.services.saludos import SALUDOS


def test_construir_mensajes_arma_sistema_y_usuario():
    mensajes = prompt.construir_mensajes("¿Qué hace Apple?")

    assert mensajes == [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": "¿Qué hace Apple?"},
    ]


@pytest.mark.anyio
async def test_sin_openai_responde_en_modo_demostracion(monkeypatch):
    async def no_debe_llamarse(_mensajes):
        raise AssertionError("no debe consultar al agente en modo demostración")

    monkeypatch.setattr(prompt, "ejecutar_agente", no_debe_llamarse)

    assert await prompt.generar_respuesta("hola") in SALUDOS


@pytest.mark.anyio
async def test_con_openai_configurado_delega_en_el_agente(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("sk-de-prueba"))
    recibidos = []

    async def agente_falso(mensajes):
        recibidos.append(mensajes)
        return "respuesta del agente"

    monkeypatch.setattr(prompt, "ejecutar_agente", agente_falso)

    assert await prompt.generar_respuesta("hola") == "respuesta del agente"
    assert recibidos == [prompt.construir_mensajes("hola")]
