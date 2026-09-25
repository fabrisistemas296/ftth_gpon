from typing import Literal
from pydantic import BaseModel


class ResultadoOpticoCreate(BaseModel):
    simulacion_id: int
    perdida_total_db: float
    potencia_recibida_dbm: float
    estado_operativo: Literal[
        "operativo",
        "fuera_de_rango"
    ]


class ResultadoOpticoResponse(BaseModel):
    id: int
    simulacion_id: int
    perdida_total_db: float
    potencia_recibida_dbm: float
    estado_operativo: str

    class Config:
        from_attributes = True