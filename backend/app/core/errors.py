class ConfiguracionFaltante(Exception):
    """Falta una variable de configuración necesaria (por ejemplo, una API key en .env)."""


class ProveedorError(Exception):
    """Falló un proveedor externo (OpenAI o AlphaVantage): red, cuota agotada, respuesta inválida."""
