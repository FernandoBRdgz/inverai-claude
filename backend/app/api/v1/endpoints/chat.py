from fastapi import APIRouter, HTTPException

from app.core.errors import ProveedorError
from app.models.chat import MensajeEntrada, RespuestaAsistente
from app.services.prompt import generar_respuesta

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=RespuestaAsistente)
async def enviar_mensaje(payload: MensajeEntrada) -> RespuestaAsistente:
    """Recibe el mensaje del usuario y responde con el asistente (services/prompt.py).

    Sin claves de OpenAI en .env responde en modo demostración (un saludo).
    Si OpenAI o AlphaVantage fallan, devuelve 502 y el frontend muestra su mensaje de error.
    """
    try:
        respuesta = await generar_respuesta(payload.mensaje)
    except ProveedorError:
        raise HTTPException(
            status_code=502,
            detail="No fue posible obtener una respuesta del asistente. Intente nuevamente.",
        ) from None
    return RespuestaAsistente(respuesta=respuesta)
