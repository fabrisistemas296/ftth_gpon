from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Componente, Topologia
from app.schemas.componente import (
    ComponenteCreate,
    ComponenteResponse
)


router = APIRouter(
    prefix="/componentes",
    tags=["Componentes"]
)


@router.get("/", response_model=list[ComponenteResponse])
def obtener_componentes(db: Session = Depends(get_db)):
    componentes = db.query(Componente).all()

    return componentes


@router.post("/", response_model=ComponenteResponse)
def crear_componente(
    componente: ComponenteCreate,
    db: Session = Depends(get_db)
):
    topologia = db.query(Topologia).filter(
        Topologia.id == componente.topologia_id
    ).first()

    if not topologia:
        raise HTTPException(
            status_code=404,
            detail="La topología no existe"
        )

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

@router.get("/{componente_id}", response_model=ComponenteResponse)
def obtener_componente(componente_id: int, db: Session = Depends(get_db)):
    componente = db.query(Componente).filter(
        Componente.id == componente_id
    ).first()

    if not componente:
        raise HTTPException(
            status_code=404,
            detail="El componente no existe"
        )

    return componente

@router.delete("/{componente_id}", response_model=ComponenteResponse)
def eliminar_componente(componente_id: int, db: Session = Depends(get_db)):
    componente = db.query(Componente).filter(
        Componente.id == componente_id
    ).first()

    if not componente:
        raise HTTPException(
            status_code=404,
            detail="El componente no existe"
        )

    db.delete(componente)
    db.commit()

    return componente