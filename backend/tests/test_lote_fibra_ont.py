from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.models import Componente, Conexion, ResultadoOptico, ResultadoTrafico
from app.schemas.componente import ComponenteCreate
from app.services.calculo_optico import TopologiaInvalidaError, calcular_enlaces
from app.services.viabilidad import evaluar_viabilidad
from tests.conftest import crear_topologia_valida


def datos_lote(topologia_id=1, cantidad=8):
    return dict(topologia_id=topologia_id, tipo="LOTE_FIBRA_ONT", cantidad=cantidad,
                posicion_x=0, posicion_y=0, longitud_km=2, atenuacion_db_km=0.28,
                cantidad_conectores=2, cantidad_empalmes=1,
                sensibilidad_min_dbm=-28, potencia_sobrecarga_dbm=-8)


def nodo(id, tipo, **datos):
    base = dict(id=id, tipo=tipo, cantidad=1, potencia_tx_dbm=5, clase_potencia="C+",
                longitud_km=5, atenuacion_db_km=0.28, cantidad_conectores=2,
                cantidad_empalmes=1, relacion_division="1:8",
                sensibilidad_min_dbm=-28, potencia_sobrecarga_dbm=-8)
    return SimpleNamespace(**(base | datos))


def conexion(a, b):
    return SimpleNamespace(componente_origen_id=a, componente_destino_id=b)


def red_lote(cantidad=8):
    return ([nodo(1, "OLT"), nodo(2, "FIBRA"), nodo(3, "SPLITTER"),
             nodo(4, "LOTE_FIBRA_ONT", cantidad=cantidad, longitud_km=2)],
            [conexion(1, 2), conexion(2, 3), conexion(3, 4)])


def test_lote_tiene_parametros_de_fibra_y_ont_y_cantidad_unica():
    lote = ComponenteCreate(**datos_lote())
    assert lote.cantidad == 8
    assert lote.longitud_km == 2
    assert lote.sensibilidad_min_dbm == -28


@pytest.mark.parametrize("campo", ["longitud_km", "atenuacion_db_km", "sensibilidad_min_dbm", "potencia_sobrecarga_dbm"])
def test_lote_exige_ambos_conjuntos_de_parametros(campo):
    datos = datos_lote()
    datos.pop(campo)
    with pytest.raises(ValidationError):
        ComponenteCreate(**datos)


@pytest.mark.parametrize("cantidad", [0, -1, 1.5, True, "8", None, 2147483648])
def test_cantidad_debe_ser_entera_positiva(cantidad):
    with pytest.raises(ValidationError):
        ComponenteCreate(**datos_lote(cantidad=cantidad))


@pytest.mark.parametrize("tipo,datos", [
    ("FIBRA", {"longitud_km": 1, "atenuacion_db_km": 0.28}),
    ("ONT_ONU", {"sensibilidad_min_dbm": -28, "potencia_sobrecarga_dbm": -8}),
])
def test_componentes_individuales_no_pueden_ocultar_cantidades(tipo, datos):
    with pytest.raises(ValidationError):
        ComponenteCreate(topologia_id=1, tipo=tipo, cantidad=8, posicion_x=0, posicion_y=0, **datos)


def test_lote_es_equivalente_a_ocho_pares_individuales_en_paralelo():
    componentes, conexiones = red_lote()
    lote = calcular_enlaces(componentes, conexiones)[0]
    individuales, aristas = componentes[:3], conexiones[:2]
    for i in range(8):
        fibra_id = 10 + i * 2
        individuales.extend([nodo(fibra_id, "FIBRA", longitud_km=2), nodo(fibra_id + 1, "ONT_ONU")])
        aristas.extend([conexion(3, fibra_id), conexion(fibra_id, fibra_id + 1)])
    resultados = calcular_enlaces(individuales, aristas)
    assert lote.cantidad_onts == 8
    assert lote.longitud_total_km == 7
    assert lote.perdida_total_db == pytest.approx(14.26)
    for r in resultados:
        assert r.longitud_total_km == lote.longitud_total_km
        assert r.perdida_total_db == lote.perdida_total_db
        assert r.potencia_recibida_dbm == lote.potencia_recibida_dbm
        assert r.estado_operativo == lote.estado_operativo == "operativo"


@pytest.mark.parametrize("cantidad", [1, 8])
def test_cantidad_no_multiplica_distancia_ni_atenuacion(cantidad):
    r = calcular_enlaces(*red_lote(cantidad))[0]
    assert r.longitud_total_km == 7
    assert r.perdida_total_db == pytest.approx(14.26)


def test_lote_no_puede_eludir_la_capacidad_del_splitter():
    with pytest.raises(TopologiaInvalidaError, match="9 salidas"):
        calcular_enlaces(*red_lote(9))


@pytest.mark.parametrize("longitud,estado", [(8, "viable"), (8.001, "no_viable")])
def test_fibra_incorporada_al_lote_cuenta_para_el_limite_de_20km(longitud, estado):
    componentes, conexiones = red_lote()
    componentes[1].longitud_km = 12
    componentes[3].longitud_km = longitud
    r = evaluar_viabilidad(componentes, conexiones)
    assert r.estado == estado
    assert r.cantidad_onts == 8
    assert r.enlaces[0].longitud_total_km == pytest.approx(12 + longitud)


def test_lote_no_admite_ont_adicionales_como_transito():
    componentes, conexiones = red_lote()
    componentes.append(nodo(5, "ONT_ONU"))
    conexiones.append(conexion(4, 5))
    with pytest.raises(TopologiaInvalidaError, match="único enlace"):
        calcular_enlaces(componentes, conexiones)


def test_cable_individual_no_puede_alimentar_varios_pares_sin_splitter():
    componentes, _ = red_lote()
    with pytest.raises(TopologiaInvalidaError, match="splitter"):
        calcular_enlaces(componentes, [conexion(1, 3), conexion(3, 2), conexion(2, 4)])


def test_lotes_desconectados_y_fibras_sin_terminar_impiden_viabilidad():
    componentes, conexiones = red_lote()
    assert evaluar_viabilidad(componentes, conexiones[:-1]).estado == "incompleta"
    componentes.append(nodo(5, "FIBRA"))
    conexiones.append(conexion(3, 5))
    assert evaluar_viabilidad(componentes, conexiones).estado == "incompleta"


@pytest.fixture()
def lote_api(client, alumno_headers):
    ids = crear_topologia_valida(client, alumno_headers)
    r = client.post('/componentes/', json=datos_lote(ids["topologia_id"]), headers=alumno_headers)
    assert r.status_code == 200
    ids["lote_id"] = r.json()["id"]
    return ids


def conectar_lote(client, headers, ids):
    # Orden inverso al recorrido óptico: las validaciones no dependen del dibujo.
    return client.post('/conexiones/', json=dict(topologia_id=ids["topologia_id"],
                       componente_origen_id=ids["lote_id"], componente_destino_id=ids["splitter_id"]), headers=headers)


def test_api_guarda_reabre_previsualiza_y_simula_lote(client, alumno_headers, lote_api, db_session):
    ids = lote_api
    assert conectar_lote(client, alumno_headers, ids).status_code == 200
    url = f'/topologias/{ids["topologia_id"]}/viabilidad'
    r = client.get(url, headers=alumno_headers)
    assert r.json()["estado"] == "viable"
    assert r.json()["cantidad_onts"] == 9  # una individual y ocho del lote
    enlace = next(e for e in r.json()["enlaces"] if e["ont_id"] == ids["lote_id"])
    assert enlace["cantidad_onts"] == 8
    assert enlace["longitud_total_km"] == 10
    assert enlace["perdida_total_db"] == pytest.approx(22.6)

    detalle = client.get(f'/proyectos/{ids["proyecto_id"]}/detalle', headers=alumno_headers).json()["topologia"]
    lote = next(c for c in detalle["componentes"] if c["id"] == ids["lote_id"])
    assert lote["cantidad"] == 8 and lote["longitud_km"] == 2 and lote["sensibilidad_min_dbm"] == -28
    lote["cantidad"] = 12
    previa = client.post(url, json={k: detalle[k] for k in ("componentes", "conexiones")}, headers=alumno_headers)
    assert previa.json()["cantidad_onts"] == 13
    assert db_session.get(Componente, ids["lote_id"]).cantidad == 8

    sim = client.post('/simulaciones/', json=dict(proyecto_id=ids["proyecto_id"], cantidad_usuarios=9,
                      tipo_consumo="streaming"), headers=alumno_headers).json()
    assert client.post(f'/simulaciones/{sim["id"]}/calcular', headers=alumno_headers).status_code == 200
    assert db_session.query(ResultadoOptico).count() == 1
    assert db_session.query(ResultadoTrafico).count() == 1


def test_api_rechaza_exceso_al_conectar_y_al_editar_sin_modificar_datos(client, alumno_headers, lote_api, db_session):
    ids = lote_api
    assert conectar_lote(client, alumno_headers, ids).status_code == 200
    datos = datos_lote(ids["topologia_id"], cantidad=32)  # más la ONT individual: 33 > 32
    r = client.put(f'/componentes/{ids["lote_id"]}', json=datos, headers=alumno_headers)
    assert r.status_code == 400 and "33" in r.json()["detail"]
    assert db_session.get(Componente, ids["lote_id"]).cantidad == 8
    r = client.post('/componentes/', json=datos, headers=alumno_headers)
    nuevo_id = r.json()["id"]
    r = client.post('/conexiones/', json=dict(topologia_id=ids["topologia_id"], componente_origen_id=nuevo_id,
                    componente_destino_id=ids["splitter_id"]), headers=alumno_headers)
    assert r.status_code == 400
    assert db_session.query(Conexion).count() == 4


def test_no_se_puede_reducir_splitter_por_debajo_de_salidas_ocupadas(client, alumno_headers, lote_api, db_session):
    ids = lote_api
    assert conectar_lote(client, alumno_headers, ids).status_code == 200
    datos = dict(topologia_id=ids["topologia_id"], tipo="SPLITTER", posicion_x=0, posicion_y=0, relacion_division="1:8")
    r = client.put(f'/componentes/{ids["splitter_id"]}', json=datos, headers=alumno_headers)
    assert r.status_code == 400
    assert db_session.get(Componente, ids["splitter_id"]).relacion_division == "1:32"


def test_bloque_no_admite_cables_adicionales_ni_conexion_a_otra_ont(client, alumno_headers, lote_api, db_session):
    ids = lote_api
    r = conectar_lote(client, alumno_headers, ids)
    assert r.status_code == 200
    conexion_id = r.json()["id"]
    datos = dict(topologia_id=ids["topologia_id"], componente_origen_id=ids["lote_id"], componente_destino_id=ids["ont_id"])
    assert client.post('/conexiones/', json=datos, headers=alumno_headers).status_code == 400
    assert client.put(f'/conexiones/{conexion_id}', json=datos, headers=alumno_headers).status_code == 400
    assert db_session.query(Conexion).count() == 4
    # Editar la misma conexión no se confunde con crear una conexión duplicada.
    datos["componente_destino_id"] = ids["splitter_id"]
    assert client.put(f'/conexiones/{conexion_id}', json=datos, headers=alumno_headers).status_code == 200


def test_cantidad_historica_incorrecta_no_puede_ejecutar_trafico(client, alumno_headers, lote_api, db_session, monkeypatch):
    ids = lote_api
    assert conectar_lote(client, alumno_headers, ids).status_code == 200
    db_session.get(Componente, ids["lote_id"]).cantidad = 33
    db_session.commit()

    def no_ejecutar(**kwargs):
        pytest.fail("No debe ejecutarse tráfico con un exceso de conexiones")

    monkeypatch.setattr('app.routers.simulacion.calcular_resultado_trafico', no_ejecutar)
    s = client.post('/simulaciones/', json=dict(proyecto_id=ids["proyecto_id"], cantidad_usuarios=34,
                    tipo_consumo="web"), headers=alumno_headers).json()
    r = client.post(f'/simulaciones/{s["id"]}/calcular', headers=alumno_headers)
    assert r.status_code == 422
    assert db_session.query(ResultadoOptico).count() == db_session.query(ResultadoTrafico).count() == 0
