"""
app/inicializacion.py

Se ejecuta al iniciar el backend. Deja la base lista para usar en
entornos donde no hay consola (por ejemplo, el plan gratuito de Render):

1. Crea las tablas que falten (no borra ni modifica las existentes).
2. Aplica las migraciones aditivas para bases existentes.
3. Crea el usuario profesor a partir de variables de entorno, si están
   definidas y el email no está registrado.

Variables de entorno:
    PROFESOR_EMAIL      email del profesor (ej. profesor@frm.utn.edu.ar)
    PROFESOR_PASSWORD   contraseña inicial del profesor
    PROFESOR_NOMBRE     nombre a mostrar (opcional)

Todo es idempotente: ejecutarlo varias veces no duplica datos.
"""

import logging
import os

from app.database import Base, SessionLocal, engine
from app.models import models  # noqa: F401  (registra las entidades en Base)
from app.models.models import Usuario
from app.core.security import hash_password
from app.migraciones import migrar_cantidad_componentes, migrar_publicacion_proyectos

logger = logging.getLogger("uvicorn.error")

def inicializar_base() -> None:
    Base.metadata.create_all(bind=engine)
    migrar_cantidad_componentes(engine)
    migrar_publicacion_proyectos(engine)

    db = SessionLocal()
    try:
        email = os.environ.get("PROFESOR_EMAIL")
        password = os.environ.get("PROFESOR_PASSWORD")
        if email and password:
            if not db.query(Usuario).filter_by(email=email).first():
                db.add(Usuario(
                    nombre=os.environ.get("PROFESOR_NOMBRE", "Profesor"),
                    email=email,
                    password_hash=hash_password(password),
                    rol="profesor",
                ))
                logger.info("Usuario profesor creado: %s", email)
        else:
            logger.info("PROFESOR_EMAIL / PROFESOR_PASSWORD no definidas: no se crea el profesor.")

        db.commit()
    finally:
        db.close()
