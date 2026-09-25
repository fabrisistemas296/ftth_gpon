"""
app/core/security.py

Módulo de seguridad del sistema.
Implementa RNF-08 (hasheo de contraseñas con bcrypt) y
RNF-09 (autenticación basada en JWT).



Contraseña profesor = admin
"""

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

# ------------------------------------------------------------------
# Configuración de hasheo de contraseñas (RNF-08)
# ------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera el hash seguro (bcrypt) de una contraseña en texto plano."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica que una contraseña en texto plano coincida con su hash."""
    return pwd_context.verify(password, password_hash)


# ------------------------------------------------------------------
# Configuración de JWT (RNF-09)
# ------------------------------------------------------------------
# SECRET_KEY se toma de la variable de entorno SECRET_KEY.
# El valor por defecto es SOLO para desarrollo local; en cualquier entorno
# compartido o repositorio público debe configurarse la variable de entorno
# real (ej. en un archivo .env NO versionado, o en la config del servidor).
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-only-secret-nunca-usar-en-produccion-cambiar-ya"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas


def crear_access_token(usuario_id: int, rol: str) -> str:
    """
    Genera un JWT que identifica al usuario autenticado y su rol.
    El rol viaja dentro del token para poder usarse en la autorización
    de cada endpoint (RNF-07), sin necesidad de volver a consultar la BD.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_access_token(token: str) -> dict:
    """
    Decodifica y valida un JWT. Lanza JWTError si el token es inválido
    o expiró.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise