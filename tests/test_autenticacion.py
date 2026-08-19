import pytest
from fastapi import HTTPException

from app.core.autenticacion import _parsear_api_keys, verificar_api_key
from app.core.configuracion import Configuracion

def _config(api_keys_csv: str = "") -> Configuracion:
    """Crea una Configuracion en memoria con las claves dadas como CSV."""
    return Configuracion.model_construct(
        nombre_app="Test",
        version_app="0.0.0",
        nivel_log="ERROR",
        max_mensajes_historial=10,
        api_keys=api_keys_csv if api_keys_csv else None,
    )

def test_auth_deshabilitada_permite_cualquier_request() -> None:
    """Si api_keys está vacío, todos los requests pasan sin importar el header."""
    config = _config()  

    verificar_api_key(api_key=None, configuracion=config)
    verificar_api_key(api_key="clave-random-sin-configurar", configuracion=config)


def test_auth_habilitada_sin_header_devuelve_401() -> None:
    config = _config("clave-secreta")

    with pytest.raises(HTTPException) as exc_info:
        verificar_api_key(api_key=None, configuracion=config)

    assert exc_info.value.status_code == 401
    assert "X-API-Key" in exc_info.value.detail


def test_auth_habilitada_clave_invalida_devuelve_403() -> None:
    config = _config("clave-secreta")

    with pytest.raises(HTTPException) as exc_info:
        verificar_api_key(api_key="clave-incorrecta", configuracion=config)

    assert exc_info.value.status_code == 403
    assert "inválida" in exc_info.value.detail.lower()


def test_auth_habilitada_clave_valida_pasa() -> None:
    config = _config("clave-secreta")
    verificar_api_key(api_key="clave-secreta", configuracion=config)


def test_auth_acepta_cualquiera_de_multiples_claves() -> None:
    """Soporte para rotación de claves: varias claves válidas simultáneas."""
    config = _config("clave-prod,clave-staging,clave-dev")

    verificar_api_key(api_key="clave-prod", configuracion=config)
    verificar_api_key(api_key="clave-staging", configuracion=config)
    verificar_api_key(api_key="clave-dev", configuracion=config)


def test_auth_rechaza_clave_que_no_esta_en_la_lista() -> None:
    config = _config("clave-prod,clave-staging")

    with pytest.raises(HTTPException) as exc_info:
        verificar_api_key(api_key="clave-dev", configuracion=config)

    assert exc_info.value.status_code == 403

def test_parseo_csv_con_espacios() -> None:
    claves = _parsear_api_keys("clave-1, clave-2 , clave-3")
    assert claves == frozenset({"clave-1", "clave-2", "clave-3"})


def test_parseo_csv_vacio_devuelve_frozenset_vacio() -> None:
    assert _parsear_api_keys("") == frozenset()
    assert _parsear_api_keys(None) == frozenset()


def test_parseo_csv_clave_unica_sin_comas() -> None:
    """Agent1357 debe parsearse como una única clave válida."""
    claves = _parsear_api_keys("Agent1357")
    assert claves == frozenset({"Agent1357"})
