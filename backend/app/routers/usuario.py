from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import hash_password
from app.core.deps import get_usuario_actual, requerir_rol_profesor
from app.models.models import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioResponse


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)


@router.get("/", response_model=list[UsuarioResponse])
def obtener_usuarios(
    db: Session = Depends(get_db),
    _profesor: Usuario = Depends(requerir_rol_profesor),  # solo profesores listan usuarios
):
    usuarios = db.query(Usuario).all()
    return usuarios


@router.post("/", response_model=UsuarioResponse)
def crear_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db)
):
    # Evitar registros duplicados por email
    existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    nuevo_usuario = Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        password_hash=hash_password(usuario.password),  # <- hasheada, no texto plano
        rol="alumno",  # <- forzado en el servidor, nunca viene del cliente (RF-01)
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return nuevo_usuario


@router.get("/me", response_model=UsuarioResponse)
def obtener_usuario_actual(
    usuario: Usuario = Depends(get_usuario_actual),
):
    """Devuelve los datos del usuario autenticado según su token."""
    return usuario


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _profesor: Usuario = Depends(requerir_rol_profesor),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.delete("/{usuario_id}", response_model=UsuarioResponse)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _profesor: Usuario = Depends(requerir_rol_profesor),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(usuario)
    db.commit()

    return usuario