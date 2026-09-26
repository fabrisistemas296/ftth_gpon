"""
app/schemas/proyecto_detalle.py

Schemas de solo lectura para la "vista completa" de un proyecto:
agrupan en una única respuesta la topología (con sus componentes y
conexiones) y todas las simulaciones ejecutadas (con sus resultados),
para que el Profesor (o el propio Alumno) no tenga que encadenar
varias llamadas a la API para ver el estado de un proyecto.
"""

from pydantic import BaseModel

from app.schemas.componente import ComponenteResponse
from app.schemas.conexion import ConexionResponse
from app.schemas.resultado_optico import ResultadoOpticoResponse
from app.schemas.resultado_trafico import ResultadoTraficoResponse


class TopologiaDetalleResponse(BaseModel):
    id: int
    proyecto_id: int
    componentes: list[ComponenteResponse]
    conexiones: list[ConexionResponse]

    class Config:
        from_attributes = True


class SimulacionDetalleResponse(BaseModel):
    id: int
    escenario_id: int | None
    fecha_ejecucion: str
    cantidad_usuarios: int
    tipo_consumo: str
    resultado_optico: ResultadoOpticoResponse | None
    resultado_trafico: ResultadoTraficoResponse | None

    class Config:
        from_attributes = True


class ProyectoDetalleResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    usuario_id: int
    fecha_creacion: str
    fecha_modificacion: str
    topologia: TopologiaDetalleResponse | None
    simulaciones: list[SimulacionDetalleResponse]

    class Config:
        from_attributes = True
