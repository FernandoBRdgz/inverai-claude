from pydantic import BaseModel


class EstadoSalud(BaseModel):
    """Estado operativo del backend: sirve para que un panel de administración
    muestre si el asistente está bien configurado, sin exponer ninguna clave."""

    status: str
    openai_configurado: bool
    alphavantage_configurado: bool
    modelo: str
