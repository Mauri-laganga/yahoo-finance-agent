import logging
import re
from dataclasses import dataclass
from typing import Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.dominio.estados_agente import EstadoAgente, TRANSICIONES_AGENT_LOOP
from app.herramientas.herramienta_financiera import HerramientaFinanciera
from app.modelos.mensaje import MensajeConversacion, RolMensaje
from app.utils.constantes import (
    EMPRESAS_CONOCIDAS,
    PALABRAS_FINANCIERAS,
    PALABRAS_NO_TICKER,
    PATRON_TICKER,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecisionHerramienta:
    usar_herramienta: bool
    simbolo: str | None
    motivo: str


@dataclass
class ContextoAgentLoop:
    conversation_id: str
    mensaje_usuario: str
    historial: list[MensajeConversacion]
    herramienta_financiera: HerramientaFinanciera
    llm: BaseChatModel | None
    mensaje_limpio: str = ""
    contexto_historial: str = ""
    decision: DecisionHerramienta = DecisionHerramienta(
        False,
        None,
        "El agente todavía no evaluó intención.",
    )
    resultado_herramienta: str | None = None
    respuesta: str = ""


def agent_loop(
    *,
    conversation_id: str,
    mensaje_usuario: str,
    historial: list[MensajeConversacion],
    herramienta_financiera: HerramientaFinanciera,
    llm: BaseChatModel | None = None,
) -> str:
    """Grafo de estados del agente: contexto, decisión, tool y respuesta final."""
    logger.info("Iniciando agent_loop para conversation_id=%s", conversation_id)

    contexto = ContextoAgentLoop(
        conversation_id=conversation_id,
        mensaje_usuario=mensaje_usuario,
        historial=historial,
        herramienta_financiera=herramienta_financiera,
        llm=llm,
    )
    handlers: dict[EstadoAgente, Callable[[ContextoAgentLoop], None]] = {
        EstadoAgente.INICIO: _iniciar_agent_loop,
        EstadoAgente.LEER_HISTORIAL: _leer_historial,
        EstadoAgente.ANALIZAR_INTENCION: _analizar_intencion,
        EstadoAgente.DECIDIR_HERRAMIENTA: _registrar_decision_herramienta,
        EstadoAgente.EJECUTAR_HERRAMIENTA: _ejecutar_herramienta,
        EstadoAgente.GENERAR_RESPUESTA: _generar_respuesta,
    }
    estado = EstadoAgente.INICIO

    while estado != EstadoAgente.FINALIZAR:
        logger.info("Agente estado=%s conversation_id=%s", estado.value, conversation_id)
        handlers[estado](contexto)
        estado = TRANSICIONES_AGENT_LOOP[estado]

    logger.info("Agente estado=%s conversation_id=%s", EstadoAgente.FINALIZAR.value, conversation_id)
    logger.info("agent_loop finalizado para conversation_id=%s", conversation_id)
    return contexto.respuesta


def _iniciar_agent_loop(contexto: ContextoAgentLoop) -> None:
    contexto.mensaje_limpio = contexto.mensaje_usuario.strip()
    if not contexto.mensaje_limpio:
        raise ValueError("El mensaje no puede estar vacío.")


def _leer_historial(contexto: ContextoAgentLoop) -> None:
    contexto.contexto_historial = _formatear_historial(contexto.historial)
    logger.debug(
        "Historial leído conversation_id=%s mensajes=%s",
        contexto.conversation_id,
        len(contexto.historial),
    )


def _analizar_intencion(contexto: ContextoAgentLoop) -> None:
    contexto.decision = _evaluar_contexto_y_decidir_herramienta(
        mensaje=contexto.mensaje_limpio,
        historial=contexto.historial,
    )
    logger.info(
        "Agente decisión conversation_id=%s usar_herramienta=%s simbolo=%s motivo=%s",
        contexto.conversation_id,
        contexto.decision.usar_herramienta,
        contexto.decision.simbolo,
        contexto.decision.motivo,
    )


def _registrar_decision_herramienta(contexto: ContextoAgentLoop) -> None:
    if contexto.decision.usar_herramienta:
        return
    logger.info(
        "Agente sin herramienta conversation_id=%s motivo=%s",
        contexto.conversation_id,
        contexto.decision.motivo,
    )


def _ejecutar_herramienta(contexto: ContextoAgentLoop) -> None:
    if not contexto.decision.usar_herramienta or not contexto.decision.simbolo:
        return

    logger.info(
        "Agente ejecuta herramienta_financiera conversation_id=%s simbolo=%s",
        contexto.conversation_id,
        contexto.decision.simbolo,
    )
    try:
        contexto.resultado_herramienta = contexto.herramienta_financiera.ejecutar_como_tool(
            contexto.decision.simbolo,
        )
    except Exception:
        logger.exception(
            "Error ejecutando herramienta_financiera conversation_id=%s simbolo=%s",
            contexto.conversation_id,
            contexto.decision.simbolo,
        )
        raise


def _generar_respuesta(contexto: ContextoAgentLoop) -> None:
    contexto.respuesta = _generar_respuesta_final(
        mensaje=contexto.mensaje_limpio,
        contexto_historial=contexto.contexto_historial,
        decision=contexto.decision,
        resultado_herramienta=contexto.resultado_herramienta,
        llm=contexto.llm,
    )


def _evaluar_contexto_y_decidir_herramienta(
    *,
    mensaje: str,
    historial: list[MensajeConversacion],
) -> DecisionHerramienta:
    texto = mensaje.lower()
    simbolo = _extraer_simbolo(mensaje)
    tiene_intencion_financiera = any(palabra in texto for palabra in PALABRAS_FINANCIERAS)

    if simbolo and tiene_intencion_financiera:
        return DecisionHerramienta(True, simbolo, "El usuario pidió datos financieros.")

    if tiene_intencion_financiera:
        simbolo_historial = _buscar_ultimo_simbolo_en_historial(historial)
        if simbolo_historial:
            return DecisionHerramienta(
                True,
                simbolo_historial,
                "El usuario mantiene el tema financiero de la conversación.",
            )

    if simbolo and _parece_pedido_financiero_corto(texto):
        return DecisionHerramienta(True, simbolo, "El mensaje menciona un ticker o empresa.")

    return DecisionHerramienta(False, None, "No se detectó necesidad de consultar finanzas.")


def _extraer_simbolo(texto: str) -> str | None:
    texto_normalizado = texto.lower()
    simbolo_empresa = next(
        (
            simbolo
            for nombre_empresa, simbolo in EMPRESAS_CONOCIDAS.items()
            if nombre_empresa in texto_normalizado
        ),
        None,
    )
    if simbolo_empresa:
        return simbolo_empresa

    coincidencias = re.findall(PATRON_TICKER, texto)
    return next(
        (coincidencia for coincidencia in coincidencias if coincidencia not in PALABRAS_NO_TICKER),
        None,
    )


def _buscar_ultimo_simbolo_en_historial(historial: list[MensajeConversacion]) -> str | None:
    return next(
        (
            simbolo
            for simbolo in (
                _extraer_simbolo(mensaje.contenido)
                for mensaje in reversed(historial)
            )
            if simbolo
        ),
        None,
    )


def _parece_pedido_financiero_corto(texto: str) -> bool:
    return len(texto.split()) <= 8


def _formatear_historial(historial: list[MensajeConversacion]) -> str:
    if not historial:
        return "Sin historial previo."
    return "\n".join(f"{mensaje.rol.value}: {mensaje.contenido}" for mensaje in historial)


def _generar_respuesta_final(
    *,
    mensaje: str,
    contexto_historial: str,
    decision: DecisionHerramienta,
    resultado_herramienta: str | None,
    llm: BaseChatModel | None,
) -> str:
    contexto_tool = resultado_herramienta or "No se usó herramienta financiera."

    if llm is None:
        return _generar_respuesta_sin_llm(
            mensaje=mensaje,
            decision=decision,
            resultado_herramienta=resultado_herramienta,
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Sos un agente conversacional claro, útil y breve. "
                "Respondé en castellano argentino técnico. "
                "Si hay datos financieros, explicalos sin inventar información.",
            ),
            (
                "human",
                "Historial:\n{historial}\n\n"
                "Mensaje actual:\n{mensaje}\n\n"
                "Decisión de herramienta:\n{decision}\n\n"
                "Resultado de herramienta:\n{resultado_tool}\n\n"
                "Generá la respuesta final.",
            ),
        ]
    )
    cadena = prompt | llm | StrOutputParser()
    return cadena.invoke(
        {
            "historial": contexto_historial,
            "mensaje": mensaje,
            "decision": decision,
            "resultado_tool": contexto_tool,
        }
    )


def _generar_respuesta_sin_llm(
    *,
    mensaje: str,
    decision: DecisionHerramienta,
    resultado_herramienta: str | None,
) -> str:
    if resultado_herramienta:
        return (
            f"Consulté Yahoo Finance para {decision.simbolo}. "
            f"{resultado_herramienta}"
        )

    return (
        "Recibí tu mensaje y lo guardé en esta conversación. "
        "Si querés consultar una acción, mencioná el ticker o la empresa, por ejemplo: "
        "'¿Cómo está AAPL hoy?'."
    )
