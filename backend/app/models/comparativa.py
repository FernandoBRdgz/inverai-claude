from typing import Any, Literal

from pydantic import BaseModel

CategoriaGrafica = Literal["income", "fcf", "roic", "precio"]


class RespuestaGraficas(BaseModel):
    """Una o varias figuras de Plotly, ya serializadas (dict con "data"/"layout"),
    listas para pasarle a Plotly.js en el frontend tal cual."""

    figuras: list[dict[str, Any]]
