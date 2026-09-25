from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_profesor
from app.models.models import EscenarioPredefinido, Usuario
from app.schemas.escenario_predefinido import (
    EscenarioPredefinidoCreate,
    EscenarioPredefinidoResponse
)


router = APIRouter(
    prefix="/escenarios",
    tags=["Escenarios Predefinidos"]
)


@router.get("/", response_model=list[EscenarioPredefinidoResponse])
def obtener_escenarios(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_usuario_actual),  # cualquier usuario logueado
):
    """Catálogo de referencia: visible para alumnos y profesores (RF-18/RF-19)."""
    return db.query(EscenarioPredefinido).all()


@router.get("/{escenario_id}", response_model=EscenarioPredefinidoResponse)
def obtener_escenario(
    escenario_id: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_usuario_actual),
):
    escenario = db.query(EscenarioPredefinido).filter(
        EscenarioPredefinido.id == escenario_id
    ).first()

    if not escenario:
        raise HTTPException(status_code=404, detail="El escenario no existe")

    return escenario


@router.put("/{escenario_id}", response_model=EscenarioPredefinidoResponse)
def modificar_escenario(
    escenario_id: int,
    datos: EscenarioPredefinidoCreate,
    db: Session = Depends(get_db),
    _profesor: Usuario = Depends(requerir_rol_profesor),  # solo el profesor edita el catálogo
):
    escenario = db.query(EscenarioPredefinido).filter(
        EscenarioPredefinido.id == escenario_id
    ).first()

    if not escenario:
        raise HTTPException(status_code=404, detail="El escenario no existe")

    escenario.nombre = datos.nombre
    escenario.cantidad_usuarios_default = datos.cantidad_usuarios_default
    escenario.distancia_tipica_km = datos.distancia_tipica_km
    escenario.descripcion = datos.descripcion

    db.commit()
    db.refresh(escenario)

    return escenario