import sqlite3

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.migraciones import migrar_cantidad_componentes, migrar_tipos_componentes
from tests.conftest import crear_topologia_valida


# Esquema anterior real: además del tipo restringe clase de potencia y división.
SQL_ANTIGUO = """
CREATE TABLE componente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topologia_id INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('OLT', 'FIBRA', 'SPLITTER', 'ONT_ONU')),
    posicion_x REAL NOT NULL,
    posicion_y REAL NOT NULL,
    potencia_tx_dbm REAL,
    clase_potencia TEXT CHECK (clase_potencia IN ('B+', 'C+') OR clase_potencia IS NULL),
    longitud_km REAL,
    atenuacion_db_km REAL,
    cantidad_conectores INTEGER,
    cantidad_empalmes INTEGER,
    relacion_division TEXT CHECK (relacion_division IN ('1:2','1:4','1:8','1:16','1:32','1:64') OR relacion_division IS NULL),
    sensibilidad_min_dbm REAL,
    potencia_sobrecarga_dbm REAL,
    FOREIGN KEY (topologia_id) REFERENCES topologia(id) ON DELETE CASCADE
)
"""


def _tabla_antigua(motor, cantidad=True):
    Base.metadata.create_all(motor)
    with motor.begin() as c:
        c.exec_driver_sql("DROP TABLE componente")
        c.exec_driver_sql(SQL_ANTIGUO)
        c.exec_driver_sql("CREATE INDEX idx_componente_topologia ON componente(topologia_id)")
    if cantidad:
        migrar_cantidad_componentes(motor)


def _datos_anteriores(motor):
    with motor.begin() as c:
        c.exec_driver_sql("INSERT INTO usuario(id,nombre,email,password_hash,rol) VALUES (1,'Alumno','alumno@example.test','hash','alumno')")
        c.exec_driver_sql("INSERT INTO proyecto(id,nombre,usuario_id) VALUES (11,'Proyecto anterior',1)")
        c.exec_driver_sql("INSERT INTO topologia(id,proyecto_id) VALUES (19,11)")
        c.exec_driver_sql("INSERT INTO componente(id,topologia_id,tipo,posicion_x,posicion_y,potencia_tx_dbm,clase_potencia) VALUES (41,19,'OLT',10,20,5,'C+')")
        c.exec_driver_sql("INSERT INTO componente(id,topologia_id,tipo,posicion_x,posicion_y,longitud_km,atenuacion_db_km) VALUES (42,19,'FIBRA',30,40,8,0.28)")
        c.exec_driver_sql("INSERT INTO componente(id,topologia_id,tipo,posicion_x,posicion_y,relacion_division) VALUES (43,19,'SPLITTER',50,60,'1:32')")
        c.exec_driver_sql("INSERT INTO componente(id,topologia_id,tipo,posicion_x,posicion_y,sensibilidad_min_dbm,potencia_sobrecarga_dbm) VALUES (44,19,'ONT_ONU',70,80,-32,-8)")
        for id, origen, destino in [(51, 41, 42), (52, 42, 43), (53, 43, 44)]:
            c.exec_driver_sql("INSERT INTO conexion(id,topologia_id,componente_origen_id,componente_destino_id) VALUES (?,19,?,?)", (id, origen, destino))
        c.exec_driver_sql("INSERT INTO componente(id,topologia_id,tipo,posicion_x,posicion_y) VALUES (99,19,'FIBRA',0,0)")
        c.exec_driver_sql("DELETE FROM componente WHERE id=99")
        c.exec_driver_sql("CREATE TABLE auditoria (valor TEXT)")
        c.exec_driver_sql("CREATE TRIGGER registrar_componente AFTER INSERT ON componente BEGIN INSERT INTO auditoria VALUES (NEW.tipo); END")
        c.exec_driver_sql("CREATE VIEW vista_componentes AS SELECT id, tipo FROM componente")
        c.exec_driver_sql("CREATE VIEW vista_terminales AS SELECT id FROM vista_componentes WHERE tipo='ONT_ONU'")


@pytest.fixture()
def base_antigua():
    motor = create_engine("sqlite:///:memory:")
    @event.listens_for(motor, "connect")
    def activar_fk(dbapi, _):
        dbapi.execute("PRAGMA foreign_keys=ON")
    _tabla_antigua(motor)
    _datos_anteriores(motor)
    yield motor
    motor.dispose()


def _fotografia(motor):
    with motor.connect() as c:
        return {t: c.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY id').all()
                for t in ("usuario", "proyecto", "topologia", "componente", "conexion")}


def test_migracion_conserva_datos_relaciones_indices_triggers_vistas_y_secuencia(base_antigua):
    motor = base_antigua
    antes = _fotografia(motor)
    migrar_tipos_componentes(motor)
    assert _fotografia(motor) == antes
    with motor.begin() as c:
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert c.exec_driver_sql("SELECT id FROM vista_terminales").all() == [(44,)]
        assert c.exec_driver_sql("SELECT count(*) FROM auditoria").scalar_one() == 0
        assert c.exec_driver_sql("SELECT count(*) FROM sqlite_schema WHERE name='idx_componente_topologia'").scalar_one() == 1
        c.exec_driver_sql("INSERT INTO componente(topologia_id,tipo,cantidad,posicion_x,posicion_y,longitud_km,atenuacion_db_km,sensibilidad_min_dbm,potencia_sobrecarga_dbm) VALUES (19,'LOTE_FIBRA_ONT',8,90,100,1,0.28,-28,-8)")
        assert c.exec_driver_sql("SELECT id FROM componente WHERE tipo='LOTE_FIBRA_ONT'").scalar_one() == 100
        assert c.exec_driver_sql("SELECT valor FROM auditoria").all() == [("LOTE_FIBRA_ONT",)]
        c.exec_driver_sql("DELETE FROM topologia WHERE id=19")
        assert c.exec_driver_sql("SELECT count(*) FROM componente").scalar_one() == 0
        assert c.exec_driver_sql("SELECT count(*) FROM conexion").scalar_one() == 0


@pytest.mark.parametrize("campo,valor", [("tipo", "TIPO_INVALIDO"), ("clase_potencia", "Z+"), ("relacion_division", "1:999")])
def test_ampliar_tipos_no_elimina_otras_restricciones(base_antigua, campo, valor):
    migrar_tipos_componentes(base_antigua)
    with pytest.raises(IntegrityError):
        with base_antigua.begin() as c:
            c.execute(text(f"UPDATE componente SET {campo}=:valor WHERE id=41"), {"valor": valor})


def test_migracion_se_puede_repetir_y_no_recrea_una_base_actualizada(base_antigua):
    migrar_tipos_componentes(base_antigua)
    antes = _fotografia(base_antigua)
    with base_antigua.connect() as c:
        version = c.exec_driver_sql("PRAGMA schema_version").scalar_one()
    assert migrar_tipos_componentes(base_antigua) is None
    with base_antigua.connect() as c:
        assert c.exec_driver_sql("PRAGMA schema_version").scalar_one() == version
    assert _fotografia(base_antigua) == antes


def test_fallo_durante_reemplazo_revierte_tabla_conexiones_y_restauracion_fk(base_antigua):
    antes = _fotografia(base_antigua)
    def fallar(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('ALTER TABLE "_componente_lote_migracion"'):
            raise RuntimeError("Fallo simulado después del reemplazo")
    event.listen(base_antigua, "before_cursor_execute", fallar)
    try:
        with pytest.raises(RuntimeError, match="Fallo simulado"):
            migrar_tipos_componentes(base_antigua)
    finally:
        event.remove(base_antigua, "before_cursor_execute", fallar)
    assert _fotografia(base_antigua) == antes
    with base_antigua.connect() as c:
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert c.exec_driver_sql("SELECT id FROM vista_terminales").all() == [(44,)]
        assert c.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name='componente'").scalar_one() == 99
        assert c.exec_driver_sql("SELECT count(*) FROM sqlite_schema WHERE name='_componente_lote_migracion'").scalar_one() == 0


def test_base_en_archivo_se_respalda_antes_de_cambiar_restricciones(tmp_path):
    ruta = tmp_path / "red.sqlite3"
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    _tabla_antigua(motor)
    _datos_anteriores(motor)
    antes = _fotografia(motor)
    respaldo = migrar_tipos_componentes(motor)
    assert respaldo is not None and respaldo.exists()
    with sqlite3.connect(respaldo) as c:
        assert "LOTE_FIBRA_ONT" not in c.execute("SELECT sql FROM sqlite_schema WHERE name='componente'").fetchone()[0]
        assert c.execute("SELECT count(*) FROM componente").fetchone()[0] == 4
        assert c.execute("SELECT count(*) FROM conexion").fetchone()[0] == 3
    assert _fotografia(motor) == antes
    with motor.connect() as c:
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 0
    assert migrar_tipos_componentes(motor) is None
    assert len(list(tmp_path.glob("red.sqlite3.pre-lote-*.sqlite3"))) == 1
    motor.dispose()


@pytest.mark.parametrize("cantidad_existente", [False, True])
def test_arranque_actualiza_el_check_y_conserva_las_bases_anteriores(monkeypatch, cantidad_existente):
    from app import inicializacion
    motor = create_engine("sqlite:///:memory:")
    _tabla_antigua(motor, cantidad=cantidad_existente)
    _datos_anteriores(motor)
    monkeypatch.setattr(inicializacion, "engine", motor)
    monkeypatch.setattr(inicializacion, "SessionLocal", sessionmaker(bind=motor))
    monkeypatch.delenv("PROFESOR_EMAIL", raising=False)
    monkeypatch.delenv("PROFESOR_PASSWORD", raising=False)
    inicializacion.inicializar_base()
    inicializacion.inicializar_base()
    with motor.connect() as c:
        sql = c.exec_driver_sql("SELECT sql FROM sqlite_schema WHERE name='componente'").scalar_one()
        assert "LOTE_FIBRA_ONT" in sql
        assert c.exec_driver_sql("SELECT cantidad FROM componente ORDER BY id").all() == [(1,), (1,), (1,), (1,)]
        assert c.exec_driver_sql("SELECT count(*) FROM conexion").scalar_one() == 3
        assert c.exec_driver_sql("SELECT count(*) FROM proyecto").scalar_one() == 1
    motor.dispose()


def test_api_crea_lote_sobre_esquema_antiguo_despues_de_migrar(client, alumno_headers, db_session):
    _tabla_antigua(db_session.get_bind())
    ids = crear_topologia_valida(client, alumno_headers)
    db_session.rollback()
    migrar_tipos_componentes(db_session.get_bind())
    r = client.post('/componentes/', json=dict(
        topologia_id=ids["topologia_id"], tipo="LOTE_FIBRA_ONT", cantidad=8,
        posicion_x=70, posicion_y=292, longitud_km=1, atenuacion_db_km=0.28,
        cantidad_conectores=2, cantidad_empalmes=0, sensibilidad_min_dbm=-28,
        potencia_sobrecarga_dbm=-8,
    ), headers=alumno_headers)
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "LOTE_FIBRA_ONT"
    assert r.json()["cantidad"] == 8


def test_migracion_omite_bases_vacias_y_actualizadas():
    motor = create_engine("sqlite:///:memory:")
    assert migrar_tipos_componentes(motor) is None
    Base.metadata.create_all(motor)
    assert migrar_tipos_componentes(motor) is None
    motor.dispose()
