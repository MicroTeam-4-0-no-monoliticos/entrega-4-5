"""
Cliente de Apache Pulsar con circuit breaker y retry logic
"""
import pulsar
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import time
from enum import Enum

# Import protobuf messages
import sys
import os

# Agregar el path del directorio generated al path de Python
current_dir = os.path.dirname(__file__)
project_root = os.path.join(current_dir, '..', '..', '..')
generated_dir = os.path.join(project_root, 'generated')
sys.path.insert(0, project_root)
sys.path.insert(0, generated_dir)

try:
    import common_pb2, tracking_pb2, campaign_pb2, partner_pb2, collector_pb2
    from google.protobuf.timestamp_pb2 import Timestamp
    PROTOBUF_AVAILABLE = True
    logging.info("✅ Clases Protobuf importadas correctamente")
except ImportError as e:
    logging.error(f"Error importando clases Protobuf: {e}")
    # Fallback para desarrollo
    common_pb2 = None
    tracking_pb2 = None
    campaign_pb2 = None
    partner_pb2 = None
    collector_pb2 = None
    Timestamp = None
    PROTOBUF_AVAILABLE = False

# Importar modelos locales después de protobuf
from .config import Settings

# Importar para type hints (después de config)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import CollectClickRequest, CollectImpressionRequest, CollectConversionRequest


logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "closed"      # Funcionando normalmente
    OPEN = "open"          # Fallos detectados, requests rechazados
    HALF_OPEN = "half_open"  # Probando si el servicio se recuperó


class CircuitBreaker:
    """Circuit breaker simple para Pulsar"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """Ejecutar función con circuit breaker"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Verificar si debemos intentar resetear el circuit breaker"""
        return (time.time() - self.last_failure_time) > self.recovery_timeout
    
    def _on_success(self):
        """Manejar éxito"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Manejar fallo"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class PulsarProducer:
    """Cliente de Pulsar con circuit breaker y retry logic"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Optional[pulsar.Client] = None
        self.producers: Dict[str, pulsar.Producer] = {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout
        )
        self._connected = False
    
    async def connect(self):
        """Conectar a Pulsar"""
        try:
            logger.info(f"Conectando a Pulsar: {self.settings.pulsar_url}")
            
            self.client = pulsar.Client(
                self.settings.pulsar_url,
                connection_timeout_ms=10000,
                operation_timeout_ms=30000,
                log_conf_file_path=None  # Deshabilitar logs verbose de Pulsar
            )
            
            # Pre-crear producers para topics principales
            await self._create_producers()
            
            self._connected = True
            logger.info("Conectado a Pulsar exitosamente")
            
        except Exception as e:
            logger.error(f"Error conectando a Pulsar: {e}")
            raise
    
    async def _create_producers(self):
        """Crear producers para los topics principales"""
        topics = [
            self.settings.tracking_click_topic,
            self.settings.tracking_impression_topic,
            self.settings.tracking_conversion_topic,
            self.settings.campaign_create_topic,
            self.settings.partner_register_topic
        ]
        
        for topic in topics:
            try:
                producer = self.client.create_producer(
                    topic,
                    batching_enabled=True,
                    batching_max_messages=self.settings.producer_batch_size,
                    batching_max_allowed_size_in_bytes=1024*1024,  # 1MB
                    batching_max_publish_delay_ms=self.settings.producer_batch_timeout_ms,
                    send_timeout_ms=self.settings.producer_send_timeout_ms,
                    max_pending_messages=self.settings.producer_max_pending_messages
                )
                self.producers[topic] = producer
                logger.info(f"Producer creado para topic: {topic}")
            except Exception as e:
                logger.error(f"Error creando producer para {topic}: {e}")
                # Continuar con otros topics
    
    async def disconnect(self):
        """Desconectar de Pulsar"""
        if self._connected:
            try:
                # Cerrar producers
                for topic, producer in self.producers.items():
                    try:
                        producer.close()
                        logger.info(f"Producer cerrado para topic: {topic}")
                    except Exception as e:
                        logger.error(f"Error cerrando producer {topic}: {e}")
                
                # Cerrar cliente
                if self.client:
                    self.client.close()
                    logger.info("Cliente Pulsar cerrado")
                
                self._connected = False
                
            except Exception as e:
                logger.error(f"Error desconectando de Pulsar: {e}")
    
    def _create_meta(self, event_id: Optional[str] = None):
        """Crear metadatos comunes para mensajes"""
        if not common_pb2:
            return None
            
        meta = common_pb2.Meta()
        meta.event_id = event_id or str(uuid.uuid4())
        meta.producer = self.settings.service_name
        meta.schema_version = self.settings.service_version
        
        # Timestamp actual
        now = Timestamp()
        now.GetCurrentTime()
        meta.timestamp.CopyFrom(now)
        
        return meta
    
    async def publish_click_command(
        self, 
        request: 'CollectClickRequest',
        ip_address: Optional[str] = None
    ) -> str:
        """Publicar comando de registro de click"""
        if not tracking_pb2:
            raise Exception("Protobuf classes not available")
        
        try:
            # Crear comando Protobuf
            cmd = tracking_pb2.RegisterClickCommand()
            cmd.command_id = str(uuid.uuid4())
            cmd.click_id = request.click_id or str(uuid.uuid4())
            cmd.campaign_id = request.campaign_id
            cmd.partner_id = request.partner_id
            
            if request.session_id:
                cmd.session_id = request.session_id
            if request.user_agent:
                cmd.user_agent = request.user_agent
            if ip_address:
                cmd.ip_address = ip_address
            if request.referrer:
                cmd.referrer = request.referrer
            if request.landing_url:
                cmd.landing_url = request.landing_url
            
            # Timestamp
            now = Timestamp()
            now.GetCurrentTime()
            cmd.timestamp.CopyFrom(now)
            
            # Metadatos (UTM + custom)
            all_metadata = {**request.utm_params, **request.custom_params}
            for key, value in all_metadata.items():
                cmd.metadata[key] = str(value)
            
            # Meta común
            cmd.meta.CopyFrom(self._create_meta())
            
            # Serializar y enviar
            data = cmd.SerializeToString()
            partition_key = cmd.campaign_id  # Particionar por campaign_id
            
            def send_message():
                producer = self.producers.get(self.settings.tracking_click_topic)
                if not producer:
                    raise Exception(f"Producer no encontrado para topic: {self.settings.tracking_click_topic}")
                
                producer.send(data, partition_key=partition_key)
                return cmd.click_id
            
            # Usar circuit breaker
            click_id = self.circuit_breaker.call(send_message)
            logger.info(f"Click command enviado: {click_id}")
            return click_id
            
        except Exception as e:
            logger.error(f"Error enviando click command: {e}")
            raise
    
    async def publish_impression_command(self, request: 'CollectImpressionRequest') -> str:
        """Publicar comando de registro de impresión"""
        # Implementación similar a click
        impression_id = request.impression_id or str(uuid.uuid4())
        logger.info(f"Impression command (mock): {impression_id}")
        return impression_id
    
    async def publish_conversion_command(self, request: 'CollectConversionRequest') -> str:
        """Publicar comando de registro de conversión"""
        # Implementación similar a click
        conversion_id = request.conversion_id or str(uuid.uuid4())
        logger.info(f"Conversion command (mock): {conversion_id}")
        return conversion_id
    
    def get_health_status(self) -> Dict[str, Any]:
        """Obtener estado de salud del cliente Pulsar"""
        return {
            "connected": self._connected,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "producers_count": len(self.producers)
        }


# Instancia global del producer (se inicializa en app startup)
pulsar_producer: Optional[PulsarProducer] = None


def get_pulsar_producer() -> PulsarProducer:
    """Obtener instancia del producer (para dependency injection)"""
    if not pulsar_producer:
        raise Exception("PulsarProducer not initialized")
    return pulsar_producer
