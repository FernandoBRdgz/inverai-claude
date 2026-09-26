from app.core.errors import ConfiguracionFaltante, ProveedorError
from app.services import alphavantage


def test_devuelve_el_precio_de_alphavantage(client, monkeypatch):
    async def falso(symbol):
        assert symbol == "AAPL"
        return {"Global Quote": {"05. price": "230.7700"}}

    monkeypatch.setattr(alphavantage, "global_quote", falso)

    respuesta = client.get("/api/v1/cotizacion", params={"ticker": "aapl"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ticker": "AAPL", "precio": 230.77}


def test_error_del_proveedor_da_502_sin_filtrar_detalles(client, monkeypatch):
    async def falla(symbol):
        raise ProveedorError("AlphaVantage: Note - cuota agotada, apikey=xyz-secreta")

    monkeypatch.setattr(alphavantage, "global_quote", falla)

    respuesta = client.get("/api/v1/cotizacion", params={"ticker": "AAPL"})

    assert respuesta.status_code == 502
    assert "xyz-secreta" not in respuesta.text


def test_sin_clave_configurada_da_502(client, monkeypatch):
    async def falla(symbol):
        raise ConfiguracionFaltante("Falta ALPHAVANTAGE_API_KEY")

    monkeypatch.setattr(alphavantage, "global_quote", falla)

    respuesta = client.get("/api/v1/cotizacion", params={"ticker": "AAPL"})

    assert respuesta.status_code == 502


def test_respuesta_sin_precio_da_502(client, monkeypatch):
    async def sin_precio(symbol):
        return {"Global Quote": {}}  # ticker inválido: AlphaVantage devuelve un objeto vacío

    monkeypatch.setattr(alphavantage, "global_quote", sin_precio)

    respuesta = client.get("/api/v1/cotizacion", params={"ticker": "NOEXISTE"})

    assert respuesta.status_code == 502


def test_ticker_vacio_da_422(client):
    respuesta = client.get("/api/v1/cotizacion", params={"ticker": ""})

    assert respuesta.status_code == 422
