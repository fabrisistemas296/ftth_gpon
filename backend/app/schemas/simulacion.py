from typing import Literal
from pydantic import BaseModel


class SimulacionCreate(BaseModel):
    proyecto_id: int
    escenario_id: int | None = None
    cantidad_usuarios: int
    tipo_consumo: Literal[
        "web",
        "streaming",
        "videoconferencia",
        "descarga"
    ]


class SimulacionResponse(BaseModel):
    id: int
    proyecto_id: int
    escenario_id: int | None
    fecha_ejecucion: str
    cantidad_usuarios: int
    tipo_consumo: Literal[
        "web",
        "streaming",
        "videoconferencia",
        "descarga"
    ]

    class Config:
        from_attributes = True