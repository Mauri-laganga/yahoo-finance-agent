from threading import RLock

from app.modelos.mensaje import MensajeConversacion


class RepositorioMemoria:
    def __init__(self) -> None:
        self._conversaciones: dict[str, list[MensajeConversacion]] = {}
        self._lock = RLock()

    def obtener_historial(self, conversation_id: str) -> list[MensajeConversacion]:
        with self._lock:
            return list(self._conversaciones.get(conversation_id, []))

    def agregar_mensaje(
        self,
        conversation_id: str,
        mensaje: MensajeConversacion,
    ) -> None:
        with self._lock:
            self._conversaciones.setdefault(conversation_id, []).append(mensaje)
