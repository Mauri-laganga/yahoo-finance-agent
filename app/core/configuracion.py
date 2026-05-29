from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    nombre_app: str = "API Agente Financiero"
    version_app: str = "1.0.0"
    nivel_log: str = "INFO"
    max_mensajes_historial: int = 30
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    modelo_llm: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
