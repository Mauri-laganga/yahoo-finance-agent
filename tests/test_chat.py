from app.api.rutas_chat import conversar, obtener_historial
from app.core.configuracion import Configuracion
from app.modelos.esquemas_chat import PedidoChat
from app.repositorios.repositorio_memoria import RepositorioMemoria
from app.servicios.servicio_chat import ServicioConversacional


class FakeHerramientaFinanciera:
    def ejecutar_como_tool(self, simbolo: str) -> str:
        return f"Empresa: Test Corp ({simbolo}). Precio actual: 10.00 USD. Fuente: Yahoo Finance (mock)."


def crear_servicio() -> ServicioConversacional:
    return ServicioConversacional(
        repositorio_memoria=RepositorioMemoria(max_mensajes_historial=20),
        herramienta_financiera=FakeHerramientaFinanciera(),
        configuracion=Configuracion(),
    )


def test_endpoint_chat_y_memoria_por_conversation_id() -> None:
    servicio = crear_servicio()

    respuesta_a = conversar(
        PedidoChat(conversation_id="conv-a", mensaje="AAPL price"),
        servicio_chat=servicio,
    )
    respuesta_b = conversar(
        PedidoChat(conversation_id="conv-b", mensaje="MSFT price"),
        servicio_chat=servicio,
    )

    assert respuesta_a.conversation_id == "conv-a"
    assert "AAPL" in respuesta_a.respuesta
    assert respuesta_b.conversation_id == "conv-b"
    assert "MSFT" in respuesta_b.respuesta

    historial_a = obtener_historial("conv-a", servicio_chat=servicio)
    historial_b = obtener_historial("conv-b", servicio_chat=servicio)

    assert len(historial_a.historial) == 2
    assert len(historial_b.historial) == 2
    assert "AAPL" in historial_a.historial[0].contenido
    assert "MSFT" in historial_b.historial[0].contenido


def test_pregunta_fuera_de_dominio_no_llama_a_yahoo() -> None:
    """Preguntas sin relación con finanzas deben recibir una respuesta que
    aclara el dominio del agente, sin invocar la herramienta financiera."""
    servicio = crear_servicio()

    for mensaje in [
        "¿qué temperatura hace hoy en Buenos Aires?",
        "quién ganó el último mundial?",
        "contame un chiste",
        "¿cuánto es 2 + 2?",
    ]:
        respuesta = conversar(
            PedidoChat(conversation_id="fuera-dominio", mensaje=mensaje),
            servicio_chat=servicio,
        )
        # Debe indicar que solo puede ayudar con finanzas, no inventar datos.
        assert "financiera" in respuesta.respuesta.lower() or "accion" in respuesta.respuesta.lower() or "bolsa" in respuesta.respuesta.lower(), (
            f"Se esperaba respuesta de dominio financiero para: '{mensaje}'. "
            f"Respuesta actual: '{respuesta.respuesta}'"
        )
        # No debe incluir datos de Yahoo Finance falsos.
        assert "Test Corp" not in respuesta.respuesta, (
            f"La herramienta financiera no debería haberse invocado para: '{mensaje}'"
        )


def test_meta_pregunta_responde_desde_historial() -> None:
    """Preguntas sobre la conversación previa deben responderse con el historial,
    no con datos de Yahoo Finance ni con el mensaje genérico de dominio."""
    servicio = crear_servicio()
    conv_id = "meta-test"

    # Primero se hace una consulta financiera real.
    conversar(
        PedidoChat(conversation_id=conv_id, mensaje="¿cómo está AAPL hoy?"),
        servicio_chat=servicio,
    )

    # Luego el usuario pregunta sobre lo que se habló.
    respuesta = conversar(
        PedidoChat(conversation_id=conv_id, mensaje="¿qué te acabo de preguntar?"),
        servicio_chat=servicio,
    )

    # Debe responder con el historial, que incluye AAPL.
    assert "AAPL" in respuesta.respuesta or "aapl" in respuesta.respuesta.lower(), (
        f"Se esperaba referencia al historial (AAPL). Respuesta: '{respuesta.respuesta}'"
    )


def test_meta_pregunta_sin_historial_previo() -> None:
    """Si se hace una meta-pregunta en una conversación vacía, debe responder
    que no hay historial previo."""
    servicio = crear_servicio()

    respuesta = conversar(
        PedidoChat(conversation_id="vacia", mensaje="¿de qué hablamos antes?"),
        servicio_chat=servicio,
    )

    assert "historial" in respuesta.respuesta.lower() or "previo" in respuesta.respuesta.lower(), (
        f"Respuesta inesperada para conversación vacía: '{respuesta.respuesta}'"
    )
