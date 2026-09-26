import asyncio
import json
import logging
import time
from functools import partial
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from app.models.comparativa import CategoriaGrafica, RespuestaGraficas
from app.services import visualization

logger = logging.getLogger(__name__)

router = APIRouter(tags=["comparativa"])

# Mismo criterio que app/services/tools.py: AlphaVantage puede tardar mucho sin que
# sea un error (se midió incluso "precio" — una sola llamada — tardando 150s con una
# clave real). Copia local (no se toca tools.py) del mismo patrón _en_hilo/timeout.
# "income"/"fcf" encadenan hasta 4/3 llamadas a AlphaVantage (utils.py las hace en
# serie, cada una con timeout propio de TIMEOUT_ALPHAVANTAGE_SEGUNDOS=100s), así que el
# timeout de categoría debe cubrir ese peor caso con margen, no solo una llamada suelta.
TIMEOUT_SEGUNDOS = 420
TIMEOUT_LARGO_SEGUNDOS = 850  # roic: vuelve a llamar income+fcf engineering por dentro (~8 llamadas)

CACHE_TTL_SEGUNDOS = 900  # 15 min, igual que app/services/alphavantage.py
_cache: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}

# La vista dual carga los dos lados casi al mismo tiempo (4 llamadas a AlphaVantage por
# lado, en "income"/"fcf"; el doble en "roic"). AlphaVantage confirmó el motivo exacto de
# los fallos al probar esto: "Burst pattern detected... no more than 5 requests per
# second" — con ambos lados en paralelo se supera ese límite y alguna llamada llega
# rechazada, lo que utils.py no distingue de un dato real y revienta con un KeyError
# confuso en vez de un error claro. Serializar aquí (un lado espera al otro) mantiene
# cada cadena de llamadas dentro del límite; no se toca utils.py.
_SEMAFORO_ALPHAVANTAGE = asyncio.Semaphore(1)


def _en_hilo(funcion_sincrona: Callable[..., Any], timeout_segundos: float) -> Callable[..., Any]:
    async def envoltura(ticker: str) -> Any:
        return await asyncio.wait_for(
            asyncio.to_thread(partial(funcion_sincrona, ticker)), timeout=timeout_segundos
        )

    return envoltura


# Cada categoría despacha a la función de visualization.py correspondiente. "precio"
# devuelve una sola figura (no una lista): se normaliza más abajo para que la respuesta
# siempre tenga la misma forma.
_DESPACHADORES: dict[str, Callable[[str], Any]] = {
    "income": _en_hilo(visualization.viz_income_engineering, TIMEOUT_SEGUNDOS),
    "fcf": _en_hilo(visualization.viz_fcf_engineering, TIMEOUT_SEGUNDOS),
    "roic": _en_hilo(visualization.viz_roic_engineering, TIMEOUT_LARGO_SEGUNDOS),
    "precio": _en_hilo(visualization.viz_price_history, TIMEOUT_SEGUNDOS),
}


@router.get("/comparativa/graficas", response_model=RespuestaGraficas)
async def obtener_graficas(
    ticker: str = Query(..., min_length=1, max_length=10),
    categoria: CategoriaGrafica = Query(...),
) -> RespuestaGraficas:
    """Gráficas de Plotly (app/services/visualization.py) para un ticker y una categoría.

    Pensado para la vista "Comparativa de compañías": se llama una vez por cada lado
    (izquierdo/derecho), cada uno con su propio ticker.
    """
    ticker = ticker.strip().upper()
    clave_cache = (ticker, categoria)
    en_cache = _cache.get(clave_cache)
    if en_cache and time.monotonic() - en_cache[0] < CACHE_TTL_SEGUNDOS:
        return RespuestaGraficas(figuras=en_cache[1])

    try:
        async with _SEMAFORO_ALPHAVANTAGE:
            resultado = await _DESPACHADORES[categoria](ticker)
    except Exception as error:  # noqa: BLE001 - se traduce a 502, no se propaga el detalle
        logger.warning("No se pudieron generar las gráficas de %s/%s: %s", ticker, categoria, type(error).__name__)
        raise HTTPException(
            status_code=502,
            detail="No fue posible generar las gráficas para esa compañía. Intente nuevamente.",
        ) from None

    figuras_crudas = resultado if isinstance(resultado, list) else [resultado]
    figuras = [json.loads(figura.to_json()) for figura in figuras_crudas]

    _cache[clave_cache] = (time.monotonic(), figuras)
    return RespuestaGraficas(figuras=figuras)
