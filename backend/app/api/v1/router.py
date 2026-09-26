from fastapi import APIRouter

from app.api.v1.endpoints import chat, comparativa, cotizacion

# Punto único donde se agregan los routers de cada dominio de negocio.
# Nuevos dominios (ej. usuarios, inversiones) se registran aquí también.
api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(comparativa.router)
api_router.include_router(cotizacion.router)
