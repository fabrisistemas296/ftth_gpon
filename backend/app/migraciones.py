"""Migraciones de bases existentes que conservan sus registros y relaciones."""

import logging
import re
import sqlite3
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


logger = logging.getLogger(__name__)

_CHECK_TIPO = re.compile(
    r"(\bCHECK\s*\(\s*(?:tipo|\"tipo\"|`tipo`|\[tipo\])\s+IN\s*\(\s*)"
    r"('[^']*'(?:\s*,\s*'[^']*')*)(\s*\)\s*\))",
    re.IGNORECASE,
)


def _ampliar_tipos(sql: str) -> str:
    def ampliar(coincidencia):
        valores = coincidencia.group(2)
        if "LOTE_FIBRA_ONT" not in re.findall(r"'([^']*)'", valores):
            valores += ", 'LOTE_FIBRA_ONT'"
        return coincidencia.group(1) + valores + coincidencia.group(3)
    return _CHECK_TIPO.sub(ampliar, sql)


def migrar_tipos_componentes(motor: Engine) -> Path | None:
    """Amplía el CHECK antiguo de SQLite y conserva el resto del esquema.

    SQLite requiere reconstruir la tabla para cambiar un CHECK. Se hace en
    una transacción, sin activar cascadas durante el reemplazo, manteniendo
    IDs, columnas, índices, triggers, vistas y secuencias AUTOINCREMENT.
    Una base en archivo se respalda con la API de backup antes de modificarla.
    """
    if motor.dialect.name != "sqlite":
        return None
    respaldo = None
    with motor.connect() as conexion:
        sql = conexion.exec_driver_sql(
            "SELECT sql FROM sqlite_schema WHERE type='table' AND name='componente'"
        ).scalar_one_or_none()
        if not sql or _ampliar_tipos(sql) == sql:
            return None
        claves_foraneas = conexion.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
        archivos = conexion.exec_driver_sql("PRAGMA database_list").all()
        conexion.commit()
        archivo = next((fila[2] for fila in archivos if fila[1] == "main"), "")
        if archivo:
            ruta = Path(archivo)
            respaldo = ruta.with_name(f"{ruta.name}.pre-lote-{uuid4().hex}.sqlite3")
            with sqlite3.connect(respaldo) as destino:
                conexion.connection.driver_connection.backup(destino)

        # El PRAGMA debe cambiarse ANTES de iniciar la transacción; de lo
        # contrario DROP TABLE podría borrar conexiones por ON DELETE CASCADE.
        conexion.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conexion.commit()
        try:
            conexion.exec_driver_sql("BEGIN IMMEDIATE")
            sql = conexion.exec_driver_sql(
                "SELECT sql FROM sqlite_schema WHERE type='table' AND name='componente'"
            ).scalar_one()
            actualizado = _ampliar_tipos(sql)
            if actualizado == sql:
                conexion.commit()
                return None
            nuevo_sql, cambios = re.subn(
                r'^CREATE\s+TABLE\s+(?:"componente"|`componente`|\[componente\]|componente)(?=\s*\()',
                'CREATE TABLE "_componente_lote_migracion"', actualizado, count=1, flags=re.IGNORECASE,
            )
            if cambios != 1:
                raise RuntimeError("No se pudo identificar la tabla componente para migrar su restricción de tipos")
            quote = motor.dialect.identifier_preparer.quote
            columnas = ", ".join(quote(c[1]) for c in conexion.exec_driver_sql('PRAGMA table_info("componente")'))
            indices = conexion.exec_driver_sql(
                "SELECT sql FROM sqlite_schema WHERE type='index' AND tbl_name='componente' AND sql IS NOT NULL"
            ).scalars().all()
            # Al renombrar, SQLite también analiza las vistas y los triggers de
            # otras tablas. Se restauran con su SQL original en esta transacción.
            objetos = conexion.exec_driver_sql(
                "SELECT type, name, sql FROM sqlite_schema WHERE type IN ('trigger','view') AND sql IS NOT NULL"
            ).all()
            secuencia = None
            if re.search(r"\bAUTOINCREMENT\b", sql, re.IGNORECASE):
                secuencia = conexion.exec_driver_sql(
                    "SELECT seq FROM sqlite_sequence WHERE name='componente'"
                ).scalar_one_or_none()
            conexion.exec_driver_sql(nuevo_sql)
            conexion.exec_driver_sql(
                f'INSERT INTO "_componente_lote_migracion" ({columnas}) SELECT {columnas} FROM "componente"'
            )
            for tipo in ("trigger", "view"):
                for tipo_objeto, nombre, _ in objetos:
                    if tipo_objeto == tipo:
                        conexion.exec_driver_sql(f"DROP {tipo.upper()} {quote(nombre)}")
            conexion.exec_driver_sql('DROP TABLE "componente"')
            conexion.exec_driver_sql('ALTER TABLE "_componente_lote_migracion" RENAME TO "componente"')
            for sentencia in indices:
                conexion.exec_driver_sql(sentencia)
            for tipo in ("view", "trigger"):
                for tipo_objeto, _, sentencia in objetos:
                    if tipo_objeto == tipo:
                        conexion.exec_driver_sql(sentencia)
            if secuencia is not None:
                conexion.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name='componente'")
                conexion.exec_driver_sql("INSERT INTO sqlite_sequence (name, seq) VALUES ('componente', ?)", (secuencia,))
            if conexion.exec_driver_sql("PRAGMA foreign_key_check").first():
                raise RuntimeError("La migración encontró relaciones inválidas; se revierte sin modificar los datos")
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.exec_driver_sql(f"PRAGMA foreign_keys={int(claves_foraneas)}")
            conexion.commit()
    logger.info("Restricción de tipos actualizada para LOTE_FIBRA_ONT. Respaldo: %s", respaldo)
    return respaldo


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
