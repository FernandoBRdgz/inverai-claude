import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.core.errors import ConfiguracionFaltante, ProveedorError
from app.services import alphavantage

CLAVE = "av-clave-de-prueba"


@pytest.fixture
def con_clave(monkeypatch):
    monkeypatch.setattr(settings, "alphavantage_api_key", SecretStr(CLAVE))


def _simular(monkeypatch, manejador):
    """Reemplaza la red de AlphaVantage por `manejador(request) -> httpx.Response`."""
    monkeypatch.setattr(alphavantage, "_transport", httpx.MockTransport(manejador))


@pytest.mark.anyio
async def test_sin_clave_lanza_configuracion_faltante():
    with pytest.raises(ConfiguracionFaltante):
        await alphavantage.consultar("OVERVIEW", symbol="IBM")


@pytest.mark.anyio
async def test_envia_function_parametros_y_apikey(con_clave, monkeypatch):
    recibidos = []

    def manejador(request: httpx.Request) -> httpx.Response:
        recibidos.append(dict(request.url.params))
        return httpx.Response(200, json={"Symbol": "IBM"})

    _simular(monkeypatch, manejador)

    datos = await alphavantage.company_overview("IBM")

    assert datos == {"Symbol": "IBM"}
    assert recibidos == [{"function": "OVERVIEW", "symbol": "IBM", "apikey": CLAVE}]


@pytest.mark.anyio
@pytest.mark.parametrize("clave_de_error", ["Error Message", "Note", "Information"])
async def test_los_avisos_del_proveedor_se_convierten_en_error(con_clave, monkeypatch, clave_de_error):
    # AlphaVantage responde 200 aun cuando falla (cuota agotada, símbolo inválido, etc.).
    _simular(monkeypatch, lambda request: httpx.Response(200, json={clave_de_error: "Detalle del aviso"}))

    with pytest.raises(ProveedorError, match="Detalle del aviso"):
        await alphavantage.consultar("OVERVIEW", symbol="XXXX")


@pytest.mark.anyio
async def test_error_http_no_filtra_la_apikey(con_clave, monkeypatch):
    _simular(monkeypatch, lambda request: httpx.Response(500, text="fallo"))

    with pytest.raises(ProveedorError) as error:
        await alphavantage.consultar("OVERVIEW", symbol="IBM")

    assert CLAVE not in str(error.value)


@pytest.mark.anyio
@pytest.mark.parametrize("cuerpo", [b"esto no es json", b"[1, 2, 3]"])
async def test_respuestas_con_formato_inesperado_son_error(con_clave, monkeypatch, cuerpo):
    _simular(monkeypatch, lambda request: httpx.Response(200, content=cuerpo))

    with pytest.raises(ProveedorError):
        await alphavantage.consultar("OVERVIEW", symbol="IBM")


@pytest.mark.anyio
async def test_una_segunda_consulta_identica_sale_de_la_cache(con_clave, monkeypatch):
    llamadas = []

    def manejador(request: httpx.Request) -> httpx.Response:
        llamadas.append(request)
        return httpx.Response(200, json={"Symbol": "IBM"})

    _simular(monkeypatch, manejador)

    await alphavantage.global_quote("IBM")
    await alphavantage.global_quote("IBM")
    assert len(llamadas) == 1

    await alphavantage.global_quote("AAPL")  # otro símbolo: consulta distinta
    assert len(llamadas) == 2


@pytest.mark.anyio
async def test_los_errores_no_se_guardan_en_cache(con_clave, monkeypatch):
    respuestas = [{"Note": "cuota agotada"}, {"Symbol": "IBM"}]
    _simular(monkeypatch, lambda request: httpx.Response(200, json=respuestas.pop(0)))

    with pytest.raises(ProveedorError):
        await alphavantage.consultar("OVERVIEW", symbol="IBM")

    assert await alphavantage.consultar("OVERVIEW", symbol="IBM") == {"Symbol": "IBM"}
