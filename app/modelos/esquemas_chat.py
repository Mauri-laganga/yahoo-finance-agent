from pydantic import BaseModel, Field

from app.modelos.mensaje import MensajeConversacion


class PedidoChat(BaseModel):
    conversation_id: str = Field(..., min_length=1, examples=["abc123"])
    mensaje: str = Field(..., min_length=1, examples=["¿Cómo está Apple hoy?"])


class RespuestaChat(BaseModel):
    conversation_id: str
    respuesta: str


class RespuestaHistorial(BaseModel):
    conversation_id: str
    historial: list[MensajeConversacion]
