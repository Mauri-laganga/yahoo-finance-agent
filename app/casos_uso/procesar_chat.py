import logging

from app.agentes.agente_conversacional import agent_loop
from app.herramientas.herramienta_financiera import HerramientaFinanciera
from app.modelos.mensaje import MensajeConversacion, RolMensaje
from app.puertos.memoria import PuertoMemoria

logger = logging.getLogger(__name__)


class ProcesarChat:
    def __init__(
        self,
        *,
        repositorio_memoria: PuertoMemoria,
        herramienta_financiera: HerramientaFinanciera,
        **_kwargs: object,
    ) -> None:
        self._repositorio_memoria = repositorio_memoria
        self._herramienta_financiera = herramienta_financiera

    def procesar_mensaje(self, conversation_id: str, mensaje: str) -> str:
        conversation_id_limpio = conversation_id.strip()
        if not conversation_id_limpio:
            raise ValueError("conversation_id no puede estar vacío.")

        historial = self._repositorio_memoria.obtener_historial(conversation_id_limpio)
        respuesta = agent_loop(
            conversation_id=conversation_id_limpio,
            mensaje_usuario=mensaje,
            historial=historial,
            herramienta_financiera=self._herramienta_financiera,
        )

        self._repositorio_memoria.agregar_mensaje(
            conversation_id_limpio,
            MensajeConversacion(rol=RolMensaje.usuario, contenido=mensaje),
        )
        self._repositorio_memoria.agregar_mensaje(
            conversation_id_limpio,
            MensajeConversacion(rol=RolMensaje.asistente, contenido=respuesta),
        )
        logger.info("Mensaje procesado conversation_id=%s", conversation_id_limpio)
        return respuesta

    def obtener_historial(self, conversation_id: str) -> list[MensajeConversacion]:
        return self._repositorio_memoria.obtener_historial(conversation_id)
