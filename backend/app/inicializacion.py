"""
app/inicializacion.py

Se ejecuta al iniciar el backend. Deja la base lista para usar en
entornos donde no hay consola (por ejemplo, el plan gratuito de Render):

1. Crea las tablas que falten (no borra ni modifica las existentes).
2. Carga los escenarios predefinidos si todavía no existen.
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
from app.models.models import EscenarioPredefinido, Usuario
from app.core.security import hash_password

logger = logging.getLogger("uvicorn.error")

# Valores ilustrativos: ajustarlos con los tutores (también se pueden
# editar después desde la aplicación, con el usuario profesor).
ESCENARIOS = [
    ("Barrio urbano", 150, 2.0, "Zona residencial densa con distancias cortas a la central."),
    ("Zona rural", 40, 15.0, "Baja densidad de usuarios y tramos troncales largos."),
    ("Campus universitario", 300, 1.0, "Alta densidad de usuarios en edificios cercanos."),
    ("Operador FTTH", 64, 5.0, "Despliegue típico de un operador con splitters 1:64."),
]


def inicializar_base() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for nombre, usuarios, distancia, descripcion in ESCENARIOS:
            if not db.query(EscenarioPredefinido).filter_by(nombre=nombre).first():
                db.add(EscenarioPredefinido(
                    nombre=nombre,
                    cantidad_usuarios_default=usuarios,
                    distancia_tipica_km=distancia,
                    descripcion=descripcion,
                ))
                logger.info("Escenario creado: %s", nombre)

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
