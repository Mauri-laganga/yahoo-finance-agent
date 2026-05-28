import logging
import re
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.herramientas.herramienta_financiera import HerramientaFinanciera
from app.modelos.mensaje import MensajeConversacion, RolMensaje

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecisionHerramienta:
    usar_herramienta: bool
    simbolo: str | None
    motivo: str


EMPRESAS_CONOCIDAS: dict[str, str] = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "mercado libre": "MELI",
    "mercadolibre": "MELI",
    "coca cola": "KO",
    "coca-cola": "KO",
    "walmart": "WMT",
    "disney": "DIS",
}

PALABRAS_FINANCIERAS = (
    "accion",
    "acciones",
    "bolsa",
    "cotiza",
    "cotizacion",
    "financ",
    "market cap",
    "mercado",
    "precio",
    "ticker",
    "variacion",
    "valor",
    "yahoo",
)


def agent_loop(
    *,
    conversation_id: str,
    mensaje_usuario: str,
    historial: list[MensajeConversacion],
    herramienta_financiera: HerramientaFinanciera,
    llm: BaseChatModel | None = None,
) -> str:
    """Flujo explícito del agente: contexto, decisión, tool y respuesta final."""
    logger.info("Iniciando agent_loop para conversation_id=%s", conversation_id)

    mensaje_limpio = mensaje_usuario.strip()
    if not mensaje_limpio:
        raise ValueError("El mensaje no puede estar vacío.")

    contexto_historial = _formatear_historial(historial)
    logger.debug("Historial leído para %s: %s mensajes", conversation_id, len(historial))

    decision = _evaluar_contexto_y_decidir_herramienta(
        mensaje=mensaje_limpio,
        historial=historial,
    )
    logger.info(
        "Decisión de herramienta para %s: usar=%s simbolo=%s motivo=%s",
        conversation_id,
        decision.usar_herramienta,
        decision.simbolo,
        decision.motivo,
    )

    resultado_herramienta: str | None = None
    if decision.usar_herramienta and decision.simbolo:
        resultado_herramienta = herramienta_financiera.ejecutar_como_tool(decision.simbolo)

    respuesta = _generar_respuesta_final(
        mensaje=mensaje_limpio,
        contexto_historial=contexto_historial,
        decision=decision,
        resultado_herramienta=resultado_herramienta,
        llm=llm,
    )
    logger.info("agent_loop finalizado para conversation_id=%s", conversation_id)
    return respuesta


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
    for nombre_empresa, simbolo in EMPRESAS_CONOCIDAS.items():
        if nombre_empresa in texto_normalizado:
            return simbolo

    coincidencias = re.findall(r"\b[A-Z]{1,5}(?:\.[A-Z]{1,2})?\b", texto)
    palabras_no_ticker = {"API", "CEO", "USD", "IA", "AI"}
    for coincidencia in coincidencias:
        if coincidencia not in palabras_no_ticker:
            return coincidencia
    return None


def _buscar_ultimo_simbolo_en_historial(historial: list[MensajeConversacion]) -> str | None:
    for mensaje in reversed(historial):
        simbolo = _extraer_simbolo(mensaje.contenido)
        if simbolo:
            return simbolo
    return None


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
