from pydantic import BaseModel



class ProyectoBase(BaseModel):
    nombre: str
    descripcion: str | None = None


class ProyectoCreate(ProyectoBase):
    usuario_id: int


class ProyectoResponse(ProyectoBase):
    id: int
    usuario_id: int
    fecha_creacion: str
    fecha_modificacion: str

    class Config:
        from_attributes = True