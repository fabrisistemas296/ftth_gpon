from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_alumno
from app.models.models import Proyecto, Usuario
from app.schemas.proyecto import ProyectoCreate, ProyectoResponse

router = APIRouter(
    prefix="/proyectos",
    tags=["Proyectos"]
)


def _verificar_acceso_proyecto(proyecto: Proyecto, usuario: Usuario):
    """
    Un alumno solo puede acceder a sus propios proyectos.
    Un profesor puede acceder (solo lectura) a cualquier proyecto.
    """
    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para acceder a este proyecto"
        )


@router.get("/", response_model=list[ProyectoResponse])
def obtener_proyectos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    """
    Alumno: ve solo sus propios proyectos.
    Profesor: ve los proyectos de todos los alumnos (RF-06).
    """
    if usuario.rol == "profesor":
        return db.query(Proyecto).all()

    return db.query(Proyecto).filter(Proyecto.usuario_id == usuario.id).all()


@router.post("/", response_model=ProyectoResponse)
def crear_proyecto(
    proyecto: ProyectoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),  # solo alumnos crean proyectos
):
    nuevo_proyecto = Proyecto(
        nombre=proyecto.nombre,
        descripcion=proyecto.descripcion,
        usuario_id=usuario.id,  # <- del token, NUNCA del body (evita crear a nombre de otro)
    )

    db.add(nuevo_proyecto)
    db.commit()
    db.refresh(nuevo_proyecto)

    return nuevo_proyecto


@router.get("/{proyecto_id}", response_model=ProyectoResponse)
def obtener_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    _verificar_acceso_proyecto(proyecto, usuario)

    return proyecto


@router.put("/{proyecto_id}", response_model=ProyectoResponse)
def actualizar_proyecto(
    proyecto_id: int,
    proyecto_data: ProyectoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),  # profesores no editan (solo lectura)
):
    proyecto_existente = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto_existente:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    if proyecto_existente.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para editar este proyecto"
        )

    proyecto_existente.nombre = proyecto_data.nombre
    proyecto_existente.descripcion = proyecto_data.descripcion
    # usuario_id NO se actualiza: el dueño de un proyecto no cambia
    proyecto_existente.fecha_modificacion = datetime.now(timezone.utc).isoformat(
        sep=" ", timespec="seconds"
    )

    db.commit()
    db.refresh(proyecto_existente)

    return proyecto_existente


@router.delete("/{proyecto_id}", response_model=ProyectoResponse)
def eliminar_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    if proyecto.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para eliminar este proyecto"
        )

    db.delete(proyecto)
    db.commit()

    return proyecto