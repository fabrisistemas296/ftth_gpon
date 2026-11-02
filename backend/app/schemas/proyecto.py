from pydantic import BaseModel


class ProyectoBase(BaseModel):
    nombre: str
    descripcion: str | None = None


class ProyectoCreate(ProyectoBase):
    pass
    # Sin campo usuario_id: se toma del token del usuario autenticado (ver router)


class ProyectoResponse(ProyectoBase):
    id: int
    usuario_id: int
    publicado: bool = False
    fecha_creacion: str
    fecha_modificacion: str

    class Config:
        from_attributes = True


class PublicacionProyecto(BaseModel):
    publicado: bool


class ProyectoPublicadoResponse(ProyectoResponse):
    autor: str
