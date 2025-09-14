"""
Modelos Pydantic para validación de requests/responses
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Estados de salud del servicio"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CollectClickRequest(BaseModel):
    """Request para registrar un click"""
    click_id: Optional[str] = Field(None, description="ID único del click (se genera si no se provee)")
    campaign_id: str = Field(..., description="ID de la campaña", min_length=1, max_length=50)
    partner_id: str = Field(..., description="ID del partner", min_length=1, max_length=50)
    session_id: Optional[str] = Field(None, description="ID de sesión del usuario")
    user_agent: Optional[str] = Field(None, description="User agent del navegador")
    ip_address: Optional[str] = Field(None, description="IP del usuario")
    referrer: Optional[str] = Field(None, description="URL de referencia")
    landing_url: Optional[str] = Field(None, description="URL de destino")
    utm_params: Optional[Dict[str, str]] = Field(default_factory=dict, description="Parámetros UTM")
    custom_params: Optional[Dict[str, str]] = Field(default_factory=dict, description="Parámetros personalizados")
    
    @validator('campaign_id', 'partner_id')
    def validate_ids(cls, v):
        if not v or not v.strip():
            raise ValueError('ID no puede estar vacío')
        return v.strip()
    
    @validator('utm_params', 'custom_params')
    def validate_params(cls, v):
        if v is None:
            return {}
        # Limitar número de parámetros para evitar payloads muy grandes
        if len(v) > 20:
            raise ValueError('Máximo 20 parámetros permitidos')
        return v


class CollectClickResponse(BaseModel):
    """Response al registrar un click"""
    click_id: str = Field(..., description="ID del click generado/confirmado")
    status: str = Field(..., description="Estado del procesamiento")
    message: str = Field(..., description="Mensaje descriptivo")
    processed_at: datetime = Field(..., description="Timestamp de procesamiento")


class CollectImpressionRequest(BaseModel):
    """Request para registrar una impresión"""
    impression_id: Optional[str] = Field(None, description="ID único de la impresión")
    campaign_id: str = Field(..., description="ID de la campaña")
    partner_id: str = Field(..., description="ID del partner")
    session_id: Optional[str] = Field(None, description="ID de sesión")
    ad_creative_id: Optional[str] = Field(None, description="ID del creative/banner")
    placement_id: Optional[str] = Field(None, description="ID del placement")
    view_duration_ms: Optional[int] = Field(None, description="Duración de visualización en ms", ge=0)
    custom_params: Optional[Dict[str, str]] = Field(default_factory=dict)


class CollectImpressionResponse(BaseModel):
    """Response al registrar una impresión"""
    impression_id: str
    status: str
    message: str
    processed_at: datetime


class CollectConversionRequest(BaseModel):
    """Request para registrar una conversión"""
    conversion_id: Optional[str] = Field(None, description="ID único de la conversión")
    click_id: Optional[str] = Field(None, description="ID del click asociado")
    campaign_id: str = Field(..., description="ID de la campaña")
    partner_id: str = Field(..., description="ID del partner")
    session_id: Optional[str] = Field(None, description="ID de sesión")
    conversion_type: str = Field(..., description="Tipo de conversión (PURCHASE, SIGNUP, etc)")
    value_amount: Optional[float] = Field(None, description="Valor de la conversión", ge=0)
    value_currency: str = Field(default="USD", description="Moneda del valor")
    order_id: Optional[str] = Field(None, description="ID de la orden")
    customer_id: Optional[str] = Field(None, description="ID del customer")
    conversion_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Datos adicionales")


class CollectConversionResponse(BaseModel):
    """Response al registrar una conversión"""
    conversion_id: str
    status: str
    message: str
    processed_at: datetime
    attributed_click_id: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response del health check"""
    service_name: str
    status: HealthStatus
    version: str
    timestamp: datetime
    checks: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    """Response con métricas del servicio"""
    service_name: str
    timestamp: datetime
    metrics: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Response de error estándar"""
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    trace_id: Optional[str] = None
