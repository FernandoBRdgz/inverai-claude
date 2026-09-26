from app.core.config import Settings

NOMBRES_DE_CLAVES = ("OPENAI_API_KEY", "OPENAI_MODEL", "ALPHAVANTAGE_API_KEY", "INVERAI_ALPHAVANTAGE_CACHE_TTL")


def _sin_variables_de_entorno(monkeypatch):
    for nombre in NOMBRES_DE_CLAVES:
        monkeypatch.delenv(nombre, raising=False)


def test_lee_las_claves_sin_prefijo_desde_el_env(tmp_path, monkeypatch):
    _sin_variables_de_entorno(monkeypatch)
    env = tmp_path / ".env"
    env.write_text(
        "OPENAI_API_KEY=sk-de-prueba\n"
        "OPENAI_MODEL=modelo-de-prueba\n"
        "ALPHAVANTAGE_API_KEY=av-de-prueba\n"
        "INVERAI_ALPHAVANTAGE_CACHE_TTL=5\n"
        "VARIABLE_AJENA=ignorada\n"  # no debe romper la carga (extra="ignore")
    )

    ajustes = Settings(_env_file=env)

    assert ajustes.openai_api_key.get_secret_value() == "sk-de-prueba"
    assert ajustes.alphavantage_api_key.get_secret_value() == "av-de-prueba"
    assert ajustes.openai_model == "modelo-de-prueba"
    assert ajustes.alphavantage_cache_ttl == 5
    assert ajustes.openai_configurado and ajustes.alphavantage_configurado


def test_sin_claves_no_esta_configurado(tmp_path, monkeypatch):
    _sin_variables_de_entorno(monkeypatch)

    ajustes = Settings(_env_file=tmp_path / "no-existe.env")

    assert ajustes.openai_api_key is None
    assert not ajustes.openai_configurado
    assert not ajustes.alphavantage_configurado


def test_una_clave_vacia_cuenta_como_no_configurada(tmp_path, monkeypatch):
    _sin_variables_de_entorno(monkeypatch)
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=\nALPHAVANTAGE_API_KEY=   \n")

    ajustes = Settings(_env_file=env)

    assert not ajustes.openai_configurado
    assert not ajustes.alphavantage_configurado


def test_las_claves_no_se_filtran_en_repr(tmp_path, monkeypatch):
    _sin_variables_de_entorno(monkeypatch)
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-secreta-123\nALPHAVANTAGE_API_KEY=av-secreta-456\n")

    ajustes = Settings(_env_file=env)

    texto = repr(ajustes) + str(ajustes)
    assert "sk-secreta-123" not in texto
    assert "av-secreta-456" not in texto
