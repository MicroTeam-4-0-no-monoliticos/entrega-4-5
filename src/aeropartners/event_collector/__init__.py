"""
Event Collector / BFF Microservice
==================================

Microservicio Python (FastAPI) que actúa como Backend for Frontend (BFF) y Event Collector.

Responsabilidades:
- Recibir requests HTTP de clientes externos
- Validar y enriquecer los datos
- Serializar a Protobuf y publicar comandos en Apache Pulsar
- Proveer endpoints para health checks y métricas
- Rate limiting y validaciones de seguridad

Patrones aplicados:
- BFF (Backend for Frontend)
- Event-driven architecture
- Circuit breaker para Pulsar
- Request/Response validation
"""

from .app import app, health_router, collector_router
from .config import Settings
from .pulsar_client import PulsarProducer
from .models import CollectClickRequest, CollectClickResponse

__all__ = [
    'app',
    'health_router', 
    'collector_router',
    'Settings',
    'PulsarProducer',
    'CollectClickRequest',
    'CollectClickResponse'
]
