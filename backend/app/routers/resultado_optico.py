from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_alumno
from app.models.models import ResultadoOptico, Simulacion, Proyecto, Usuario
from app.schemas.resultado_optico import (
    ResultadoOpticoCreate,
    ResultadoOpticoResponse
)


router = APIRouter(
    prefix="/resultados-opticos",
    tags=["Resultados Ópticos"]
)


def _obtener_proyecto_de_simulacion(simulacion_id: int, db: Session) -> tuple[Simulacion, Proyecto]:
    simulacion = db.query(Simulacion).filter(Simulacion.id == simulacion_id).first()
    if not simulacion:
        raise HTTPException(status_code=404, detail="La simulación no existe")

    proyecto = db.query(Proyecto).filter(Proyecto.id == simulacion.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto asociado no existe")

    return simulacion, proyecto


@router.get("/{resultado_id}", response_model=ResultadoOpticoResponse)
def obtener_resultado_optico(
    resultado_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    resultado = db.query(ResultadoOptico).filter(ResultadoOptico.id == resultado_id).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="El resultado óptico no existe")

    _, proyecto = _obtener_proyecto_de_simulacion(resultado.simulacion_id, db)
    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre este resultado")

    return resultado


@router.post("/", response_model=ResultadoOpticoResponse)
def crear_resultado_optico(
    datos: ResultadoOpticoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    _, proyecto = _obtener_proyecto_de_simulacion(datos.simulacion_id, db)

    if proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre esta simulación")

    resultado_existente = db.query(ResultadoOptico).filter(
        ResultadoOptico.simulacion_id == datos.simulacion_id
    ).first()
    if resultado_existente:
        raise HTTPException(status_code=400, detail="La simulación ya tiene un resultado óptico")

    nuevo_resultado = ResultadoOptico(
        simulacion_id=datos.simulacion_id,
        perdida_total_db=datos.perdida_total_db,
        potencia_recibida_dbm=datos.potencia_recibida_dbm,
        estado_operativo=datos.estado_operativo
    )

    db.add(nuevo_resultado)
    db.commit()
    db.refresh(nuevo_resultado)

    return nuevo_resultado