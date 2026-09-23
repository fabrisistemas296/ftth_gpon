from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Topologia, Proyecto
from app.schemas.topologia import TopologiaCreate, TopologiaResponse


router = APIRouter(
    prefix="/topologias",
    tags=["Topologías"]
)


@router.get("/", response_model=list[TopologiaResponse])
def obtener_topologias(db: Session = Depends(get_db)):
    topologias = db.query(Topologia).all()

    return topologias


@router.post("/", response_model=TopologiaResponse)
def crear_topologia(
    topologia: TopologiaCreate,
    db: Session = Depends(get_db)
):
    proyecto = db.query(Proyecto).filter(
        Proyecto.id == topologia.proyecto_id
    ).first()

    if not proyecto:
        raise HTTPException(
            status_code=404,
            detail="El proyecto no existe"
        )

    topologia_existente = db.query(Topologia).filter(
        Topologia.proyecto_id == topologia.proyecto_id
    ).first()

    if topologia_existente:
        raise HTTPException(
            status_code=400,
            detail="El proyecto ya tiene una topología"
        )

    nueva_topologia = Topologia(
        proyecto_id=topologia.proyecto_id
    )

    db.add(nueva_topologia)
    db.commit()
    db.refresh(nueva_topologia)

    return nueva_topologia

@router.get("/{topologia_id}", response_model=TopologiaResponse)
def obtener_topologia(topologia_id: int, db: Session = Depends(get_db)):
    topologia = db.query(Topologia).filter(
        Topologia.id == topologia_id
    ).first()

    if not topologia:
        raise HTTPException(
            status_code=404,
            detail="Topología no encontrada"
        )

    return topologia



@router.delete("/{topologia_id}", response_model=TopologiaResponse)
def eliminar_topologia(topologia_id: int, db: Session = Depends(get_db)):
    topologia = db.query(Topologia).filter(
        Topologia.id == topologia_id
    ).first()

    if not topologia:
        raise HTTPException(
            status_code=404,
            detail="Topología no encontrada"
        )

    db.delete(topologia)
    db.commit()

    return topologia

