from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    nombre_app: str = "API Agente Financiero"
    version_app: str = "1.0.0"
    nivel_log: str = "INFO"
    max_mensajes_historial: int = 30
    api_keys: str | None = Field(
        default=None,
        validation_alias="API_KEYS",
        description=(
            "Claves de API válidas separadas por coma. "
            "Si está vacío o no se configura, la autenticación está deshabilitada."
        ),
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
