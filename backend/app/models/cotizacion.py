from pydantic import BaseModel


class Cotizacion(BaseModel):
    """Último precio de un ticker, para autocompletar "Precio por acción" al dar de
    alta una posición en el portafolio (el usuario ya no lo escribe a mano)."""

    ticker: str
    precio: float
