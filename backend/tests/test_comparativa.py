import asyncio
import time
from types import SimpleNamespace

import pytest

from app.api.v1.endpoints import comparativa
from app.services import visualization


def _figura(valor: str = "x"):
    """Imita un go.Figure lo justo para el endpoint: solo necesita .to_json()."""
    return SimpleNamespace(to_json=lambda: f'{{"data": [], "layout": {{"title": "{valor}"}}}}')


@pytest.fixture(autouse=True)
def _sin_cache():
    comparativa._cache.clear()
    yield
    comparativa._cache.clear()


def test_categoria_invalida_da_422(client):
    respuesta = client.get("/api/v1/comparativa/graficas", params={"ticker": "AAPL", "categoria": "no-existe"})

    assert respuesta.status_code == 422


def test_income_despacha_a_viz_income_engineering_y_normaliza_a_lista(client, monkeypatch):
    recibidos = []

    def falso(ticker):
        recibidos.append(ticker)
        return [_figura("uno"), _figura("dos")]

    monkeypatch.setattr(visualization, "viz_income_engineering", falso)
    monkeypatch.setitem(comparativa._DESPACHADORES, "income", comparativa._en_hilo(falso, 5))

    respuesta = client.get("/api/v1/comparativa/graficas", params={"ticker": "aapl", "categoria": "income"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["figuras"]) == 2
    assert recibidos == ["AAPL"]  # se normaliza a mayúsculas


def test_precio_normaliza_una_sola_figura_a_lista_de_un_elemento(client, monkeypatch):
    def falso(ticker):
        return _figura("precio")

    monkeypatch.setitem(comparativa._DESPACHADORES, "precio", comparativa._en_hilo(falso, 5))

    cuerpo = client.get("/api/v1/comparativa/graficas", params={"ticker": "MSFT", "categoria": "precio"}).json()

    assert len(cuerpo["figuras"]) == 1


def test_una_falla_al_generar_las_graficas_da_502_sin_filtrar_detalles(client, monkeypatch):
    def falla(ticker):
        raise ValueError("detalle interno con la apikey=xyz")

    monkeypatch.setitem(comparativa._DESPACHADORES, "income", comparativa._en_hilo(falla, 5))

    respuesta = client.get("/api/v1/comparativa/graficas", params={"ticker": "AAPL", "categoria": "income"})

    assert respuesta.status_code == 502
    assert "apikey" not in respuesta.text


@pytest.mark.anyio
async def test_en_hilo_corta_por_timeout_en_vez_de_bloquear():
    # Igual que el equivalente en test_tools.py: se prueba el wrapper como coroutine
    # directa (no vía TestClient), que sí espera a que el hilo huérfano de time.sleep
    # termine al cerrar su propio loop, y falsearía la medición de tiempo.
    def lenta(ticker):
        time.sleep(5)
        return _figura()

    envuelta = comparativa._en_hilo(lenta, 0.05)

    inicio = time.monotonic()
    with pytest.raises(TimeoutError):
        await envuelta("AAPL")
    duracion = time.monotonic() - inicio

    assert duracion < 4  # se cortó por timeout, no esperó los 5s completos


def test_una_categoria_colgada_da_502(client, monkeypatch):
    def lenta(ticker):
        time.sleep(0.2)
        return _figura()

    monkeypatch.setitem(comparativa._DESPACHADORES, "fcf", comparativa._en_hilo(lenta, 0.05))

    respuesta = client.get("/api/v1/comparativa/graficas", params={"ticker": "AAPL", "categoria": "fcf"})

    assert respuesta.status_code == 502


def test_una_segunda_consulta_identica_sale_de_la_cache(client, monkeypatch):
    llamadas = []

    def falso(ticker):
        llamadas.append(ticker)
        return [_figura()]

    monkeypatch.setitem(comparativa._DESPACHADORES, "roic", comparativa._en_hilo(falso, 5))

    client.get("/api/v1/comparativa/graficas", params={"ticker": "AAPL", "categoria": "roic"})
    client.get("/api/v1/comparativa/graficas", params={"ticker": "AAPL", "categoria": "roic"})

    assert len(llamadas) == 1

    client.get("/api/v1/comparativa/graficas", params={"ticker": "MSFT", "categoria": "roic"})
    assert len(llamadas) == 2  # otro ticker: consulta distinta


def test_roic_tiene_un_timeout_mas_largo():
    assert comparativa.TIMEOUT_LARGO_SEGUNDOS > comparativa.TIMEOUT_SEGUNDOS


@pytest.mark.anyio
async def test_las_llamadas_a_alphavantage_se_serializan_entre_lados(monkeypatch):
    # Regresión: la vista dual pedía ambos lados a la vez, AlphaVantage respondía
    # "Burst pattern detected... no more than 5 requests per second" para alguna de
    # las llamadas, y utils.py lo confundía con datos reales (KeyError). El semáforo
    # debe garantizar que nunca haya dos despachos en curso al mismo tiempo.
    activos = 0
    maximo_concurrente = 0

    async def lenta(ticker):
        nonlocal activos, maximo_concurrente
        activos += 1
        maximo_concurrente = max(maximo_concurrente, activos)
        await asyncio.sleep(0.05)
        activos -= 1
        return _figura()

    monkeypatch.setitem(comparativa._DESPACHADORES, "income", lenta)

    await asyncio.gather(
        comparativa.obtener_graficas(ticker="AAPL", categoria="income"),
        comparativa.obtener_graficas(ticker="MSFT", categoria="income"),
    )

    assert maximo_concurrente == 1
