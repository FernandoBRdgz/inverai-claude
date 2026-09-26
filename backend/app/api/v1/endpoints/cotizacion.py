from fastapi import APIRouter, HTTPException, Query

from app.core.errors import ConfiguracionFaltante, ProveedorError
from app.models.cotizacion import Cotizacion
from app.services import alphavantage

router = APIRouter(tags=["cotizacion"])


@router.get("/cotizacion", response_model=Cotizacion)
async def obtener_cotizacion(ticker: str = Query(..., min_length=1, max_length=10)) -> Cotizacion:
    """Último precio de un ticker (AlphaVantage GLOBAL_QUOTE) — usa app/services/alphavantage.py,
    que ya cachea 15 min y detecta avisos de cuota/error del proveedor.

    Pensado para "Mi portafolio": el usuario solo elige la empresa y cuántas acciones tiene;
    el ticker y el precio se completan solos a partir de esta consulta.
    """
    ticker = ticker.strip().upper()
    try:
        datos = await alphavantage.global_quote(ticker)
    except (ConfiguracionFaltante, ProveedorError):
        raise HTTPException(
            status_code=502,
            detail="No fue posible obtener la cotización de esa compañía. Intente nuevamente.",
        ) from None

    cotizacion = datos.get("Global Quote") or {}
    precio_texto = cotizacion.get("05. price")
    if not precio_texto:
        raise HTTPException(
            status_code=502,
            detail="AlphaVantage no devolvió una cotización para ese ticker.",
        )
    try:
        precio = float(precio_texto)
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="La cotización recibida no tiene un formato válido.",
        ) from None

    return Cotizacion(ticker=ticker, precio=precio)
