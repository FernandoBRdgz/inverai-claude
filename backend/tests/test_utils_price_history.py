from types import SimpleNamespace

from app.services import utils


def test_get_price_history_devuelve_la_serie_completa_indexada_por_fecha(monkeypatch):
    respuesta_alphavantage = {
        "Monthly Adjusted Time Series": {
            "2024-02-29": {"5. adjusted close": "185.50"},
            "2024-01-31": {"5. adjusted close": "180.00"},
        }
    }
    monkeypatch.setattr(
        utils.requests, "get", lambda url: SimpleNamespace(json=lambda: respuesta_alphavantage)
    )

    serie = utils.get_price_history("AAPL")

    assert list(serie.columns) == ["adjusted_close"]
    assert len(serie) == 2
    assert serie["adjusted_close"].iloc[0] == 180.00  # ordenado ascendente por fecha
    assert serie["adjusted_close"].iloc[-1] == 185.50


def test_get_price_history_lanza_si_alphavantage_no_trae_la_serie(monkeypatch):
    monkeypatch.setattr(
        utils.requests, "get", lambda url: SimpleNamespace(json=lambda: {"Note": "cuota agotada"})
    )

    try:
        utils.get_price_history("AAPL")
        assert False, "debía lanzar ValueError"
    except ValueError:
        pass
