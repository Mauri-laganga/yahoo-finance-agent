from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencias import obtener_servicio_chat
from app.modelos.esquemas_chat import PedidoChat, RespuestaChat, RespuestaHistorial
from app.servicios.servicio_chat import ServicioConversacional

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=RespuestaChat)
def conversar(
    pedido: PedidoChat,
    servicio_chat: ServicioConversacional = Depends(obtener_servicio_chat),
) -> RespuestaChat:
    try:
        respuesta = servicio_chat.procesar_mensaje(
            conversation_id=pedido.conversation_id,
            mensaje=pedido.mensaje,
        )
        return RespuestaChat(conversation_id=pedido.conversation_id, respuesta=respuesta)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get("/chat/{id}", response_model=RespuestaHistorial)
def obtener_historial(
    id: str,
    servicio_chat: ServicioConversacional = Depends(obtener_servicio_chat),
) -> RespuestaHistorial:
    historial = servicio_chat.obtener_historial(id)
    return RespuestaHistorial(conversation_id=id, historial=historial)
