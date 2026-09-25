from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_alumno
from app.models.models import Conexion, Topologia, Componente, Proyecto, Usuario
from app.schemas.conexion import ConexionCreate, ConexionResponse


router = APIRouter(
    prefix="/conexiones",
    tags=["Conexiones"]
)


def _verificar_acceso_topologia(topologia_id: int, usuario: Usuario, db: Session):
    topologia = db.query(Topologia).filter(Topologia.id == topologia_id).first()
    if not topologia:
        raise HTTPException(status_code=404, detail="La topología no existe")

    proyecto = db.query(Proyecto).filter(Proyecto.id == topologia.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto asociado no existe")

    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre esta topología")


def validar_conexion(conexion: ConexionCreate, db: Session):
    topologia = db.query(Topologia).filter(Topologia.id == conexion.topologia_id).first()
    if not topologia:
        raise HTTPException(status_code=404, detail="La topología no existe")

    componente_origen = db.query(Componente).filter(
        Componente.id == conexion.componente_origen_id
    ).first()
    if not componente_origen:
        raise HTTPException(status_code=404, detail="El componente origen no existe")

    componente_destino = db.query(Componente).filter(
        Componente.id == conexion.componente_destino_id
    ).first()
    if not componente_destino:
        raise HTTPException(status_code=404, detail="El componente destino no existe")

    if conexion.componente_origen_id == conexion.componente_destino_id:
        raise HTTPException(
            status_code=400,
            detail="El componente origen y destino no pueden ser iguales"
        )

    if componente_origen.topologia_id != conexion.topologia_id:
        raise HTTPException(
            status_code=400,
            detail="El componente origen no pertenece a la topología indicada"
        )

    if componente_destino.topologia_id != conexion.topologia_id:
        raise HTTPException(
            status_code=400,
            detail="El componente destino no pertenece a la topología indicada"
        )


@router.get("/{conexion_id}", response_model=ConexionResponse)
def obtener_conexion(
    conexion_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    conexion = db.query(Conexion).filter(Conexion.id == conexion_id).first()
    if not conexion:
        raise HTTPException(status_code=404, detail="La conexión no existe")

    _verificar_acceso_topologia(conexion.topologia_id, usuario, db)

    return conexion


@router.post("/", response_model=ConexionResponse)
def crear_conexion(
    conexion: ConexionCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    validar_conexion(conexion, db)
    _verificar_acceso_topologia(conexion.topologia_id, usuario, db)

    nueva_conexion = Conexion(
        topologia_id=conexion.topologia_id,
        componente_origen_id=conexion.componente_origen_id,
        componente_destino_id=conexion.componente_destino_id
    )

    db.add(nueva_conexion)
    db.commit()
    db.refresh(nueva_conexion)

    return nueva_conexion


@router.put("/{conexion_id}", response_model=ConexionResponse)
def modificar_conexion(
    conexion_id: int,
    conexion_data: ConexionCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    conexion = db.query(Conexion).filter(Conexion.id == conexion_id).first()
    if not conexion:
        raise HTTPException(status_code=404, detail="La conexión no existe")

    validar_conexion(conexion_data, db)
    _verificar_acceso_topologia(conexion_data.topologia_id, usuario, db)

    conexion.topologia_id = conexion_data.topologia_id
    conexion.componente_origen_id = conexion_data.componente_origen_id
    conexion.componente_destino_id = conexion_data.componente_destino_id

    db.commit()
    db.refresh(conexion)

    return conexion


@router.delete("/{conexion_id}")
def eliminar_conexion(
    conexion_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    conexion = db.query(Conexion).filter(Conexion.id == conexion_id).first()
    if not conexion:
        raise HTTPException(status_code=404, detail="La conexión no existe")

    _verificar_acceso_topologia(conexion.topologia_id, usuario, db)

    db.delete(conexion)
    db.commit()

    return {"message": "Conexión eliminada correctamente"}