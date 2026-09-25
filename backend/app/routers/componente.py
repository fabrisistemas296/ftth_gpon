from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_alumno
from app.models.models import Componente, Topologia, Proyecto, Usuario
from app.schemas.componente import (
    ComponenteCreate,
    ComponenteResponse
)


router = APIRouter(
    prefix="/componentes",
    tags=["Componentes"]
)


def _obtener_proyecto_de_topologia(topologia_id: int, db: Session) -> Proyecto | None:
    topologia = db.query(Topologia).filter(Topologia.id == topologia_id).first()
    if not topologia:
        return None
    return db.query(Proyecto).filter(Proyecto.id == topologia.proyecto_id).first()


def _verificar_acceso_topologia(topologia_id: int, usuario: Usuario, db: Session, requerir_dueno: bool = False):
    """
    Verifica que el usuario pueda acceder a la topología indicada.
    - Alumno: solo si es dueño del proyecto asociado.
    - Profesor: solo lectura (requerir_dueno=True lo bloquea siempre,
      porque un profesor nunca es "dueño" de un proyecto de alumno).
    """
    proyecto = _obtener_proyecto_de_topologia(topologia_id, db)
    if not proyecto:
        raise HTTPException(status_code=404, detail="La topología no existe")

    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre esta topología")

    if requerir_dueno and usuario.rol != "alumno":
        raise HTTPException(status_code=403, detail="Esta acción requiere ser el alumno dueño del proyecto")


@router.get("/{componente_id}", response_model=ComponenteResponse)
def obtener_componente(
    componente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    componente = db.query(Componente).filter(Componente.id == componente_id).first()
    if not componente:
        raise HTTPException(status_code=404, detail="El componente no existe")

    _verificar_acceso_topologia(componente.topologia_id, usuario, db)

    return componente


@router.post("/", response_model=ComponenteResponse)
def crear_componente(
    componente: ComponenteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    _verificar_acceso_topologia(componente.topologia_id, usuario, db, requerir_dueno=True)

    nuevo_componente = Componente(
        topologia_id=componente.topologia_id,
        tipo=componente.tipo,
        posicion_x=componente.posicion_x,
        posicion_y=componente.posicion_y,
        potencia_tx_dbm=componente.potencia_tx_dbm,
        clase_potencia=componente.clase_potencia,
        longitud_km=componente.longitud_km,
        atenuacion_db_km=componente.atenuacion_db_km,
        cantidad_conectores=componente.cantidad_conectores,
        cantidad_empalmes=componente.cantidad_empalmes,
        relacion_division=componente.relacion_division,
        sensibilidad_min_dbm=componente.sensibilidad_min_dbm,
        potencia_sobrecarga_dbm=componente.potencia_sobrecarga_dbm
    )

    db.add(nuevo_componente)
    db.commit()
    db.refresh(nuevo_componente)

    return nuevo_componente


@router.delete("/{componente_id}", response_model=ComponenteResponse)
def eliminar_componente(
    componente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    componente = db.query(Componente).filter(Componente.id == componente_id).first()
    if not componente:
        raise HTTPException(status_code=404, detail="El componente no existe")

    _verificar_acceso_topologia(componente.topologia_id, usuario, db, requerir_dueno=True)

    db.delete(componente)
    db.commit()

    return componente