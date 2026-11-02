from sqlalchemy import create_engine, inspect, text

from app.migraciones import migrar_cantidad_componentes, migrar_publicacion_proyectos


def test_migracion_agrega_cantidad_sin_perder_datos_y_es_idempotente():
    motor = create_engine("sqlite:///:memory:")
    with motor.begin() as conexion:
        conexion.execute(text("CREATE TABLE componente (id INTEGER PRIMARY KEY, tipo TEXT NOT NULL)"))
        conexion.execute(text("INSERT INTO componente (id, tipo) VALUES (1, 'FIBRA'), (2, 'ONT_ONU')"))

    migrar_cantidad_componentes(motor)
    migrar_cantidad_componentes(motor)

    with motor.connect() as conexion:
        assert conexion.execute(text("SELECT id, tipo, cantidad FROM componente ORDER BY id")).all() == [
            (1, "FIBRA", 1), (2, "ONT_ONU", 1),
        ]
        conexion.execute(text("INSERT INTO componente (id, tipo) VALUES (3, 'OLT')"))
        assert conexion.execute(text("SELECT cantidad FROM componente WHERE id = 3")).scalar_one() == 1
    motor.dispose()


def test_migracion_no_requiere_una_tabla_preexistente():
    motor = create_engine("sqlite:///:memory:")
    migrar_cantidad_componentes(motor)
    assert inspect(motor).get_table_names() == []
    motor.dispose()


def test_proyectos_anteriores_se_conservan_sin_publicarse_automaticamente():
    motor = create_engine("sqlite:///:memory:")
    with motor.begin() as conexion:
        conexion.execute(text("CREATE TABLE proyecto (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL)"))
        conexion.execute(text("INSERT INTO proyecto (id, nombre) VALUES (1, 'Proyecto previo')"))
    migrar_publicacion_proyectos(motor)
    migrar_publicacion_proyectos(motor)
    with motor.connect() as conexion:
        assert conexion.execute(text("SELECT id, nombre, publicado FROM proyecto")).all() == [(1, "Proyecto previo", 0)]
    motor.dispose()
