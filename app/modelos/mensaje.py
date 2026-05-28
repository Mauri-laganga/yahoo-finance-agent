from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class RolMensaje(str, Enum):
    usuario = "usuario"
    asistente = "asistente"


class MensajeConversacion(BaseModel):
    rol: RolMensaje
    contenido: str
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
