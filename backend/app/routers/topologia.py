from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_usuario_actual
from app.models.models import Topologia, Proyecto, Usuario, Componente, Conexion
from app.schemas.topologia import TopologiaCreate, TopologiaResponse
from app.schemas.viabilidad import TopologiaPrevia, ViabilidadResponse
from app.services.viabilidad import evaluar_viabilidad


router = APIRouter(
    prefix="/topologias",
    tags=["Topologías"]
)


def _obtener_proyecto_o_404(proyecto_id: int, db: Session) -> Proyecto:
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto no existe")
    return proyecto


def _verificar_acceso_topologia(topologia: Topologia, usuario: Usuario, db: Session):
    proyecto = db.query(Proyecto).filter(Proyecto.id == topologia.proyecto_id).first()
    if usuario.rol == "alumno" and (not proyecto or proyecto.usuario_id != usuario.id):
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para acceder a esta topología"
        )


@router.post("/", response_model=TopologiaResponse)
def crear_topologia(
    topologia: TopologiaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    proyecto = _obtener_proyecto_o_404(topologia.proyecto_id, db)

    if proyecto.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para crear una topología en este proyecto"
        )

    topologia_existente = db.query(Topologia).filter(
        Topologia.proyecto_id == topologia.proyecto_id
    ).first()
    if topologia_existente:
        raise HTTPException(status_code=400, detail="El proyecto ya tiene una topología")

    nueva_topologia = Topologia(proyecto_id=topologia.proyecto_id)

    db.add(nueva_topologia)
    db.commit()
    db.refresh(nueva_topologia)

    return nueva_topologia


@router.get("/{topologia_id}", response_model=TopologiaResponse)
def obtener_topologia(
    topologia_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    topologia = db.query(Topologia).filter(Topologia.id == topologia_id).first()
    if not topologia:
        raise HTTPException(status_code=404, detail="Topología no encontrada")

    _verificar_acceso_topologia(topologia, usuario, db)

    return topologia


@router.delete("/{topologia_id}", response_model=TopologiaResponse)
def eliminar_topologia(
    topologia_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    topologia = db.query(Topologia).filter(Topologia.id == topologia_id).first()
    if not topologia:
        raise HTTPException(status_code=404, detail="Topología no encontrada")

    proyecto = db.query(Proyecto).filter(Proyecto.id == topologia.proyecto_id).first()
    if not proyecto or proyecto.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para eliminar esta topología"
        )

    db.delete(topologia)
    db.commit()

    return topologia


@router.get("/{topologia_id}/viabilidad", response_model=ViabilidadResponse)
def obtener_viabilidad(
    topologia_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    topologia = db.get(Topologia, topologia_id)
    if not topologia:
        raise HTTPException(status_code=404, detail="Topología no encontrada")
    _verificar_acceso_topologia(topologia, usuario, db)
    return evaluar_viabilidad(
        db.query(Componente).filter_by(topologia_id=topologia_id).all(),
        db.query(Conexion).filter_by(topologia_id=topologia_id).all(),
    )


@router.post("/{topologia_id}/viabilidad", response_model=ViabilidadResponse)
def previsualizar_viabilidad(
    topologia_id: int,
    datos: TopologiaPrevia,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    """Evalúa cambios del formulario sin guardar ni crear una simulación."""
    topologia = db.get(Topologia, topologia_id)
    if not topologia:
        raise HTTPException(status_code=404, detail="Topología no encontrada")
    _verificar_acceso_topologia(topologia, usuario, db)
    if any(c.topologia_id != topologia_id for c in [*datos.componentes, *datos.conexiones]):
        raise HTTPException(status_code=422, detail="Los elementos deben pertenecer a la topología indicada")
    return evaluar_viabilidad(datos.componentes, datos.conexiones)
