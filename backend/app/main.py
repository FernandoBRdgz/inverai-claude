import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.models.salud import EstadoSalud

# Sin esto, logger.info/warning de app/services/* (ej. qué herramienta llamó el agente)
# no se ven: uvicorn configura sus propios loggers, pero no el resto del código.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")

app = FastAPI(title=settings.proyecto)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=EstadoSalud)
def health() -> EstadoSalud:
    """Estado operativo: lo consume la vista de Administración del frontend."""
    return EstadoSalud(
        status="ok",
        openai_configurado=settings.openai_configurado,
        alphavantage_configurado=settings.alphavantage_configurado,
        modelo=settings.openai_model,
    )
