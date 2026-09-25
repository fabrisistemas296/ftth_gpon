"""
app/core/deps.py

Dependencias reutilizables de FastAPI para:
- Extraer y validar el usuario autenticado a partir del JWT.
- Restringir endpoints según el rol del usuario (RNF-07).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decodificar_access_token
from app.models.models import Usuario

# El tokenUrl debe apuntar al endpoint de login que armen (ej. /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Extrae el usuario autenticado a partir del JWT enviado en el header
    Authorization: Bearer <token>.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decodificar_access_token(token)
        usuario_id = payload.get("sub")
        if usuario_id is None:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    usuario = db.query(Usuario).filter(Usuario.id == int(usuario_id)).first()
    if usuario is None:
        raise credenciales_invalidas

    return usuario


def requerir_rol_profesor(
    usuario: Usuario = Depends(get_usuario_actual),
) -> Usuario:
    """
    Dependencia para proteger endpoints exclusivos del rol Profesor
    (ej. ver proyectos de cualquier alumno).
    """
    if usuario.rol != "profesor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere rol de Profesor",
        )
    return usuario


def requerir_rol_alumno(
    usuario: Usuario = Depends(get_usuario_actual),
) -> Usuario:
    """
    Dependencia para proteger endpoints exclusivos del rol Alumno
    (ej. crear/editar/eliminar sus propios proyectos).
    """
    if usuario.rol != "alumno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere rol de Alumno",
        )
    return usuario