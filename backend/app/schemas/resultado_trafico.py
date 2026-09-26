from pydantic import BaseModel


class ResultadoTraficoCreate(BaseModel):
    simulacion_id: int
    throughput_mbps: float
    throughput_por_usuario_mbps: float
    utilizacion_pct: float
    congestion: int
    tiempo_respuesta_ms: float


class ResultadoTraficoResponse(BaseModel):
    id: int
    simulacion_id: int
    throughput_mbps: float
    throughput_por_usuario_mbps: float | None
    utilizacion_pct: float
    congestion: int
    tiempo_respuesta_ms: float | None

    class Config:
        from_attributes = True