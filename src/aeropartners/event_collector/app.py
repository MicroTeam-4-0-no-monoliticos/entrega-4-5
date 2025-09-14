"""
FastAPI Application - Event Collector/BFF
"""
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time
import uuid
from datetime import datetime
from typing import Optional

# Importar módulos locales
from .config import Settings, get_settings
from .models import (
    CollectClickRequest, CollectClickResponse,
    CollectImpressionRequest, CollectImpressionResponse,
    CollectConversionRequest, CollectConversionResponse,
    HealthCheckResponse, HealthStatus, ErrorResponse
)
from .pulsar_client import PulsarProducer, get_pulsar_producer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instancia global del producer
pulsar_producer: Optional[PulsarProducer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    global pulsar_producer
    
    # Startup
    logger.info("🚀 Iniciando Event Collector...")
    settings = get_settings()
    
    try:
        # Inicializar Pulsar producer
        pulsar_producer = PulsarProducer(settings)
        await pulsar_producer.connect()
        logger.info("✅ Event Collector iniciado correctamente")
    except Exception as e:
        logger.error(f"❌ Error iniciando Event Collector: {e}")
        # En desarrollo, continuamos sin Pulsar
        if settings.debug:
            logger.warning("⚠️ Continuando en modo debug sin Pulsar")
            pulsar_producer = None
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando Event Collector...")
    if pulsar_producer:
        await pulsar_producer.disconnect()
    logger.info("✅ Event Collector cerrado correctamente")


# Crear aplicación FastAPI
app = FastAPI(
    title="ALPES Partners - Event Collector",
    description="Backend for Frontend (BFF) y Event Collector para el sistema ALPES Partners",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency para obtener IP del cliente
def get_client_ip(request: Request) -> str:
    """Obtener IP del cliente considerando proxies"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Dependency para rate limiting (simulado)
async def rate_limit_check(request: Request, settings: Settings = Depends(get_settings)):
    """Verificación de rate limiting (implementación básica)"""
    client_ip = get_client_ip(request)
    
    # En una implementación real, usarías Redis o similar
    # Por ahora solo logueamos
    logger.debug(f"Rate limit check for IP: {client_ip}")
    
    # Verificar IPs bloqueadas
    if client_ip in settings.blocked_ips:
        raise HTTPException(status_code=403, detail="IP blocked")


# Dependency para obtener el producer
def get_producer() -> Optional[PulsarProducer]:
    """Obtener instancia del Pulsar producer"""
    return pulsar_producer


# Exception handler global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejo global de excepciones"""
    trace_id = str(uuid.uuid4())
    logger.error(f"Global exception [trace_id: {trace_id}]: {exc}", exc_info=True)
    
    error_response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        error_message="Internal server error",
        timestamp=datetime.utcnow(),
        trace_id=trace_id
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


# Health Check Endpoints
@app.get("/health", response_model=HealthCheckResponse)
async def health_check(producer: Optional[PulsarProducer] = Depends(get_producer)):
    """Health check endpoint"""
    checks = {}
    overall_status = HealthStatus.HEALTHY
    
    # Check Pulsar
    if producer:
        pulsar_health = producer.get_health_status()
        checks["pulsar"] = pulsar_health
        if not pulsar_health.get("connected", False):
            overall_status = HealthStatus.DEGRADED
    else:
        checks["pulsar"] = {"status": "not_connected"}
        overall_status = HealthStatus.DEGRADED
    
    return HealthCheckResponse(
        service_name=settings.service_name,
        status=overall_status,
        version=settings.service_version,
        timestamp=datetime.utcnow(),
        checks=checks,
        metadata={
            "uptime": "unknown",
            "environment": "development" if settings.debug else "production"
        }
    )


@app.get("/health/ready")
async def readiness_check():
    """Readiness check para Kubernetes"""
    return {"status": "ready"}


@app.get("/health/live")
async def liveness_check():
    """Liveness check para Kubernetes"""
    return {"status": "alive"}


# Event Collection Endpoints
@app.post("/collect/click", response_model=CollectClickResponse)
async def collect_click(
    request_data: CollectClickRequest,
    background_tasks: BackgroundTasks,
    client_request: Request,
    producer: Optional[PulsarProducer] = Depends(get_producer),
    _: None = Depends(rate_limit_check)
):
    """
    Recopilar evento de click
    
    - **campaign_id**: ID de la campaña (requerido)
    - **partner_id**: ID del partner (requerido)
    - **click_id**: ID del click (se genera si no se provee)
    - **session_id**: ID de sesión del usuario
    - **utm_params**: Parámetros UTM
    - **custom_params**: Parámetros personalizados
    """
    start_time = time.time()
    client_ip = get_client_ip(client_request)
    
    try:
        if producer:
            click_id = await producer.publish_click_command(request_data, client_ip)
        else:
            # Modo fallback sin Pulsar
            click_id = request_data.click_id or str(uuid.uuid4())
            logger.warning(f"Click procesado sin Pulsar: {click_id}")
        
        response = CollectClickResponse(
            click_id=click_id,
            status="SUCCESS",
            message="Click registered successfully",
            processed_at=datetime.utcnow()
        )
        
        # Log de métricas
        processing_time = (time.time() - start_time) * 1000
        logger.info(f"Click processed: {click_id} in {processing_time:.2f}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing click: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing click: {str(e)}"
        )


@app.post("/collect/impression", response_model=CollectImpressionResponse)
async def collect_impression(
    request_data: CollectImpressionRequest,
    client_request: Request,
    producer: Optional[PulsarProducer] = Depends(get_producer),
    _: None = Depends(rate_limit_check)
):
    """Recopilar evento de impresión"""
    client_ip = get_client_ip(client_request)
    
    try:
        if producer:
            impression_id = await producer.publish_impression_command(request_data)
        else:
            impression_id = request_data.impression_id or str(uuid.uuid4())
            logger.warning(f"Impression procesada sin Pulsar: {impression_id}")
        
        return CollectImpressionResponse(
            impression_id=impression_id,
            status="SUCCESS",
            message="Impression registered successfully",
            processed_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error processing impression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collect/conversion", response_model=CollectConversionResponse)
async def collect_conversion(
    request_data: CollectConversionRequest,
    client_request: Request,
    producer: Optional[PulsarProducer] = Depends(get_producer),
    _: None = Depends(rate_limit_check)
):
    """Recopilar evento de conversión"""
    client_ip = get_client_ip(client_request)
    
    try:
        if producer:
            conversion_id = await producer.publish_conversion_command(request_data)
        else:
            conversion_id = request_data.conversion_id or str(uuid.uuid4())
            logger.warning(f"Conversion procesada sin Pulsar: {conversion_id}")
        
        return CollectConversionResponse(
            conversion_id=conversion_id,
            status="SUCCESS",
            message="Conversion registered successfully",
            processed_at=datetime.utcnow(),
            attributed_click_id=request_data.click_id
        )
        
    except Exception as e:
        logger.error(f"Error processing conversion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch endpoints (para casos de alto volumen)
@app.post("/collect/batch")
async def collect_batch():
    """Endpoint para procesamiento en lote (futuro)"""
    return {"message": "Batch processing not implemented yet"}


# Métricas básicas
@app.get("/metrics")
async def metrics():
    """Endpoint de métricas básicas"""
    return {
        "service_name": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "requests_total": "not_implemented",
            "errors_total": "not_implemented",
            "pulsar_messages_sent": "not_implemented"
        }
    }


# Información de la aplicación
@app.get("/")
async def root():
    """Información básica del servicio"""
    return {
        "service": "ALPES Partners Event Collector",
        "version": settings.service_version,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "collect_click": "/collect/click",
            "collect_impression": "/collect/impression",
            "collect_conversion": "/collect/conversion",
            "metrics": "/metrics"
        }
    }


# Routers para organizar endpoints (para importar desde __init__.py)
from fastapi import APIRouter

health_router = APIRouter(prefix="/health", tags=["health"])
health_router.add_api_route("/", health_check, methods=["GET"])
health_router.add_api_route("/ready", readiness_check, methods=["GET"])
health_router.add_api_route("/live", liveness_check, methods=["GET"])

collector_router = APIRouter(prefix="/collect", tags=["collection"])
collector_router.add_api_route("/click", collect_click, methods=["POST"])
collector_router.add_api_route("/impression", collect_impression, methods=["POST"])
collector_router.add_api_route("/conversion", collect_conversion, methods=["POST"])
collector_router.add_api_route("/batch", collect_batch, methods=["POST"])
