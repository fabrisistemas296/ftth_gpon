from pydantic import BaseModel


class EscenarioPredefinidoCreate(BaseModel):
    nombre: str
    cantidad_usuarios_default: int
    distancia_tipica_km: float
    descripcion: str | None = None


class EscenarioPredefinidoResponse(BaseModel):
    id: int
    nombre: str
    cantidad_usuarios_default: int
    distancia_tipica_km: float
    descripcion: str | None

    class Config:
        from_attributes = True