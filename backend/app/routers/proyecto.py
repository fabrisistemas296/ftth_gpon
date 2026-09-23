from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Proyecto
from app.schemas.proyecto import ProyectoCreate, ProyectoResponse

router = APIRouter(
    prefix="/proyectos",
    tags=["Proyectos"]
)

@router.get("/", response_model=list[ProyectoResponse])
def obtener_proyectos(db: Session = Depends(get_db)):
    proyectos = db.query(Proyecto).all()
    return proyectos

@router.post("/", response_model=ProyectoResponse)
def crear_proyecto(
    proyecto: ProyectoCreate,
    db: Session = Depends(get_db)
):
    nuevo_proyecto = Proyecto(
        nombre=proyecto.nombre,
        descripcion=proyecto.descripcion,
        usuario_id=proyecto.usuario_id
    )

    db.add(nuevo_proyecto)
    db.commit()
    db.refresh(nuevo_proyecto)

    return nuevo_proyecto

@router.get("/{proyecto_id}", response_model=ProyectoResponse)
def obtener_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto

@router.put("/{proyecto_id}", response_model=ProyectoResponse)
def actualizar_proyecto(
    proyecto_id: int,
    proyecto: ProyectoCreate,
    db: Session = Depends(get_db)
):
    proyecto_existente = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto_existente:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    proyecto_existente.nombre = proyecto.nombre
    proyecto_existente.descripcion = proyecto.descripcion
    proyecto_existente.usuario_id = proyecto.usuario_id
    proyecto_existente.fecha_modificacion = text("(datetime('now'))")

    db.commit()
    db.refresh(proyecto_existente)

    return proyecto_existente

@router.delete("/{proyecto_id}", response_model=ProyectoResponse)
def eliminar_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    db.delete(proyecto)
    db.commit()

    return proyecto
