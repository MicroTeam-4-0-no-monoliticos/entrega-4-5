"""
Configuración del Event Collector
"""
import os
from pydantic_settings import BaseSettings
from typing import List, Optional, Type


class Settings(BaseSettings):
    """Configuración del Event Collector/BFF"""
    
    # Información del servicio
    service_name: str = "event-collector"
    service_version: str = "1.0.0"
    
    # FastAPI settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Pulsar configuration
    pulsar_url: str = "pulsar://localhost:6650"
    pulsar_admin_url: str = "http://localhost:8080"
    
    # Topics configuration
    tracking_click_topic: str = "cmd.tracking.registerClick.v1"
    tracking_impression_topic: str = "cmd.tracking.registerImpression.v1"
    tracking_conversion_topic: str = "cmd.tracking.registerConversion.v1"
    campaign_create_topic: str = "cmd.campaign.createCampaign.v1"
    partner_register_topic: str = "cmd.partner.registerPartner.v1"
    
    # Rate limiting
    rate_limit_per_second: int = 1000
    rate_limit_per_partner_per_second: int = 100
    rate_limit_per_ip_per_minute: int = 1000
    
    # Validation settings
    max_payload_size_bytes: int = 1024 * 1024  # 1MB
    enable_deduplication: bool = True
    deduplication_window_minutes: int = 5
    
    # Security
    allowed_origins: List[str] = ["*"]
    blocked_ips: List[str] = []
    require_api_key: bool = False
    api_keys: List[str] = []
    
    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = True
    log_level: str = "INFO"
    
    # Pulsar producer settings
    producer_batch_size: int = 100
    producer_batch_timeout_ms: int = 1000
    producer_send_timeout_ms: int = 5000
    producer_max_pending_messages: int = 1000
    
    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    circuit_breaker_expected_exception: Type[Exception] = Exception
    
    model_config = {
        "env_prefix": "EVENT_COLLECTOR_",
        "case_sensitive": False
    }


# Instancia global de configuración
settings = Settings()


def get_settings() -> Settings:
    """Obtener configuración (útil para dependency injection en FastAPI)"""
    return settings
