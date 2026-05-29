from threading import RLock

from app.modelos.mensaje import MensajeConversacion, RolMensaje
from app.puertos.memoria import PuertoMemoria


class Memoria(PuertoMemoria):
    def __init__(self, max_mensajes_historial: int = 30) -> None:
        self._conversaciones: dict[str, list[MensajeConversacion]] = {}
        self._max_mensajes_historial = max_mensajes_historial
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
            historial = [*self._conversaciones.get(conversation_id, []), mensaje]
            self._conversaciones[conversation_id] = self._truncar_historial(historial)

    def _truncar_historial(
        self,
        historial: list[MensajeConversacion],
    ) -> list[MensajeConversacion]:
        if self._max_mensajes_historial <= 0:
            return list(historial)

        historial_truncado = list(historial[-self._max_mensajes_historial :])
        empieza_con_asistente = (
            len(historial_truncado) > 1
            and historial_truncado[0].rol == RolMensaje.asistente
        )

        return historial_truncado[1:] if empieza_con_asistente else historial_truncado
