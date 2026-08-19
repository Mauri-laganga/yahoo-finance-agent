# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from app.core.autenticacion import verificar_api_key
from app.core.configuracion import Configuracion


def _config(*claves: str) -> Configuracion:
    """Crea una Configuracion en memoria con las claves dadas."""
    return Configuracion.model_construct(
        nombre_app="Test",
        version_app="0.0.0",
        nivel_log="ERROR",
        max_mensajes_historial=10,
        openai_api_key=None,
        modelo_llm="gpt-4o-mini",
        api_keys=frozenset(claves),
    )


def test_auth_deshabilitada_permite_cualquier_request() -> None:
    """Si api_keys está vacío, todos los requests pasan sin importar el header."""
    config = _config()  

    verificar_api_key(api_key=None, configuracion=config)
    # Header arbitrario → también OK
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
    config = _config("clave-prod", "clave-staging", "clave-dev")

    verificar_api_key(api_key="clave-prod", configuracion=config)
    verificar_api_key(api_key="clave-staging", configuracion=config)
    verificar_api_key(api_key="clave-dev", configuracion=config)


def test_auth_rechaza_clave_que_no_esta_en_la_lista() -> None:
    config = _config("clave-prod", "clave-staging")

    with pytest.raises(HTTPException) as exc_info:
        verificar_api_key(api_key="clave-dev", configuracion=config)

    assert exc_info.value.status_code == 403


def test_parseo_de_api_keys_desde_string_csv() -> None:
    """Verifica que el validator parsea correctamente un string CSV."""
    config = Configuracion(api_keys="clave-1, clave-2 , clave-3")  

    assert "clave-1" in config.api_keys
    assert "clave-2" in config.api_keys
    assert "clave-3" in config.api_keys
    assert len(config.api_keys) == 3


def test_parseo_de_api_keys_vacio_deshabilita_auth() -> None:
    config = Configuracion(api_keys="")  
    assert len(config.api_keys) == 0
