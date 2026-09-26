from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# El .env vive en backend/ y se resuelve desde aquí, no desde el directorio de trabajo,
# así funciona igual si uvicorn/pytest se lanzan desde otra carpeta.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno (.env)."""

    # Ajustes propios de la app: llevan el prefijo INVERAI_ (p. ej. INVERAI_ORIGENES_CORS).
    proyecto: str = "Inver-AI API"
    origenes_cors: list[str] = ["http://localhost:4200"]
    alphavantage_cache_ttl: int = 900  # segundos

    # Claves de proveedores: usan los nombres estándar, SIN prefijo (validation_alias
    # hace que env_prefix no se aplique). SecretStr evita filtrarlas en logs o repr().
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    alphavantage_api_key: SecretStr | None = Field(
        default=None, validation_alias="ALPHAVANTAGE_API_KEY"
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="INVERAI_",
        extra="ignore",  # el .env puede traer claves ajenas a este modelo
    )

    @property
    def openai_configurado(self) -> bool:
        """True si hay una clave de OpenAI no vacía. Si es False, el asistente va en modo demostración."""
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value().strip())

    @property
    def alphavantage_configurado(self) -> bool:
        return bool(
            self.alphavantage_api_key and self.alphavantage_api_key.get_secret_value().strip()
        )


settings = Settings()
