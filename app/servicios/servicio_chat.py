import logging

from langchain_core.language_models.chat_models import BaseChatModel

from app.agentes.agente_conversacional import agent_loop
from app.core.configuracion import Configuracion
from app.herramientas.herramienta_financiera import HerramientaFinanciera
from app.modelos.mensaje import MensajeConversacion, RolMensaje
from app.repositorios.repositorio_memoria import RepositorioMemoria

logger = logging.getLogger(__name__)


class ServicioConversacional:
    def __init__(
        self,
        *,
        repositorio_memoria: RepositorioMemoria,
        herramienta_financiera: HerramientaFinanciera,
        configuracion: Configuracion,
    ) -> None:
        self._repositorio_memoria = repositorio_memoria
        self._herramienta_financiera = herramienta_financiera
        self._llm = self._crear_llm(configuracion)

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
            llm=self._llm,
        )

        self._repositorio_memoria.agregar_mensaje(
            conversation_id_limpio,
            MensajeConversacion(rol=RolMensaje.usuario, contenido=mensaje),
        )
        self._repositorio_memoria.agregar_mensaje(
            conversation_id_limpio,
            MensajeConversacion(rol=RolMensaje.asistente, contenido=respuesta),
        )
        return respuesta

    def obtener_historial(self, conversation_id: str) -> list[MensajeConversacion]:
        return self._repositorio_memoria.obtener_historial(conversation_id)

    def _crear_llm(self, configuracion: Configuracion) -> BaseChatModel | None:
        if not configuracion.openai_api_key:
            logger.info("OPENAI_API_KEY no configurada; se usará respuesta determinística.")
            return None

        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            logger.warning("langchain-openai no está instalado; se usará respuesta determinística.")
            return None

        return ChatOpenAI(
            model=configuracion.modelo_llm,
            api_key=configuracion.openai_api_key,
            temperature=0.2,
        )
