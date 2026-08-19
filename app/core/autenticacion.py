import logging

# pyrefly: ignore [missing-import]
from fastapi import Depends, HTTPException, Security, status
# pyrefly: ignore [missing-import]
from fastapi.security import APIKeyHeader

from app.core.configuracion import Configuracion, obtener_configuracion

logger = logging.getLogger(__name__)

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_api_key(
    api_key: str | None = Security(_API_KEY_HEADER),
    configuracion: Configuracion = Depends(obtener_configuracion),
) -> None:
    """Dependencia FastAPI que valida el header X-API-Key.

    Comportamiento:
    - Si API_KEYS no está configurado → auth deshabilitada (útil en desarrollo local).
    - Si API_KEYS está configurado → el header X-API-Key es obligatorio y debe
      coincidir con alguna de las claves configuradas.

    Raises:
        HTTPException 401: falta el header X-API-Key.
        HTTPException 403: la clave no coincide con ninguna configurada.
    """
    if not configuracion.api_keys:
        logger.debug("Auth deshabilitada: API_KEYS no configurado.")
        return

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere el header X-API-Key para acceder a este endpoint.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key not in configuracion.api_keys:
        logger.warning("Intento de acceso con API key inválida.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key inválida.",
        )

    logger.debug("API key válida. Acceso permitido.")
