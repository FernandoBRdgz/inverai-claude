"""Ciclo del agente: llama a OpenAI, ejecuta las tools que pida el modelo y repite.

Esta es la implementación POR DEFECTO (Chat Completions + function calling). Si tu agente
usa otro esquema (varios agentes, OpenAI Agents SDK, Responses API...), reemplaza el
contenido de `ejecutar_agente()` manteniendo su firma: recibe la lista de mensajes ya
armada por prompt.py y devuelve el texto final para el usuario.
"""

import asyncio
import json
import logging
from typing import Any

from openai import OpenAIError

from app.core.config import settings
from app.core.errors import ProveedorError
from app.services.openai_client import get_client
from app.services.tools import TOOLS, ejecutar_tool

logger = logging.getLogger(__name__)

# Tope de vueltas modelo → tools → modelo, para evitar ciclos infinitos y gasto descontrolado.
MAX_ITERACIONES = 5

# Techo de tiempo TOTAL de la conversación con el modelo (todas las iteraciones y tools
# juntas). Sin esto, si el modelo repite una tool lenta varias veces, el usuario puede
# quedarse sin respuesta más de 15-20 minutos (MAX_ITERACIONES × el tope de la tool más
# lenta) en vez de recibir, como mínimo, un error a tiempo. Los tests financieros de
# tools.py ya limitan cada llamada individual; este límite cubre la suma de todas.
TIMEOUT_AGENTE_SEGUNDOS = 260

# Algunos modelos (los que razonan) rechazan function tools en /chat/completions salvo que
# se fije reasoning_effort="none" (el error de OpenAI trae param="reasoning_effort"). Se
# detecta en el primer fallo y se recuerda por modelo, para no repetir la llamada fallida
# en cada mensaje.
_MODELOS_SIN_REASONING_EFFORT_EN_TOOLS: set[str] = set()


async def _crear_completion(cliente: Any, modelo: str, mensajes: list[dict[str, Any]], opciones: dict[str, Any]):
    kwargs = dict(opciones)
    if modelo in _MODELOS_SIN_REASONING_EFFORT_EN_TOOLS and "tools" in kwargs:
        kwargs.setdefault("reasoning_effort", "none")
    try:
        return await cliente.chat.completions.create(model=modelo, messages=mensajes, **kwargs)
    except OpenAIError as error:
        if "reasoning_effort" not in kwargs and getattr(error, "param", None) == "reasoning_effort":
            logger.info("El modelo %s no admite tools con razonamiento activo; reintentando sin él", modelo)
            _MODELOS_SIN_REASONING_EFFORT_EN_TOOLS.add(modelo)
            kwargs["reasoning_effort"] = "none"
            return await cliente.chat.completions.create(model=modelo, messages=mensajes, **kwargs)
        raise


async def ejecutar_agente(mensajes: list[dict[str, Any]]) -> str:
    """Devuelve la respuesta final del modelo, resolviendo antes las tool_calls que solicite.

    Acota el tiempo total (ver TIMEOUT_AGENTE_SEGUNDOS): el usuario siempre recibe una
    respuesta o un error dentro de ese plazo, sin importar cuántas iteraciones haga el
    modelo ni cuánto tarden las tools.
    """
    try:
        return await asyncio.wait_for(_ejecutar_agente(mensajes), timeout=TIMEOUT_AGENTE_SEGUNDOS)
    except TimeoutError:
        logger.warning("El asistente superó el tiempo máximo total (%ss)", TIMEOUT_AGENTE_SEGUNDOS)
        raise ProveedorError("El asistente tardó demasiado en responder") from None


async def _ejecutar_agente(mensajes: list[dict[str, Any]]) -> str:
    cliente = get_client()
    conversacion = list(mensajes)
    opciones: dict[str, Any] = {"tools": TOOLS} if TOOLS else {}

    for _ in range(MAX_ITERACIONES):
        try:
            respuesta = await _crear_completion(cliente, settings.openai_model, conversacion, opciones)
        except OpenAIError as error:
            logger.warning("OpenAI falló: %s", type(error).__name__)
            raise ProveedorError(f"OpenAI no respondió correctamente ({type(error).__name__})") from None

        mensaje = respuesta.choices[0].message
        llamadas = mensaje.tool_calls or []
        if not llamadas:
            return mensaje.content or ""

        # El modelo pidió herramientas: se registra su turno y luego cada resultado.
        conversacion.append(
            {
                "role": "assistant",
                "content": mensaje.content,
                "tool_calls": [
                    {
                        "id": llamada.id,
                        "type": "function",
                        "function": {
                            "name": llamada.function.name,
                            "arguments": llamada.function.arguments,
                        },
                    }
                    for llamada in llamadas
                ],
            }
        )
        for llamada in llamadas:
            try:
                argumentos = json.loads(llamada.function.arguments or "{}")
                resultado = await ejecutar_tool(llamada.function.name, argumentos)
            except json.JSONDecodeError:
                resultado = json.dumps({"error": "Los argumentos no son un JSON válido"})
            conversacion.append({"role": "tool", "tool_call_id": llamada.id, "content": resultado})

    raise ProveedorError("El asistente superó el máximo de iteraciones con herramientas")
