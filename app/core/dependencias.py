from functools import lru_cache

from app.core.configuracion import obtener_configuracion
from app.herramientas.herramienta_financiera import HerramientaFinanciera
from app.repositorios.repositorio_memoria import RepositorioMemoria
from app.servicios.servicio_chat import ServicioConversacional


@lru_cache
def obtener_repositorio_memoria() -> RepositorioMemoria:
    configuracion = obtener_configuracion()
    return RepositorioMemoria(
        max_mensajes_historial=configuracion.max_mensajes_historial,
    )


@lru_cache
def obtener_herramienta_financiera() -> HerramientaFinanciera:
    return HerramientaFinanciera()


@lru_cache
def obtener_servicio_chat() -> ServicioConversacional:
    configuracion = obtener_configuracion()
    return ServicioConversacional(
        repositorio_memoria=obtener_repositorio_memoria(),
        herramienta_financiera=obtener_herramienta_financiera(),
        configuracion=configuracion,
    )
