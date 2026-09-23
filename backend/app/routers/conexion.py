from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Conexion, Topologia, Componente
from app.schemas.conexion import ConexionCreate, ConexionResponse


router = APIRouter(
    prefix="/conexiones",
    tags=["Conexiones"]
)


@router.get("/", response_model=list[ConexionResponse])
def obtener_conexiones(db: Session = Depends(get_db)):
    conexiones = db.query(Conexion).all()

    return conexiones


@router.post("/", response_model=ConexionResponse)
def crear_conexion(
    conexion: ConexionCreate,
    db: Session = Depends(get_db)
):
    # Verificar que exista la topología
    topologia = db.query(Topologia).filter(
        Topologia.id == conexion.topologia_id
    ).first()

    if not topologia:
        raise HTTPException(
            status_code=404,
            detail="La topología no existe"
        )

    # Verificar que exista el componente origen
    componente_origen = db.query(Componente).filter(
        Componente.id == conexion.componente_origen_id
    ).first()

    if not componente_origen:
        raise HTTPException(
            status_code=404,
            detail="El componente origen no existe"
        )

    # Verificar que exista el componente destino
    componente_destino = db.query(Componente).filter(
        Componente.id == conexion.componente_destino_id
    ).first()

    if not componente_destino:
        raise HTTPException(
            status_code=404,
            detail="El componente destino no existe"
        )

    # No permitir conectar un componente consigo mismo
    if conexion.componente_origen_id == conexion.componente_destino_id:
        raise HTTPException(
            status_code=400,
            detail="El componente origen y destino no pueden ser iguales"
        )

    # Verificar que ambos componentes pertenezcan a la misma topología
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
    db: Session = Depends(get_db)
):
    conexion = db.query(Conexion).filter(
        Conexion.id == conexion_id
    ).first()

    if not conexion:
        raise HTTPException(
            status_code=404,
            detail="La conexión no existe"
        )

    validar_conexion(conexion_data, db)

    conexion.topologia_id = conexion_data.topologia_id
    conexion.componente_origen_id = conexion_data.componente_origen_id
    conexion.componente_destino_id = conexion_data.componente_destino_id

    db.commit()
    db.refresh(conexion)

    return conexion

@router.delete("/{conexion_id}")
def eliminar_conexion(
    conexion_id: int,
    db: Session = Depends(get_db)
):
    conexion = db.query(Conexion).filter(
        Conexion.id == conexion_id
    ).first()

    if not conexion:
        raise HTTPException(
            status_code=404,
            detail="La conexión no existe"
        )

    db.delete(conexion)
    db.commit()

    return {
        "message": "Conexión eliminada correctamente"
    }


def validar_conexion(
    conexion: ConexionCreate,
    db: Session
):
    topologia = db.query(Topologia).filter(
        Topologia.id == conexion.topologia_id
    ).first()

    if not topologia:
        raise HTTPException(
            status_code=404,
            detail="La topología no existe"
        )

    componente_origen = db.query(Componente).filter(
        Componente.id == conexion.componente_origen_id
    ).first()

    if not componente_origen:
        raise HTTPException(
            status_code=404,
            detail="El componente origen no existe"
        )

    componente_destino = db.query(Componente).filter(
        Componente.id == conexion.componente_destino_id
    ).first()

    if not componente_destino:
        raise HTTPException(
            status_code=404,
            detail="El componente destino no existe"
        )

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