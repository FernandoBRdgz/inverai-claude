import asyncio
import json
import time
from types import SimpleNamespace

import openai
import pytest

from app.core.config import settings
from app.core.errors import ProveedorError
from app.services import agents, tools


class ClienteFalso:
    """Imita AsyncOpenAI().chat.completions.create devolviendo respuestas predefinidas."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._crear))

    async def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def _texto(contenido: str):
    mensaje = SimpleNamespace(content=contenido, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def _pide_tool(nombre: str, argumentos: str, id_llamada: str = "call_1"):
    llamada = SimpleNamespace(id=id_llamada, function=SimpleNamespace(name=nombre, arguments=argumentos))
    mensaje = SimpleNamespace(content=None, tool_calls=[llamada])
    return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


MENSAJES = [{"role": "system", "content": "sistema"}, {"role": "user", "content": "hola"}]


@pytest.fixture(autouse=True)
def _sin_cache_de_reasoning_effort():
    agents._MODELOS_SIN_REASONING_EFFORT_EN_TOOLS.clear()
    yield
    agents._MODELOS_SIN_REASONING_EFFORT_EN_TOOLS.clear()


class _ErrorReasoningEffort(openai.OpenAIError):
    """Imita el 400 real de OpenAI para modelos que razonan y no aceptan tools así."""

    param = "reasoning_effort"


def _usar(monkeypatch, cliente):
    monkeypatch.setattr(agents, "get_client", lambda: cliente)


@pytest.mark.anyio
async def test_devuelve_el_texto_del_modelo_sin_enviar_tools_si_no_hay(monkeypatch):
    cliente = ClienteFalso(_texto("Respuesta final"))
    _usar(monkeypatch, cliente)
    monkeypatch.setattr(agents, "TOOLS", [])

    respuesta = await agents.ejecutar_agente(MENSAJES)

    assert respuesta == "Respuesta final"
    assert "tools" not in cliente.llamadas[0]
    assert cliente.llamadas[0]["messages"] == MENSAJES


@pytest.mark.anyio
async def test_ejecuta_la_tool_pedida_y_devuelve_la_respuesta_final(monkeypatch):
    spec = [{"type": "function", "function": {"name": "perfil", "parameters": {"type": "object"}}}]
    recibidos = []

    async def perfil(symbol: str):
        recibidos.append(symbol)
        return {"symbol": symbol, "sector": "Tecnología"}

    monkeypatch.setattr(agents, "TOOLS", spec)
    monkeypatch.setitem(tools.TOOL_REGISTRY, "perfil", perfil)
    cliente = ClienteFalso(_pide_tool("perfil", '{"symbol": "IBM"}'), _texto("IBM es de tecnología"))
    _usar(monkeypatch, cliente)

    respuesta = await agents.ejecutar_agente(MENSAJES)

    assert respuesta == "IBM es de tecnología"
    assert recibidos == ["IBM"]
    assert cliente.llamadas[0]["tools"] == spec
    # En la segunda vuelta el modelo recibe su propia petición y el resultado de la tool.
    segunda = cliente.llamadas[1]["messages"]
    assert segunda[-2]["role"] == "assistant"
    assert segunda[-2]["tool_calls"][0]["function"]["name"] == "perfil"
    assert segunda[-1]["role"] == "tool"
    assert segunda[-1]["tool_call_id"] == "call_1"
    assert json.loads(segunda[-1]["content"]) == {"symbol": "IBM", "sector": "Tecnología"}


@pytest.mark.anyio
async def test_no_modifica_la_lista_de_mensajes_recibida(monkeypatch):
    monkeypatch.setattr(agents, "TOOLS", [])
    monkeypatch.setitem(tools.TOOL_REGISTRY, "x", lambda: {})
    _usar(monkeypatch, ClienteFalso(_pide_tool("x", "{}"), _texto("ok")))
    original = list(MENSAJES)

    await agents.ejecutar_agente(MENSAJES)

    assert MENSAJES == original


@pytest.mark.anyio
async def test_argumentos_con_json_invalido_se_informan_al_modelo(monkeypatch):
    cliente = ClienteFalso(_pide_tool("perfil", "{no es json"), _texto("Entendido"))
    _usar(monkeypatch, cliente)

    respuesta = await agents.ejecutar_agente(MENSAJES)

    assert respuesta == "Entendido"
    resultado_tool = cliente.llamadas[1]["messages"][-1]
    assert "error" in json.loads(resultado_tool["content"])


@pytest.mark.anyio
async def test_respeta_el_maximo_de_iteraciones(monkeypatch):
    monkeypatch.setitem(tools.TOOL_REGISTRY, "bucle", lambda: {"ok": True})
    cliente = ClienteFalso(*[_pide_tool("bucle", "{}") for _ in range(agents.MAX_ITERACIONES)])
    _usar(monkeypatch, cliente)

    with pytest.raises(ProveedorError, match="máximo de iteraciones"):
        await agents.ejecutar_agente(MENSAJES)

    assert len(cliente.llamadas) == agents.MAX_ITERACIONES


@pytest.mark.anyio
async def test_un_error_de_openai_se_convierte_en_proveedor_error(monkeypatch):
    _usar(monkeypatch, ClienteFalso(openai.OpenAIError("fallo interno con datos sensibles")))

    with pytest.raises(ProveedorError) as error:
        await agents.ejecutar_agente(MENSAJES)

    assert "sensibles" not in str(error.value)


@pytest.mark.anyio
async def test_un_contenido_vacio_devuelve_cadena_vacia(monkeypatch):
    _usar(monkeypatch, ClienteFalso(_texto(None)))

    assert await agents.ejecutar_agente(MENSAJES) == ""


@pytest.mark.anyio
async def test_reintenta_sin_reasoning_effort_si_el_modelo_lo_exige(monkeypatch):
    spec = [{"type": "function", "function": {"name": "x", "parameters": {"type": "object"}}}]
    monkeypatch.setattr(agents, "TOOLS", spec)
    cliente = ClienteFalso(_ErrorReasoningEffort("no soportado"), _texto("respuesta con tools"))
    _usar(monkeypatch, cliente)

    respuesta = await agents.ejecutar_agente(MENSAJES)

    assert respuesta == "respuesta con tools"
    assert len(cliente.llamadas) == 2
    assert "reasoning_effort" not in cliente.llamadas[0]
    assert cliente.llamadas[1]["reasoning_effort"] == "none"
    # El modelo queda recordado: la próxima vez ya no hace falta el primer intento fallido.
    assert settings.openai_model in agents._MODELOS_SIN_REASONING_EFFORT_EN_TOOLS


@pytest.mark.anyio
async def test_modelo_ya_recordado_evita_el_intento_fallido(monkeypatch):
    spec = [{"type": "function", "function": {"name": "x", "parameters": {"type": "object"}}}]
    monkeypatch.setattr(agents, "TOOLS", spec)
    agents._MODELOS_SIN_REASONING_EFFORT_EN_TOOLS.add(settings.openai_model)
    cliente = ClienteFalso(_texto("directo"))
    _usar(monkeypatch, cliente)

    respuesta = await agents.ejecutar_agente(MENSAJES)

    assert respuesta == "directo"
    assert len(cliente.llamadas) == 1
    assert cliente.llamadas[0]["reasoning_effort"] == "none"


@pytest.mark.anyio
async def test_otros_errores_de_openai_no_activan_el_reintento(monkeypatch):
    monkeypatch.setattr(agents, "TOOLS", [])
    _usar(monkeypatch, ClienteFalso(openai.OpenAIError("otro tipo de falla")))

    with pytest.raises(ProveedorError):
        await agents.ejecutar_agente(MENSAJES)


@pytest.mark.anyio
async def test_un_ciclo_que_nunca_termina_se_corta_por_el_techo_global(monkeypatch):
    """Si el modelo insiste en pedir la misma tool lenta, el usuario igual recibe una
    respuesta (un error) dentro de TIMEOUT_AGENTE_SEGUNDOS, sin esperar las 5 iteraciones
    completas a la duración real de la tool."""
    monkeypatch.setattr(agents, "TIMEOUT_AGENTE_SEGUNDOS", 0.05)
    monkeypatch.setattr(agents, "TOOLS", [{"type": "function", "function": {"name": "lenta"}}])

    async def tool_lenta(nombre, argumentos):
        await asyncio.sleep(5)
        return "{}"

    monkeypatch.setattr(agents, "ejecutar_tool", tool_lenta)
    _usar(monkeypatch, ClienteFalso(_pide_tool("lenta", "{}")))

    inicio = time.monotonic()
    with pytest.raises(ProveedorError, match="tardó demasiado"):
        await agents.ejecutar_agente(MENSAJES)
    duracion = time.monotonic() - inicio

    assert duracion < 4  # se cortó por el techo global, no esperó los 5s de la tool
