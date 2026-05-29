from app.api.rutas_chat import conversar, obtener_historial
from app.core.configuracion import Configuracion
from app.modelos.esquemas_chat import PedidoChat
from app.repositorios.repositorio_memoria import RepositorioMemoria
from app.servicios.servicio_chat import ServicioConversacional


class FakeHerramientaFinanciera:
    def ejecutar_como_tool(self, simbolo: str) -> str:
        return f"Empresa: Test Corp ({simbolo}). Precio actual: 10.00 USD. Fuente: Yahoo Finance (mock)."


def crear_servicio() -> ServicioConversacional:
    servicio = ServicioConversacional(
        repositorio_memoria=RepositorioMemoria(max_mensajes_historial=20),
        herramienta_financiera=FakeHerramientaFinanciera(),
        configuracion=Configuracion(openai_api_key=None),
    )
    servicio._llm = None
    return servicio


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
