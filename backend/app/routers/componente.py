from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_usuario_actual
from app.models.models import Componente, Conexion, Topologia, Proyecto, Usuario
from app.services.calculo_optico import TopologiaInvalidaError
from app.services.conexiones import validar_conexiones_en_edicion
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
    - Profesor: puede editar sus propios proyectos y leer los de los alumnos.
    """
    proyecto = _obtener_proyecto_de_topologia(topologia_id, db)
    if not proyecto:
        raise HTTPException(status_code=404, detail="La topología no existe")

    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre esta topología")

    if requerir_dueno and proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="Sólo podés editar componentes de tus propios proyectos")


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
    usuario: Usuario = Depends(get_usuario_actual),
):
    _verificar_acceso_topologia(componente.topologia_id, usuario, db, requerir_dueno=True)

    nuevo_componente = Componente(
        topologia_id=componente.topologia_id,
        tipo=componente.tipo,
        cantidad=componente.cantidad,
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


@router.put("/{componente_id}", response_model=ComponenteResponse)
def actualizar_componente(
    componente_id: int,
    datos: ComponenteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    """
    Actualiza los parámetros de un componente existente (RF-08 a RF-11).
    El campo topologia_id no se modifica: un componente no cambia de
    topología, solo se editan sus parámetros y posición.
    """
    componente = db.query(Componente).filter(Componente.id == componente_id).first()
    if not componente:
        raise HTTPException(status_code=404, detail="El componente no existe")

    _verificar_acceso_topologia(componente.topologia_id, usuario, db, requerir_dueno=True)

    if datos.topologia_id != componente.topologia_id:
        raise HTTPException(
            status_code=400,
            detail="No se puede mover un componente a otra topología"
        )

    # Validar el reemplazo antes de modificar el objeto persistido. Aumentar
    # la cantidad del lote también consume nuevas salidas del splitter.
    candidato = Componente(id=componente_id, **datos.model_dump())
    componentes = db.query(Componente).filter_by(topologia_id=componente.topologia_id).all()
    conexiones = db.query(Conexion).filter_by(topologia_id=componente.topologia_id).all()
    try:
        validar_conexiones_en_edicion(
            [candidato if c.id == componente_id else c for c in componentes], conexiones,
        )
    except TopologiaInvalidaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    componente.tipo = datos.tipo
    componente.cantidad = datos.cantidad
    componente.posicion_x = datos.posicion_x
    componente.posicion_y = datos.posicion_y
    componente.potencia_tx_dbm = datos.potencia_tx_dbm
    componente.clase_potencia = datos.clase_potencia
    componente.longitud_km = datos.longitud_km
    componente.atenuacion_db_km = datos.atenuacion_db_km
    componente.cantidad_conectores = datos.cantidad_conectores
    componente.cantidad_empalmes = datos.cantidad_empalmes
    componente.relacion_division = datos.relacion_division
    componente.sensibilidad_min_dbm = datos.sensibilidad_min_dbm
    componente.potencia_sobrecarga_dbm = datos.potencia_sobrecarga_dbm

    db.commit()
    db.refresh(componente)

    return componente


@router.delete("/{componente_id}", response_model=ComponenteResponse)
def eliminar_componente(
    componente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    componente = db.query(Componente).filter(Componente.id == componente_id).first()
    if not componente:
        raise HTTPException(status_code=404, detail="El componente no existe")

    _verificar_acceso_topologia(componente.topologia_id, usuario, db, requerir_dueno=True)

    db.delete(componente)
    db.commit()

    return componente
