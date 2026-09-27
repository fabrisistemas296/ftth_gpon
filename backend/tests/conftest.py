"""
tests/conftest.py

Fixtures compartidas por toda la suite de tests.

Usa una base de datos SQLite separada (en memoria) para cada test,
completamente aislada de la base de datos real del proyecto
(ftth_gpon), así que correr los tests NUNCA toca tus datos reales.
"""

import sys
from pathlib import Path

# Agrega la raíz del proyecto (la carpeta que contiene 'app/') al
# path de Python, para que 'from app...' funcione sin importar desde
# qué carpeta se invoque pytest. No depende de pyproject.toml ni de
# ninguna configuración externa.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.models.models import EscenarioPredefinido, Usuario
from app.core.security import hash_password


# ------------------------------------------------------------------
# Motor de base de datos de TEST: SQLite en memoria, aislado del
# archivo real ftth_gpon usado en desarrollo.
# ------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _habilitar_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    """Crea el esquema limpio, precarga los escenarios y lo destruye al final del test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    session.add_all([
        EscenarioPredefinido(nombre="Barrio urbano", cantidad_usuarios_default=32, distancia_tipica_km=2.5),
        EscenarioPredefinido(nombre="Zona rural", cantidad_usuarios_default=8, distancia_tipica_km=12.0),
        EscenarioPredefinido(nombre="Campus universitario", cantidad_usuarios_default=64, distancia_tipica_km=1.0),
        EscenarioPredefinido(nombre="Operador FTTH", cantidad_usuarios_default=512, distancia_tipica_km=5.0),
    ])
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """Cliente HTTP de test, con get_db sobreescrito para usar la BD de test."""
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def alumno_headers(client):
    """Registra un alumno vía la API (flujo real) y devuelve sus headers autenticados."""
    client.post("/usuarios/", json={
        "nombre": "Alumno Test",
        "email": "alumno.test@ejemplo.com",
        "password": "test1234",
    })
    r = client.post(
        "/auth/login",
        data={"username": "alumno.test@ejemplo.com", "password": "test1234"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def otro_alumno_headers(client):
    """Un segundo alumno, para probar aislamiento entre dueños distintos."""
    client.post("/usuarios/", json={
        "nombre": "Otro Alumno",
        "email": "otro.alumno@ejemplo.com",
        "password": "test1234",
    })
    r = client.post(
        "/auth/login",
        data={"username": "otro.alumno@ejemplo.com", "password": "test1234"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def profesor_headers(client, db_session):
    """
    El rol profesor NO se crea vía API (por diseño): se inserta
    directamente en la base, igual que en producción.
    """
    profesor = Usuario(
        nombre="Profesor Test",
        email="profesor.test@ejemplo.com",
        password_hash=hash_password("test1234"),
        rol="profesor",
    )
    db_session.add(profesor)
    db_session.commit()

    r = client.post(
        "/auth/login",
        data={"username": "profesor.test@ejemplo.com", "password": "test1234"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def crear_topologia_valida(client, headers) -> dict:
    """
    Helper: arma el escenario completo validado en el punto 1.3
    (OLT + Fibra 8km + Splitter 1:32 + ONT), listo para calcular.
    Devuelve un dict con los ids relevantes.
    """
    r = client.post("/proyectos/", json={"nombre": "Proyecto de test"}, headers=headers)
    proyecto_id = r.json()["id"]

    r = client.post("/topologias/", json={"proyecto_id": proyecto_id}, headers=headers)
    topologia_id = r.json()["id"]

    r = client.post("/componentes/", json={
        "topologia_id": topologia_id, "tipo": "OLT",
        "posicion_x": 0, "posicion_y": 0,
        "potencia_tx_dbm": 5.0, "clase_potencia": "C+",
    }, headers=headers)
    olt_id = r.json()["id"]

    r = client.post("/componentes/", json={
        "topologia_id": topologia_id, "tipo": "FIBRA",
        "posicion_x": 0, "posicion_y": 0,
        "longitud_km": 8.0, "atenuacion_db_km": 0.28,
        "cantidad_conectores": 3, "cantidad_empalmes": 2,
    }, headers=headers)
    fibra_id = r.json()["id"]

    r = client.post("/componentes/", json={
        "topologia_id": topologia_id, "tipo": "SPLITTER",
        "posicion_x": 0, "posicion_y": 0,
        "relacion_division": "1:32",
    }, headers=headers)
    splitter_id = r.json()["id"]

    r = client.post("/componentes/", json={
        "topologia_id": topologia_id, "tipo": "ONT_ONU",
        "posicion_x": 0, "posicion_y": 0,
        "sensibilidad_min_dbm": -32.0, "potencia_sobrecarga_dbm": -8.0,
    }, headers=headers)
    ont_id = r.json()["id"]

    for origen, destino in [(olt_id, fibra_id), (fibra_id, splitter_id), (splitter_id, ont_id)]:
        client.post("/conexiones/", json={
            "topologia_id": topologia_id,
            "componente_origen_id": origen,
            "componente_destino_id": destino,
        }, headers=headers)

    return {
        "proyecto_id": proyecto_id,
        "topologia_id": topologia_id,
        "olt_id": olt_id,
        "fibra_id": fibra_id,
        "splitter_id": splitter_id,
        "ont_id": ont_id,
    }