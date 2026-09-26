"""Cliente de OpenAI, creado una sola vez con la API key de settings (.env)."""

from functools import lru_cache

import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.errors import ConfiguracionFaltante

# El SDK por defecto usa un timeout de lectura de 600s (con max_retries=2). Un modelo con
# razonamiento tardando en sintetizar una respuesta larga (con tools) puede tardar más de
# un minuto de forma legítima: medimos respuestas reales de 65-157s. Un timeout más corto
# aquí no "corrige" nada — el SDK lo trata como fallo transitorio y reintenta en silencio
# (hasta 3 intentos), sumando minutos en vez de ahorrarlos. El único límite real que debe
# sentir el usuario es TIMEOUT_AGENTE_SEGUNDOS en agents.py; aquí solo se acota el connect
# (para fallar rápido si OpenAI es inalcanzable) y se deja un read generoso.
TIMEOUT = httpx.Timeout(connect=10.0, read=280.0, write=280.0, pool=280.0)


@lru_cache(maxsize=1)
def get_client() -> AsyncOpenAI:
    """Devuelve el AsyncOpenAI compartido. Lanza ConfiguracionFaltante si no hay OPENAI_API_KEY."""
    if not settings.openai_configurado:
        raise ConfiguracionFaltante("Falta OPENAI_API_KEY en el archivo .env")
    return AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),  # type: ignore[union-attr]
        timeout=TIMEOUT,
    )
