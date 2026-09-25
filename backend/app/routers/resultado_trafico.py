from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_alumno
from app.models.models import ResultadoTrafico, Simulacion, Proyecto, Usuario
from app.schemas.resultado_trafico import (
    ResultadoTraficoCreate,
    ResultadoTraficoResponse
)


router = APIRouter(
    prefix="/resultados-trafico",
    tags=["Resultados de Tráfico"]
)


def _obtener_proyecto_de_simulacion(simulacion_id: int, db: Session) -> tuple[Simulacion, Proyecto]:
    simulacion = db.query(Simulacion).filter(Simulacion.id == simulacion_id).first()
    if not simulacion:
        raise HTTPException(status_code=404, detail="La simulación no existe")

    proyecto = db.query(Proyecto).filter(Proyecto.id == simulacion.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto asociado no existe")

    return simulacion, proyecto


@router.get("/{resultado_id}", response_model=ResultadoTraficoResponse)
def obtener_resultado_trafico(
    resultado_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    resultado = db.query(ResultadoTrafico).filter(ResultadoTrafico.id == resultado_id).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="El resultado de tráfico no existe")

    _, proyecto = _obtener_proyecto_de_simulacion(resultado.simulacion_id, db)
    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre este resultado")

    return resultado


@router.post("/", response_model=ResultadoTraficoResponse)
def crear_resultado_trafico(
    datos: ResultadoTraficoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    _, proyecto = _obtener_proyecto_de_simulacion(datos.simulacion_id, db)

    if proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre esta simulación")

    resultado_existente = db.query(ResultadoTrafico).filter(
        ResultadoTrafico.simulacion_id == datos.simulacion_id
    ).first()
    if resultado_existente:
        raise HTTPException(status_code=400, detail="La simulación ya tiene un resultado de tráfico")

    nuevo_resultado = ResultadoTrafico(
        simulacion_id=datos.simulacion_id,
        throughput_mbps=datos.throughput_mbps,
        utilizacion_pct=datos.utilizacion_pct,
        congestion=datos.congestion
    )

    db.add(nuevo_resultado)
    db.commit()
    db.refresh(nuevo_resultado)

    return nuevo_resultado