from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    nombre_app: str = "API Agente Financiero"
    version_app: str = "1.0.0"
    nivel_log: str = "INFO"
    max_mensajes_historial: int = 30
    api_keys: frozenset[str] = Field(
        default_factory=frozenset,
        validation_alias="API_KEYS",
        description=(
            "Claves de API válidas, separadas por coma. "
            "Si está vacío, la autenticación está deshabilitada."
        ),
    )

    @field_validator("api_keys", mode="before")
    @classmethod
    def parsear_api_keys(cls, valor: object) -> frozenset[str]:
        """Parsea API_KEYS: acepta string CSV, colecciones o None."""
        if not valor:
            return frozenset()
        if isinstance(valor, frozenset | set | list | tuple):
            return frozenset(str(k).strip() for k in valor if str(k).strip())
        return frozenset(k.strip() for k in str(valor).split(",") if k.strip())

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
