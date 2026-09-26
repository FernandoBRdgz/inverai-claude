"""Function tools que el modelo puede invocar (function calling).

Dos piezas que debes mantener sincronizadas:
  1. TOOLS          → las definiciones (JSON Schema) que se le envían a OpenAI.
  2. TOOL_REGISTRY  → nombre de la tool → función Python que la ejecuta.

`ejecutar_tool()` es el despachador que usa el agente: no necesitas tocarlo.

Las tools de datos financieros (abajo) están adaptadas de app/services/utils.py y de las
especificaciones que traía app/services/tooling.py. Ese archivo (tooling.py) traía también
su propio dispatcher (`handle_tool_calls`) y usaba `from utils import ...` como import de
nivel superior; ambas cosas quedan reemplazadas aquí: el dispatcher ya existe en
`ejecutar_tool()`/`agents.py`, y el import correcto dentro del paquete es
`from app.services import utils`. tooling.py se deja intacto en el repo por si quieres
consultarlo, pero ya no se importa desde ningún lado.

Las funciones de utils.py son síncronas y bloqueantes (usan `requests` y `pandas`), así que
cada una se ejecuta en un hilo aparte (`asyncio.to_thread`) para no congelar el servidor
mientras espera la respuesta de AlphaVantage/OpenAI.
"""

import asyncio
import inspect
import json
import logging
from collections.abc import Callable
from functools import partial
from typing import Any

from app.services import utils

logger = logging.getLogger(__name__)

# >>> PEGA AQUÍ tus function tools (formato Chat Completions) ---------------------
# Definiciones adaptadas literalmente de tooling.py (mismo nombre, descripción y parámetros).
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_intrinsic_value",
            "description": (
                "Usa esta herramienta (tool) para obtener el valor intrínseco de la compañía "
                "solicitado por el usuario. Evita cálculos ajenos a la herramienta proporcionada "
                "como WACC, DFC, entre otros. Contrasta siempre con el precio final que también "
                "provee la herramienta para dar insights sin ser recomendación de compra o venta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "El TICKER de la compañía a analizar."},
                },
                "required": ["ticker"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_income_statement",
            "description": "Usa esta herramienta para obtener cualquier dato contenido en el estado de resultados de la companía que solicite el usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "El TICKER de la compañía a analizar."},
                    "period": {
                        "type": "string",
                        "enum": ["anual", "trimestral"],
                        "description": "Periodo del reporte a consultar, anual o trimestral.",
                    },
                },
                "required": ["ticker", "period"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_balance_sheet",
            "description": "Usa esta herramienta para obtener cualquier dato contenido en el balance general de la companía que solicite el usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "El TICKER de la compañía a analizar."},
                    "period": {
                        "type": "string",
                        "enum": ["anual", "trimestral"],
                        "description": "Periodo del reporte a consultar, anual o trimestral.",
                    },
                },
                "required": ["ticker", "period"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cashflow_statement",
            "description": "Usa esta herramienta para obtener cualquier dato contenido en el flujo de efectivo de la companía que solicite el usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "El TICKER de la compañía a analizar."},
                    "period": {
                        "type": "string",
                        "enum": ["anual", "trimestral"],
                        "description": "Periodo del reporte a consultar, anual o trimestral.",
                    },
                },
                "required": ["ticker", "period"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings",
            "description": "Usa esta herramienta para obtener cualquier dato contenido en los resultados de ganancias por acción de la companía que solicite el usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "El TICKER de la compañía a analizar."},
                    "period": {
                        "type": "string",
                        "enum": ["anual", "trimestral"],
                        "description": "Periodo del reporte a consultar, anual o trimestral.",
                    },
                },
                "required": ["ticker", "period"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_call_transcripts",
            "description": "Usa esta herramienta (tool) para obtener insights clave de una transcripción de earnings call",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "El TICKER de la compañía a analizar."},
                    "quarter": {
                        "type": "string",
                        "description": "El trimestre de transcripciones de la llamada con Inversionistas",
                    },
                },
                "required": ["ticker", "quarter"],
                "additionalProperties": False,
            },
        },
    },
]
# <<< FIN -------------------------------------------------------------------------


# AlphaVantage (plan gratuito) puede tardar mucho en responder sin que sea un error: se
# midió entre ~30s y ~100s para un solo estado financiero con una clave real, en momentos
# distintos. get_intrinsic_value encadena ~10 llamadas de este tipo. El límite evita que una
# llamada realmente colgada bloquee el hilo para siempre; si lo ves saltar seguido con
# respuestas normales (no colgadas), súbelo aquí.
TIMEOUT_TOOL_SEGUNDOS = 90
TIMEOUT_TOOL_LARGO_SEGUNDOS = 240  # get_intrinsic_value: encadena ~10 llamadas a AlphaVantage


def _en_hilo(funcion_sincrona: Callable[..., Any], timeout_segundos: float = TIMEOUT_TOOL_SEGUNDOS) -> Callable[..., Any]:
    """Envuelve una función síncrona y bloqueante (requests/pandas) para llamarla sin
    congelar el event loop: corre en un hilo aparte vía asyncio.to_thread, con límite de tiempo."""

    async def envoltura(**kwargs: Any) -> Any:
        return await asyncio.wait_for(
            asyncio.to_thread(partial(funcion_sincrona, **kwargs)), timeout=timeout_segundos
        )

    envoltura.__name__ = getattr(funcion_sincrona, "__name__", "funcion")
    return envoltura


# >>> PEGA AQUÍ el registro nombre → función (puede ser async o normal) ------------
TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "get_intrinsic_value": _en_hilo(utils.get_intrinsic_value, timeout_segundos=TIMEOUT_TOOL_LARGO_SEGUNDOS),
    "get_income_statement": _en_hilo(utils.get_income_statement),
    "get_balance_sheet": _en_hilo(utils.get_balance_sheet),
    "get_cashflow_statement": _en_hilo(utils.get_cashflow_statement),
    "get_earnings": _en_hilo(utils.get_earnings),
    "get_call_transcripts": _en_hilo(utils.get_call_transcripts),
}
# <<< FIN -------------------------------------------------------------------------


async def ejecutar_tool(nombre: str, argumentos: dict[str, Any]) -> str:
    """Ejecuta la tool `nombre` y devuelve su resultado como texto JSON.

    Nunca lanza: ante una tool desconocida o una excepción devuelve {"error": ...} para
    que el modelo pueda recuperarse (reintentar, pedir aclaración o responder sin ella).
    """
    funcion = TOOL_REGISTRY.get(nombre)
    if funcion is None:
        return json.dumps({"error": f"Herramienta desconocida: {nombre}"}, ensure_ascii=False)
    try:
        logger.info("Llamando a la herramienta %s con %s", nombre, argumentos)
        resultado = funcion(**argumentos)
        if inspect.isawaitable(resultado):
            resultado = await resultado
    except Exception as error:  # noqa: BLE001 - se informa al modelo, no se propaga
        logger.warning("La herramienta %s falló: %s", nombre, type(error).__name__)
        return json.dumps(
            {"error": f"La herramienta {nombre} no pudo completarse ({type(error).__name__})"},
            ensure_ascii=False,
        )
    return json.dumps(resultado, ensure_ascii=False, default=str)
