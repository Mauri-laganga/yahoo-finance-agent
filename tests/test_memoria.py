from app.modelos.mensaje import MensajeConversacion, RolMensaje
from app.repositorios.repositorio_memoria import RepositorioMemoria


def test_memoria_mantiene_conversaciones_independientes() -> None:
    memoria = RepositorioMemoria(max_mensajes_historial=10)

    memoria.agregar_mensaje("conv-a", MensajeConversacion(rol=RolMensaje.usuario, contenido="AAPL"))
    memoria.agregar_mensaje("conv-b", MensajeConversacion(rol=RolMensaje.usuario, contenido="MSFT"))

    assert [mensaje.contenido for mensaje in memoria.obtener_historial("conv-a")] == ["AAPL"]
    assert [mensaje.contenido for mensaje in memoria.obtener_historial("conv-b")] == ["MSFT"]


def test_memoria_trunca_historial_configurable() -> None:
    memoria = RepositorioMemoria(max_mensajes_historial=3)

    for indice in range(5):
        memoria.agregar_mensaje(
            "conv",
            MensajeConversacion(rol=RolMensaje.usuario, contenido=f"mensaje {indice}"),
        )

    historial = memoria.obtener_historial("conv")

    assert len(historial) == 3
    assert [mensaje.contenido for mensaje in historial] == [
        "mensaje 2",
        "mensaje 3",
        "mensaje 4",
    ]

