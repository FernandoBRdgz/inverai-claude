from pydantic import BaseModel, Field


class MensajeEntrada(BaseModel):
    """Mensaje que el usuario escribe en el chat."""

    mensaje: str = Field(..., min_length=1, max_length=1000)


class RespuestaAsistente(BaseModel):
    """Respuesta que el asistente devuelve al frontend."""

    respuesta: str
