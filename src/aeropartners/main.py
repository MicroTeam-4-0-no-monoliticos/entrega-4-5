from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.pagos import router as pagos_router
from .seedwork.infraestructura.db import engine
from .modulos.pagos.infraestructura.modelos import Base

# Import Event Collector
try:
    from .event_collector.app import app as event_collector_app
    from .event_collector.app import health_router, collector_router
    COLLECTOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Event Collector no disponible: {e}")
    COLLECTOR_AVAILABLE = False

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Configurar aplicación principal
if COLLECTOR_AVAILABLE:
    # Usar la app del Event Collector como base
    app = event_collector_app
    app.title = "ALPES Partners - Event Collector + Pagos"
    app.description = "Event Collector (BFF) y módulos DDD para ALPES Partners"
    
    # Incluir router de pagos como módulo adicional
    app.include_router(pagos_router, prefix="/api/pagos")
    
else:
    # Fallback a la app original
    app = FastAPI(
        title="Aeropartners - Microservicio de Pagos", 
        description="Microservicio de pagos para la plataforma Aeropartners implementando DDD y Arquitectura Hexagonal",
        version="1.0.0"
    )
    
    # Configurar CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Incluir routers
    app.include_router(pagos_router)
    
    @app.get("/")
    async def root():
        return {
            "mensaje": "Bienvenido al Microservicio de Pagos de Aeropartners",
            "version": "1.0.0",
            "endpoints": {
                "procesar_pago": "POST /pagos/",
                "obtener_estado": "GET /pagos/id_pago",
                "estadisticas_outbox": "GET /pagos/outbox/estadisticas"
            }
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "aeropartners-pagos"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
