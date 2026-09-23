from pydantic import BaseModel


class ConexionCreate(BaseModel):
    topologia_id: int
    componente_origen_id: int
    componente_destino_id: int


class ConexionResponse(BaseModel):
    id: int
    topologia_id: int
    componente_origen_id: int
    componente_destino_id: int

    class Config:
        from_attributes = True