from fastapi import FastAPI

from app.api.rutas_chat import router as router_chat
from app.core.configuracion import obtener_configuracion
from app.core.logs import configurar_logs


configuracion = obtener_configuracion()
configurar_logs(configuracion.nivel_log)

app = FastAPI(
    title=configuracion.nombre_app,
    version=configuracion.version_app,
    description="API de agente conversacional con memoria y consultas financieras.",
)

app.include_router(router_chat)
