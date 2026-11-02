import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.models.models import Componente, Conexion, Proyecto, Simulacion, Topologia, Usuario
from tests.conftest import crear_topologia_valida


def test_inicio_no_precarga_escenarios_antiguos(monkeypatch):
    from app import inicializacion
    from app.models.models import EscenarioPredefinido
    motor = create_engine("sqlite:///:memory:")
    sesiones = sessionmaker(bind=motor)
    monkeypatch.setattr(inicializacion, "engine", motor)
    monkeypatch.setattr(inicializacion, "SessionLocal", sesiones)
    monkeypatch.delenv("PROFESOR_EMAIL", raising=False)
    monkeypatch.delenv("PROFESOR_PASSWORD", raising=False)
    inicializacion.inicializar_base()
    inicializacion.inicializar_base()
    with sesiones() as db:
        assert db.query(EscenarioPredefinido).count() == 0
    motor.dispose()


def publicar(client, headers, proyecto_id, valor=True):
    return client.put(f'/proyectos/{proyecto_id}/publicacion', json={"publicado": valor}, headers=headers)


@pytest.fixture()
def proyecto_profesor(client, profesor_headers):
    ids = crear_topologia_valida(client, profesor_headers)
    r = client.post('/componentes/', json=dict(
        topologia_id=ids["topologia_id"], tipo="LOTE_FIBRA_ONT", cantidad=8,
        posicion_x=400, posicion_y=200, longitud_km=2, atenuacion_db_km=0.28,
        cantidad_conectores=2, cantidad_empalmes=1, sensibilidad_min_dbm=-28,
        potencia_sobrecarga_dbm=-8,
    ), headers=profesor_headers)
    assert r.status_code == 200
    ids["lote_id"] = r.json()["id"]
    r = client.post('/conexiones/', json=dict(topologia_id=ids["topologia_id"],
                    componente_origen_id=ids["splitter_id"], componente_destino_id=ids["lote_id"]), headers=profesor_headers)
    assert r.status_code == 200
    ids["conexion_id"] = r.json()["id"]
    return ids


@pytest.fixture()
def otro_profesor_headers(client, db_session):
    db_session.add(Usuario(nombre="Otro profesor", email="otro.profesor@ejemplo.com",
                           password_hash=hash_password("test1234"), rol="profesor"))
    db_session.commit()
    token = client.post('/auth/login', data={"username": "otro.profesor@ejemplo.com", "password": "test1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def detalle(client, headers, id):
    r = client.get(f'/proyectos/{id}/detalle', headers=headers)
    assert r.status_code == 200
    return r.json()


def simular(client, headers, id):
    r = client.post('/simulaciones/', json={"proyecto_id": id, "cantidad_usuarios": 9, "tipo_consumo": "streaming"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["escenario_id"] is None
    sim = r.json()["id"]
    r = client.post(f'/simulaciones/{sim}/calcular', headers=headers)
    assert r.status_code == 200
    return sim, r.json()


def test_profesor_edita_simula_y_elimina_su_propio_proyecto(client, profesor_headers, proyecto_profesor):
    ids = proyecto_profesor
    r = client.put(f'/proyectos/{ids["proyecto_id"]}', json={"nombre": "Ejercicio del profesor"}, headers=profesor_headers)
    assert r.status_code == 200
    simular(client, profesor_headers, ids["proyecto_id"])
    assert client.delete(f'/conexiones/{ids["conexion_id"]}', headers=profesor_headers).status_code == 200
    assert client.delete(f'/componentes/{ids["lote_id"]}', headers=profesor_headers).status_code == 200
    assert client.delete(f'/topologias/{ids["topologia_id"]}', headers=profesor_headers).status_code == 200
    assert client.delete(f'/proyectos/{ids["proyecto_id"]}', headers=profesor_headers).status_code == 200


def test_publicacion_es_explicita_y_lista_solo_proyectos_publicados(client, profesor_headers, alumno_headers, proyecto_profesor):
    id = proyecto_profesor["proyecto_id"]
    assert client.get('/proyectos/publicados', headers=alumno_headers).json() == []
    assert publicar(client, profesor_headers, id).json()["publicado"] is True
    lista = client.get('/proyectos/publicados', headers=alumno_headers).json()
    assert len(lista) == 1 and lista[0]["id"] == id
    assert lista[0]["autor"] == "Profesor Test"
    assert "email" not in lista[0]
    assert client.get('/proyectos/publicados').status_code == 401
    assert client.get(f'/proyectos/{id}/detalle', headers=alumno_headers).status_code == 403


def test_copia_profunda_conserva_parametros_lotes_y_conexiones_sin_historial(client, profesor_headers, alumno_headers, proyecto_profesor):
    ids = proyecto_profesor
    _, calculo_original = simular(client, profesor_headers, ids["proyecto_id"])
    assert publicar(client, profesor_headers, ids["proyecto_id"]).status_code == 200
    r = client.post(f'/proyectos/{ids["proyecto_id"]}/copiar', headers=alumno_headers)
    assert r.status_code == 200
    copia = r.json()
    origen = detalle(client, profesor_headers, ids["proyecto_id"])
    duplicado = detalle(client, alumno_headers, copia["id"])
    assert copia["id"] != origen["id"]
    assert copia["usuario_id"] != origen["usuario_id"]
    assert copia["publicado"] is False
    assert duplicado["simulaciones"] == []
    t, tc = origen["topologia"], duplicado["topologia"]
    assert tc["id"] != t["id"]
    assert len(tc["componentes"]) == len(t["componentes"]) == 5
    assert not ({c["id"] for c in t["componentes"]} & {c["id"] for c in tc["componentes"]})
    por_tipo = {c["tipo"]: c for c in t["componentes"]}
    for c in tc["componentes"]:
        assert {k: v for k, v in c.items() if k not in {"id", "topologia_id"}} == {
            k: v for k, v in por_tipo[c["tipo"]].items() if k not in {"id", "topologia_id"}}
    tipos = {c["id"]: c["tipo"] for c in t["componentes"]}
    tipos_copia = {c["id"]: c["tipo"] for c in tc["componentes"]}
    assert {(tipos[c["componente_origen_id"]], tipos[c["componente_destino_id"]]) for c in t["conexiones"]} == {
        (tipos_copia[c["componente_origen_id"]], tipos_copia[c["componente_destino_id"]]) for c in tc["conexiones"]}
    assert all(c["topologia_id"] == tc["id"] for c in tc["conexiones"])
    _, calculo_copia = simular(client, alumno_headers, copia["id"])
    assert calculo_original["resultado_optico"]["perdida_total_db"] == calculo_copia["resultado_optico"]["perdida_total_db"]
    assert copia["id"] in {p["id"] for p in client.get('/proyectos/', headers=alumno_headers).json()}


def test_copias_son_independientes_de_edicion_retiro_y_borrado_del_original(client, profesor_headers, alumno_headers, proyecto_profesor):
    id = proyecto_profesor["proyecto_id"]
    publicar(client, profesor_headers, id)
    copia = client.post(f'/proyectos/{id}/copiar', headers=alumno_headers).json()
    lote = next(c for c in detalle(client, alumno_headers, copia["id"])["topologia"]["componentes"] if c["tipo"] == "LOTE_FIBRA_ONT")
    lote_id = lote.pop("id")
    lote["cantidad"] = 12
    assert client.put(f'/componentes/{lote_id}', json=lote, headers=alumno_headers).status_code == 200
    assert next(c for c in detalle(client, profesor_headers, id)["topologia"]["componentes"] if c["tipo"] == "LOTE_FIBRA_ONT")["cantidad"] == 8
    assert publicar(client, profesor_headers, id, False).status_code == 200
    assert client.get('/proyectos/publicados', headers=alumno_headers).json() == []
    assert client.post(f'/proyectos/{id}/copiar', headers=alumno_headers).status_code == 404
    assert client.delete(f'/proyectos/{id}', headers=profesor_headers).status_code == 200
    assert next(c for c in detalle(client, alumno_headers, copia["id"])["topologia"]["componentes"] if c["id"] == lote_id)["cantidad"] == 12
    simular(client, alumno_headers, copia["id"])


def test_solo_el_profesor_dueno_puede_publicar(client, profesor_headers, otro_profesor_headers, alumno_headers, proyecto_profesor):
    id = proyecto_profesor["proyecto_id"]
    assert publicar(client, alumno_headers, id).status_code == 403
    assert publicar(client, otro_profesor_headers, id).status_code == 403
    alumno_id = client.post('/proyectos/', json={"nombre": "Trabajo de alumno"}, headers=alumno_headers).json()["id"]
    assert publicar(client, profesor_headers, alumno_id).status_code == 403
    assert client.post(f'/proyectos/{id}/copiar', headers=profesor_headers).status_code == 403
    assert publicar(client, profesor_headers, 999999).status_code == 404


def test_no_se_copian_borradores_ni_proyectos_de_alumnos(client, profesor_headers, alumno_headers, proyecto_profesor):
    id = proyecto_profesor["proyecto_id"]
    assert client.post(f'/proyectos/{id}/copiar', headers=alumno_headers).status_code == 404
    assert client.post('/proyectos/999999/copiar', headers=alumno_headers).status_code == 404
    assert client.post(f'/proyectos/{id}/copiar').status_code == 401
    r = client.post('/proyectos/', json={"nombre": "Mi proyecto", "publicado": True}, headers=alumno_headers)
    assert r.json()["publicado"] is False
    assert client.post(f'/proyectos/{r.json()["id"]}/copiar', headers=alumno_headers).status_code == 404


def test_profesor_distingue_mis_proyectos_de_proyectos_de_alumnos(client, profesor_headers, alumno_headers, proyecto_profesor):
    estudiante = client.post('/proyectos/', json={"nombre": "Trabajo del alumno"}, headers=alumno_headers).json()["id"]
    propios = client.get('/proyectos/?propios=true', headers=profesor_headers).json()
    revision = client.get('/proyectos/', headers=profesor_headers).json()
    assert [p["id"] for p in propios] == [proyecto_profesor["proyecto_id"]]
    assert [p["id"] for p in revision] == [estudiante]


@pytest.mark.parametrize("dueno", ["profesor", "alumno"])
def test_escritura_de_toda_la_red_restringida_al_dueno(client, profesor_headers, alumno_headers, dueno):
    propio, ajeno = (profesor_headers, alumno_headers) if dueno == "profesor" else (alumno_headers, profesor_headers)
    ids = crear_topologia_valida(client, propio)
    sim_id, _ = simular(client, propio, ids["proyecto_id"])
    top = detalle(client, propio, ids["proyecto_id"])["topologia"]
    c = next(c for c in top["componentes"] if c["id"] == ids["fibra_id"])
    c.pop("id")
    con = top["conexiones"][0]
    con_id = con.pop("id")
    pedidos = [
        ("put", f'/proyectos/{ids["proyecto_id"]}', {"nombre": "Ajeno"}),
        ("delete", f'/proyectos/{ids["proyecto_id"]}', None),
        ("post", '/topologias/', {"proyecto_id": ids["proyecto_id"]}),
        ("delete", f'/topologias/{ids["topologia_id"]}', None),
        ("post", '/componentes/', c),
        ("put", f'/componentes/{ids["fibra_id"]}', c),
        ("delete", f'/componentes/{ids["fibra_id"]}', None),
        ("post", '/conexiones/', con),
        ("put", f'/conexiones/{con_id}', con),
        ("delete", f'/conexiones/{con_id}', None),
        ("post", '/simulaciones/', {"proyecto_id": ids["proyecto_id"], "cantidad_usuarios": 9, "tipo_consumo": "web"}),
        ("post", f'/simulaciones/{sim_id}/calcular', None),
    ]
    for metodo, ruta, cuerpo in pedidos:
        r = client.request(metodo.upper(), ruta, json=cuerpo, headers=ajeno)
        assert r.status_code == 403, (ruta, r.text)


def test_copia_inconsistente_se_revierte_completamente(client, profesor_headers, alumno_headers, proyecto_profesor, db_session):
    ids = proyecto_profesor
    otro = crear_topologia_valida(client, alumno_headers)
    db_session.add(Conexion(topologia_id=ids["topologia_id"], componente_origen_id=ids["olt_id"],
                            componente_destino_id=otro["ont_id"]))
    db_session.commit()
    publicar(client, profesor_headers, ids["proyecto_id"])
    antes = [db_session.query(m).count() for m in (Proyecto, Topologia, Componente, Conexion, Simulacion)]
    r = client.post(f'/proyectos/{ids["proyecto_id"]}/copiar', headers=alumno_headers)
    assert r.status_code == 409
    assert [db_session.query(m).count() for m in (Proyecto, Topologia, Componente, Conexion, Simulacion)] == antes


def test_se_puede_publicar_y_copiar_un_ejercicio_incompleto(client, profesor_headers, alumno_headers):
    id = client.post('/proyectos/', json={"nombre": "Construir desde cero"}, headers=profesor_headers).json()["id"]
    publicar(client, profesor_headers, id)
    r = client.post(f'/proyectos/{id}/copiar', headers=alumno_headers)
    assert r.status_code == 200
    t = detalle(client, alumno_headers, r.json()["id"])["topologia"]
    assert t is not None and t["componentes"] == [] and t["conexiones"] == []
