"""Cambios aditivos para bases existentes; no se recrean ni borran tablas."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def migrar_cantidad_componentes(motor: Engine) -> None:
    with motor.begin() as conexion:
        if not inspect(conexion).has_table("componente"):
            return
        columnas = {c["name"] for c in inspect(conexion).get_columns("componente")}
        if "cantidad" not in columnas:
            conexion.execute(text("ALTER TABLE componente ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1"))


def migrar_publicacion_proyectos(motor: Engine) -> None:
    with motor.begin() as conexion:
        if not inspect(conexion).has_table("proyecto"):
            return
        columnas = {c["name"] for c in inspect(conexion).get_columns("proyecto")}
        if "publicado" not in columnas:
            conexion.execute(text("ALTER TABLE proyecto ADD COLUMN publicado BOOLEAN NOT NULL DEFAULT FALSE"))
