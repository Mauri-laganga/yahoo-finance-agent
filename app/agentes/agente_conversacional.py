import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

from app.dominio.estados_agente import EstadoAgente, TRANSICIONES_AGENT_LOOP
from app.herramientas.herramienta_financiera import HerramientaFinanciera
from app.modelos.mensaje import MensajeConversacion, RolMensaje
from app.utils.constantes import (
    EMPRESAS_CONOCIDAS,
    PALABRAS_FINANCIERAS,
    PALABRAS_META_HISTORIAL,
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
) -> str:
    """Grafo de estados del agente: contexto, decisión, tool y respuesta final."""
    logger.info("Iniciando agent_loop para conversation_id=%s", conversation_id)

    contexto = ContextoAgentLoop(
        conversation_id=conversation_id,
        mensaje_usuario=mensaje_usuario,
        historial=historial,
        herramienta_financiera=herramienta_financiera,
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
    contexto.respuesta = _generar_respuesta_deterministica(
        mensaje=contexto.mensaje_limpio,
        decision=contexto.decision,
        resultado_herramienta=contexto.resultado_herramienta,
        historial=contexto.historial,
    )


def _evaluar_contexto_y_decidir_herramienta(
    *,
    mensaje: str,
    historial: list[MensajeConversacion],
) -> DecisionHerramienta:
    texto = _normalizar_texto(mensaje)
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


def _normalizar_texto(texto: str) -> str:
    """Convierte a minúsculas y elimina acentos para comparación robusta."""
    texto_lower = texto.lower()
    return unicodedata.normalize("NFD", texto_lower).encode("ascii", "ignore").decode("ascii")


def _extraer_simbolo(texto: str) -> str | None:
    texto_normalizado = _normalizar_texto(texto)
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


def _es_pregunta_sobre_historial(texto_normalizado: str) -> bool:
    """Detecta si el usuario pregunta sobre la conversación previa (meta-pregunta)."""
    return any(frase in texto_normalizado for frase in PALABRAS_META_HISTORIAL)


def _generar_respuesta_deterministica(
    *,
    mensaje: str,
    decision: DecisionHerramienta,
    resultado_herramienta: str | None,
    historial: list[MensajeConversacion],
) -> str:
    # Caso 1: se consultó Yahoo Finance → devuelve los datos directamente.
    if resultado_herramienta:
        return (
            f"Consulté Yahoo Finance para {decision.simbolo}. "
            f"{resultado_herramienta}"
        )

    texto = _normalizar_texto(mensaje)

    # Caso 2: el usuario pregunta sobre la conversación misma.
    if _es_pregunta_sobre_historial(texto):
        if not historial:
            return (
                "No tenemos historial previo en esta conversación todavía. "
                "¿Querés consultar alguna acción o empresa?"
            )
        ultimos = historial[-4:] 
        resumen = "\n".join(
            f"  [{m.rol.value}]: {m.contenido}" for m in ultimos
        )
        return f"Esto es lo que hablamos recientemente:\n{resumen}"

    # Caso 3: pregunta fuera del dominio financiero.
    return (
        "Solo puedo ayudarte con consultas financieras: precios de acciones, "
        "cotizaciones, market cap y datos de bolsa. "
        "Si querés consultar una empresa o ticker, mencionálo, "
        "por ejemplo: '¿Cómo está AAPL hoy?' o 'precio de Apple'."
    )
