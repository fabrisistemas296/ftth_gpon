from typing import Literal
from pydantic import BaseModel, model_validator


class SimulacionCreate(BaseModel):
    proyecto_id: int
    escenario_id: int | None = None
    # Opcional: si se omite y hay escenario_id, se autocompleta con el
    # valor por defecto del escenario (RF-22, RF-23). Si se especifica,
    # tiene prioridad sobre el valor del escenario.
    cantidad_usuarios: int | None = None
    tipo_consumo: Literal[
        "web",
        "streaming",
        "videoconferencia",
        "descarga"
    ]

    @model_validator(mode="after")
    def _validar_cantidad_usuarios_o_escenario(self):
        if self.cantidad_usuarios is None and self.escenario_id is None:
            raise ValueError(
                "Debés indicar 'cantidad_usuarios' o seleccionar un 'escenario_id' "
                "del cual tomar el valor por defecto."
            )
        return self


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