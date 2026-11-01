from types import SimpleNamespace

import pytest

from app.models.models import Componente, ResultadoOptico, ResultadoTrafico, Simulacion
from app.services.calculo_optico import calcular_enlaces, resultado_peor_caso, TopologiaInvalidaError
from tests.conftest import crear_topologia_valida


def componente(id, tipo, **datos):
    base = dict(
        id=id, tipo=tipo, potencia_tx_dbm=5, clase_potencia="C+",
        longitud_km=8, atenuacion_db_km=0.28,
        cantidad_conectores=3, cantidad_empalmes=2,
        relacion_division="1:32", sensibilidad_min_dbm=-32,
        potencia_sobrecarga_dbm=-8,
    )
    return SimpleNamespace(**(base | datos))


def conexion(a, b):
    return SimpleNamespace(componente_origen_id=a, componente_destino_id=b)


def red(longitudes=(8,)):
    componentes = [componente(1, "OLT"), componente(2, "SPLITTER"), componente(3, "ONT_ONU")]
    fibras = [componente(i + 4, "FIBRA", longitud_km=l) for i, l in enumerate(longitudes)]
    recorrido = [1, *(f.id for f in fibras), 2, 3]
    return componentes + fibras, [conexion(a, b) for a, b in zip(recorrido, recorrido[1:])]


@pytest.mark.parametrize("longitudes,operativo", [((20,), True), ((12, 8), True), ((12, 8.001), False), ((21,), False)])
def test_alcance_se_evalua_sobre_el_recorrido_completo(longitudes, operativo):
    r = calcular_enlaces(*red(longitudes))[0]
    assert r.longitud_total_km == pytest.approx(sum(longitudes))
    assert (r.estado_operativo == "operativo") is operativo
    if not operativo:
        assert any("20 km" in m for m in r.motivos)
        # Aun con potencia dentro del rango, exceder el alcance no es viable.
        assert -32 < r.potencia_recibida_dbm < -8


def test_se_evaluan_ramas_individuales_sin_sumar_toda_la_fibra_de_la_red():
    componentes, conexiones = red((10,))
    componentes.extend([componente(5, "FIBRA", longitud_km=8), componente(6, "ONT_ONU"),
                        componente(7, "FIBRA", longitud_km=9), componente(8, "ONT_ONU")])
    conexiones.extend([conexion(2, 5), conexion(5, 6), conexion(2, 7), conexion(7, 8)])
    resultados = calcular_enlaces(componentes, conexiones)
    assert [r.longitud_total_km for r in resultados] == [10, 18, 19]
    assert all(r.estado_operativo == "operativo" for r in resultados)


@pytest.mark.parametrize("tx,motivo", [(-30, "sensibilidad"), (15, "sobrecarga")])
def test_la_potencia_es_independiente_del_alcance(tx, motivo):
    componentes, conexiones = red()
    componentes[0].potencia_tx_dbm = tx
    r = calcular_enlaces(componentes, conexiones)[0]
    assert r.longitud_total_km < 20
    assert r.estado_operativo == "fuera_de_rango"
    assert any(motivo in m for m in r.motivos)


def test_presupuesto_de_clase_no_se_elude_con_sensibilidad_irreal():
    componentes, conexiones = red((20,))
    componentes[0].clase_potencia = "B+"
    componentes[1].relacion_division = "1:64"
    componentes[2].sensibilidad_min_dbm = -45
    componentes[-1].atenuacion_db_km = 0.4
    r = calcular_enlaces(componentes, conexiones)[0]
    assert r.margen_db > 0
    assert any("presupuesto" in m for m in r.motivos)


def test_ciclo_no_elige_arbitrariamente_el_camino_mas_corto():
    componentes, conexiones = red((12, 12))
    conexiones.append(conexion(1, 2))
    with pytest.raises(TopologiaInvalidaError, match="ciclos"):
        calcular_enlaces(componentes, conexiones)


def test_splitters_en_cascada_acumulan_longitud_y_perdidas():
    componentes = [componente(1, "OLT"), componente(2, "FIBRA", longitud_km=12),
                   componente(3, "SPLITTER", relacion_division="1:2"),
                   componente(4, "FIBRA", longitud_km=9),
                   componente(5, "SPLITTER", relacion_division="1:4"), componente(6, "ONT_ONU")]
    conexiones = [conexion(i, i + 1) for i in range(1, 6)]
    r = calcular_enlaces(componentes, conexiones)[0]
    assert r.longitud_total_km == 21
    assert r.perdida_total_db == pytest.approx(21 * 0.28 + 2 * 1.4 + 3.5 + 7)
    assert r.estado_operativo == "fuera_de_rango"


def test_splitter_no_admite_mas_salidas_que_su_relacion():
    componentes, conexiones = red()
    componentes[1].relacion_division = "1:2"
    componentes.extend([componente(5, "ONT_ONU"), componente(6, "ONT_ONU")])
    conexiones.extend([conexion(2, 5), conexion(2, 6)])
    with pytest.raises(TopologiaInvalidaError, match="salidas"):
        calcular_enlaces(componentes, conexiones)


def test_una_fibra_no_puede_dividir_la_senal_sin_splitter():
    componentes, conexiones = red()
    componentes.append(componente(5, "ONT_ONU"))
    conexiones.append(conexion(4, 5))
    with pytest.raises(TopologiaInvalidaError, match="splitter"):
        calcular_enlaces(componentes, conexiones)


def test_peor_caso_considera_el_limite_de_sobrecarga():
    componentes, conexiones = red()
    componentes.extend([componente(5, "FIBRA", longitud_km=1), componente(6, "ONT_ONU", potencia_sobrecarga_dbm=-13)])
    conexiones.extend([conexion(2, 5), conexion(5, 6)])
    resultados = calcular_enlaces(componentes, conexiones)
    assert resultado_peor_caso(resultados).ont_id == 6


@pytest.mark.parametrize("longitud", [0, -1, float("nan"), float("inf")])
def test_datos_historicos_invalidos_no_se_consideran_viables(longitud):
    with pytest.raises(TopologiaInvalidaError, match="inválidas"):
        calcular_enlaces(*red((longitud,)))


def test_viabilidad_en_vivo_no_crea_simulaciones_ni_modifica_componentes(client, alumno_headers, db_session):
    ids = crear_topologia_valida(client, alumno_headers)
    url = f'/topologias/{ids["topologia_id"]}/viabilidad'
    actual = client.get(url, headers=alumno_headers)
    assert actual.status_code == 200
    assert actual.json()["estado"] == "viable"
    assert actual.json()["enlaces"][0]["perdida_total_db"] == pytest.approx(21.14)

    detalle = client.get(f'/proyectos/{ids["proyecto_id"]}/detalle', headers=alumno_headers).json()
    previa = {k: detalle["topologia"][k] for k in ("componentes", "conexiones")}
    next(c for c in previa["componentes"] if c["tipo"] == "FIBRA")["longitud_km"] = 25
    r = client.post(url, json=previa, headers=alumno_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "no_viable"
    assert r.json()["enlaces"][0]["longitud_total_km"] == 25
    assert db_session.get(Componente, ids["fibra_id"]).longitud_km == 8
    assert db_session.query(Simulacion).count() == 0
    assert client.get(url, headers=alumno_headers).json()["estado"] == "viable"


def test_viabilidad_respeta_permisos(client, alumno_headers, otro_alumno_headers, profesor_headers):
    ids = crear_topologia_valida(client, alumno_headers)
    url = f'/topologias/{ids["topologia_id"]}/viabilidad'
    assert client.get(url).status_code == 401
    assert client.get(url, headers=otro_alumno_headers).status_code == 403
    assert client.post(url, json={"componentes": [], "conexiones": []}, headers=otro_alumno_headers).status_code == 403
    assert client.get(url, headers=profesor_headers).status_code == 200
    assert client.get('/topologias/99999/viabilidad', headers=alumno_headers).status_code == 404


def test_topologia_incompleta_da_diagnostico_sin_simular(client, alumno_headers):
    p = client.post('/proyectos/', json={"nombre": "Vacía"}, headers=alumno_headers).json()
    t = client.post('/topologias/', json={"proyecto_id": p["id"]}, headers=alumno_headers).json()
    r = client.get(f'/topologias/{t["id"]}/viabilidad', headers=alumno_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "incompleta"
    assert r.json()["motivos"]
    assert r.json()["enlaces"] == []


@pytest.mark.parametrize("longitud", [0, -1, 20.001])
def test_api_rechaza_creacion_y_edicion_de_tramos_invalidos(client, alumno_headers, longitud):
    ids = crear_topologia_valida(client, alumno_headers)
    datos = dict(topologia_id=ids["topologia_id"], tipo="FIBRA", posicion_x=0, posicion_y=0,
                 longitud_km=longitud, atenuacion_db_km=0.28)
    assert client.post('/componentes/', json=datos, headers=alumno_headers).status_code == 422
    assert client.put(f'/componentes/{ids["fibra_id"]}', json=datos, headers=alumno_headers).status_code == 422


@pytest.mark.parametrize("caso", ["distancia", "potencia"])
def test_servidor_bloquea_trafico_inviable_sin_persistir_resultados(client, alumno_headers, db_session, monkeypatch, caso):
    ids = crear_topologia_valida(client, alumno_headers)
    if caso == "distancia":
        # Simula un registro creado antes de incorporar el límite de 20 km.
        db_session.get(Componente, ids["fibra_id"]).longitud_km = 25
    else:
        db_session.get(Componente, ids["olt_id"]).potencia_tx_dbm = -30
    db_session.commit()

    def trafico_no_debe_ejecutarse(**kwargs):
        pytest.fail("Se ejecutó tráfico sobre una red no viable")

    monkeypatch.setattr('app.routers.simulacion.calcular_resultado_trafico', trafico_no_debe_ejecutarse)
    s = client.post('/simulaciones/', json={"proyecto_id": ids["proyecto_id"], "cantidad_usuarios": 32,
                                          "tipo_consumo": "web"}, headers=alumno_headers).json()
    r = client.post(f'/simulaciones/{s["id"]}/calcular', headers=alumno_headers)
    assert r.status_code == 422
    assert "no es viable" in r.json()["detail"]
    assert db_session.query(ResultadoOptico).count() == 0
    assert db_session.query(ResultadoTrafico).count() == 0
