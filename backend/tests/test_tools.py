import json
import time

import pytest

from app.services import tools, utils


@pytest.mark.anyio
async def test_ejecuta_una_tool_async_y_devuelve_json(monkeypatch):
    async def perfil(symbol: str):
        return {"symbol": symbol, "sector": "Tecnología"}

    monkeypatch.setitem(tools.TOOL_REGISTRY, "perfil", perfil)

    resultado = await tools.ejecutar_tool("perfil", {"symbol": "IBM"})

    assert json.loads(resultado) == {"symbol": "IBM", "sector": "Tecnología"}


@pytest.mark.anyio
async def test_tambien_admite_tools_sincronas(monkeypatch):
    monkeypatch.setitem(tools.TOOL_REGISTRY, "suma", lambda a, b: {"total": a + b})

    resultado = await tools.ejecutar_tool("suma", {"a": 2, "b": 3})

    assert json.loads(resultado) == {"total": 5}


@pytest.mark.anyio
async def test_una_tool_desconocida_devuelve_error_en_vez_de_lanzar():
    resultado = json.loads(await tools.ejecutar_tool("no_existe", {}))

    assert "no_existe" in resultado["error"]


@pytest.mark.anyio
async def test_una_excepcion_en_la_tool_devuelve_error_sin_detalles_internos(monkeypatch):
    def rota(**_):
        raise RuntimeError("detalle interno sensible")

    monkeypatch.setitem(tools.TOOL_REGISTRY, "rota", rota)

    resultado = await tools.ejecutar_tool("rota", {})

    assert "error" in json.loads(resultado)
    assert "detalle interno sensible" not in resultado


@pytest.mark.anyio
async def test_argumentos_incorrectos_devuelven_error(monkeypatch):
    monkeypatch.setitem(tools.TOOL_REGISTRY, "suma", lambda a, b: a + b)

    resultado = await tools.ejecutar_tool("suma", {"a": 1, "parametro_inesperado": 2})

    assert "error" in json.loads(resultado)


# --- Herramientas de datos financieros (adaptadas de utils.py/tooling.py) -----------

def test_cada_tool_declarada_tiene_su_funcion_registrada():
    nombres_declarados = {t["function"]["name"] for t in tools.TOOLS}
    assert nombres_declarados <= tools.TOOL_REGISTRY.keys()
    assert nombres_declarados == {
        "get_intrinsic_value",
        "get_income_statement",
        "get_balance_sheet",
        "get_cashflow_statement",
        "get_earnings",
        "get_call_transcripts",
    }


@pytest.mark.anyio
async def test_get_income_statement_delega_en_utils_y_no_bloquea(monkeypatch):
    recibidos = {}

    def falso_get_income_statement(**kwargs):
        recibidos.update(kwargs)
        return {"totalRevenue": {"0": "123"}}

    monkeypatch.setattr(utils, "get_income_statement", falso_get_income_statement)
    # El wrapper ya capturó la referencia original al construir TOOL_REGISTRY (import time);
    # se reconstruye aquí para probar el mismo mecanismo de envoltura con el reemplazo.
    monkeypatch.setitem(tools.TOOL_REGISTRY, "get_income_statement", tools._en_hilo(falso_get_income_statement))

    resultado = await tools.ejecutar_tool(
        "get_income_statement", {"ticker": "AAPL", "period": "anual"}
    )

    assert recibidos == {"ticker": "AAPL", "period": "anual"}
    assert json.loads(resultado) == {"totalRevenue": {"0": "123"}}


@pytest.mark.anyio
async def test_una_falla_de_red_en_una_tool_financiera_no_se_propaga(monkeypatch):
    import requests

    def falla(**_):
        raise requests.exceptions.ConnectionError("sin red")

    monkeypatch.setitem(tools.TOOL_REGISTRY, "get_balance_sheet", tools._en_hilo(falla))

    resultado = await tools.ejecutar_tool("get_balance_sheet", {"ticker": "AAPL", "period": "anual"})

    assert "error" in json.loads(resultado)


@pytest.mark.anyio
async def test_una_tool_colgada_se_corta_por_timeout_en_vez_de_bloquear(monkeypatch):
    def lenta(**_):
        time.sleep(5)
        return {"nunca_deberia_verse": True}

    monkeypatch.setitem(tools.TOOL_REGISTRY, "lenta", tools._en_hilo(lenta, timeout_segundos=0.05))

    inicio = time.monotonic()
    resultado = await tools.ejecutar_tool("lenta", {})
    duracion = time.monotonic() - inicio

    assert duracion < 4  # se cortó por timeout, no esperó los 5s completos
    assert "error" in json.loads(resultado)


def test_get_intrinsic_value_tiene_un_timeout_mas_largo():
    # Encadena varias llamadas a AlphaVantage; necesita más margen que las demás.
    assert tools.TIMEOUT_TOOL_LARGO_SEGUNDOS > tools.TIMEOUT_TOOL_SEGUNDOS
