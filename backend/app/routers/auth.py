"""
app/routers/auth.py

Endpoint de login. Recibe email + password, valida contra el hash
almacenado (RNF-08) y devuelve un JWT (RNF-09).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Usuario
from app.core.security import verify_password, crear_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login estándar OAuth2 (form-data: username, password).
    Se usa el campo 'username' del formulario para recibir el email.
    """
    usuario = db.query(Usuario).filter(
        Usuario.email == form_data.username
    ).first()

    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not usuario:
        raise credenciales_invalidas

    if not verify_password(form_data.password, usuario.password_hash):
        raise credenciales_invalidas

    access_token = crear_access_token(usuario_id=usuario.id, rol=usuario.rol)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": usuario.rol,
    }