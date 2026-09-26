"""Cliente fino de AlphaVantage (https://www.alphavantage.co/documentation/).

`consultar()` es genérico: sirve para cualquier `function` de la API. Los wrappers de
abajo (symbol_search, company_overview, global_quote) son atajos para las consultas
más comunes sobre compañías; agrega los tuyos siguiendo el mismo patrón.
"""

import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import ConfiguracionFaltante, ProveedorError

BASE_URL = "https://www.alphavantage.co/query"
TIMEOUT_SEGUNDOS = 10.0

# AlphaVantage responde HTTP 200 incluso cuando algo falla; el aviso llega en el JSON
# bajo alguna de estas claves (cuota agotada, parámetros inválidos, etc.).
_CLAVES_DE_ERROR = ("Error Message", "Note", "Information")

# Caché en memoria (por proceso) para ahorrar cuota: {clave: (instante, datos)}.
_cache: dict[tuple, tuple[float, dict[str, Any]]] = {}

# Permite a los tests inyectar un httpx.MockTransport y no salir a internet.
_transport: httpx.AsyncBaseTransport | None = None


async def consultar(function: str, **params: Any) -> dict[str, Any]:
    """Llama a AlphaVantage con `function` y `params`, e inyecta la apikey desde settings.

    Lanza ConfiguracionFaltante si no hay ALPHAVANTAGE_API_KEY y ProveedorError ante
    fallas de red, respuestas no JSON o avisos de error/cuota del proveedor.
    """
    if not settings.alphavantage_configurado:
        raise ConfiguracionFaltante("Falta ALPHAVANTAGE_API_KEY en el archivo .env")

    clave_cache = (function, tuple(sorted(params.items())))
    guardado = _cache.get(clave_cache)
    if guardado and time.monotonic() - guardado[0] < settings.alphavantage_cache_ttl:
        return guardado[1]

    consulta = {"function": function, **params, "apikey": settings.alphavantage_api_key.get_secret_value()}  # type: ignore[union-attr]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEGUNDOS, transport=_transport) as cliente:
            respuesta = await cliente.get(BASE_URL, params=consulta)
            respuesta.raise_for_status()
            datos = respuesta.json()
    except (httpx.HTTPError, ValueError) as error:
        # Se registra solo el tipo de error: la URL de httpx incluiría la apikey.
        raise ProveedorError(f"AlphaVantage no respondió correctamente ({type(error).__name__})") from None

    if not isinstance(datos, dict):
        raise ProveedorError("AlphaVantage devolvió una respuesta con formato inesperado")
    for clave in _CLAVES_DE_ERROR:
        if clave in datos:
            raise ProveedorError(f"AlphaVantage: {datos[clave]}")

    _cache[clave_cache] = (time.monotonic(), datos)
    return datos


async def symbol_search(keywords: str) -> dict[str, Any]:
    """Busca símbolos bursátiles por nombre o palabras clave (SYMBOL_SEARCH)."""
    return await consultar("SYMBOL_SEARCH", keywords=keywords)


async def company_overview(symbol: str) -> dict[str, Any]:
    """Perfil y fundamentales de una compañía: descripción, sector, capitalización, ratios (OVERVIEW)."""
    return await consultar("OVERVIEW", symbol=symbol)


async def global_quote(symbol: str) -> dict[str, Any]:
    """Última cotización de un símbolo (GLOBAL_QUOTE)."""
    return await consultar("GLOBAL_QUOTE", symbol=symbol)
