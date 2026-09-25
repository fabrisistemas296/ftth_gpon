from pydantic import BaseModel


class ResultadoTraficoCreate(BaseModel):
    simulacion_id: int
    throughput_mbps: float
    utilizacion_pct: float
    congestion: int


class ResultadoTraficoResponse(BaseModel):
    id: int
    simulacion_id: int
    throughput_mbps: float
    utilizacion_pct: float
    congestion: int

    class Config:
        from_attributes = True