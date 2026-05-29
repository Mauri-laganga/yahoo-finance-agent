from typing import Protocol

from app.modelos.mensaje import MensajeConversacion


class PuertoMemoria(Protocol):
    def obtener_historial(self, conversation_id: str) -> list[MensajeConversacion]:
        """Devuelve el historial visible para una conversación."""

    def agregar_mensaje(
        self,
        conversation_id: str,
        mensaje: MensajeConversacion,
    ) -> None:
        """Agrega un mensaje al historial de una conversación."""

