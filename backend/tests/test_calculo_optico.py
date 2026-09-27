"""
tests/test_calculo_optico.py

Tests unitarios del motor de cálculo óptico (sin pasar por la API),
usando el escenario numérico validado en el punto 1.3 del informe:

OLT (C+, 5 dBm) -> Fibra 8km (0.28 dB/km, 3 conectores, 2 empalmes)
                -> Splitter 1:32 -> ONT (sensibilidad -32 dBm, sobrecarga -8 dBm)

Resultado esperado: pérdida total 21.14 dB, potencia recibida -16.14 dBm,
margen 15.86 dB, estado "operativo".
"""

import pytest
from dataclasses import dataclass

from app.services.calculo_optico import (
    perdida_de_componente,
    TopologiaInvalidaError,
)


@dataclass
class FakeComponente:
    id: int
    tipo: str
    potencia_tx_dbm: float = None
    clase_potencia: str = None
    longitud_km: float = None
    atenuacion_db_km: float = None
    cantidad_conectores: int = None
    cantidad_empalmes: int = None
    relacion_division: str = None
    sensibilidad_min_dbm: float = None
    potencia_sobrecarga_dbm: float = None


def test_perdida_fibra():
    fibra = FakeComponente(
        id=1, tipo="FIBRA", longitud_km=8.0, atenuacion_db_km=0.28,
        cantidad_conectores=3, cantidad_empalmes=2,
    )
    # 8*0.28 + 3*0.4 + 2*0.1 = 2.24 + 1.2 + 0.2 = 3.64
    assert perdida_de_componente(fibra) == pytest.approx(3.64, abs=0.001)


def test_perdida_splitter_1_32():
    splitter = FakeComponente(id=2, tipo="SPLITTER", relacion_division="1:32")
    assert perdida_de_componente(splitter) == pytest.approx(17.5, abs=0.001)


def test_perdida_splitter_relacion_no_soportada_lanza_error():
    splitter = FakeComponente(id=3, tipo="SPLITTER", relacion_division="1:128")
    with pytest.raises(TopologiaInvalidaError):
        perdida_de_componente(splitter)


def test_olt_y_ont_no_introducen_perdida_propia():
    olt = FakeComponente(id=4, tipo="OLT", potencia_tx_dbm=5.0)
    ont = FakeComponente(id=5, tipo="ONT_ONU", sensibilidad_min_dbm=-32.0, potencia_sobrecarga_dbm=-8.0)
    assert perdida_de_componente(olt) == 0.0
    assert perdida_de_componente(ont) == 0.0


class TestCalculoEndToEndViaAPI:
    """
    Prueba de integración: arma la topología completa vía la API
    (igual que probar_motor_calculo.py) y valida el resultado final.
    """

    def test_escenario_validado_en_el_punto_1_3(self, client, alumno_headers):
        from tests.conftest import crear_topologia_valida

        ids = crear_topologia_valida(client, alumno_headers)

        r = client.post("/simulaciones/", json={
            "proyecto_id": ids["proyecto_id"],
            "cantidad_usuarios": 32,
            "tipo_consumo": "streaming",
        }, headers=alumno_headers)
        simulacion_id = r.json()["id"]

        r = client.post(f"/simulaciones/{simulacion_id}/calcular", headers=alumno_headers)
        assert r.status_code == 200

        resultado = r.json()["resultado_optico"]
        assert resultado["perdida_total_db"] == pytest.approx(21.14, abs=0.01)
        assert resultado["potencia_recibida_dbm"] == pytest.approx(-16.14, abs=0.01)
        assert resultado["estado_operativo"] == "operativo"

    def test_ont_desconectada_de_la_olt_da_422(self, client, alumno_headers):
        r = client.post("/proyectos/", json={"nombre": "Test ONT suelta"}, headers=alumno_headers)
        proyecto_id = r.json()["id"]
        r = client.post("/topologias/", json={"proyecto_id": proyecto_id}, headers=alumno_headers)
        topologia_id = r.json()["id"]

        client.post("/componentes/", json={
            "topologia_id": topologia_id, "tipo": "OLT",
            "posicion_x": 0, "posicion_y": 0,
            "potencia_tx_dbm": 5.0, "clase_potencia": "C+",
        }, headers=alumno_headers)

        client.post("/componentes/", json={
            "topologia_id": topologia_id, "tipo": "ONT_ONU",
            "posicion_x": 0, "posicion_y": 0,
            "sensibilidad_min_dbm": -32.0, "potencia_sobrecarga_dbm": -8.0,
        }, headers=alumno_headers)
        # A propósito: no se conectan entre sí

        r = client.post("/simulaciones/", json={
            "proyecto_id": proyecto_id, "cantidad_usuarios": 10, "tipo_consumo": "web",
        }, headers=alumno_headers)
        simulacion_id = r.json()["id"]

        r = client.post(f"/simulaciones/{simulacion_id}/calcular", headers=alumno_headers)
        assert r.status_code == 422

    def test_topologia_sin_olt_da_422(self, client, alumno_headers):
        r = client.post("/proyectos/", json={"nombre": "Test sin OLT"}, headers=alumno_headers)
        proyecto_id = r.json()["id"]
        r = client.post("/topologias/", json={"proyecto_id": proyecto_id}, headers=alumno_headers)
        topologia_id = r.json()["id"]

        client.post("/componentes/", json={
            "topologia_id": topologia_id, "tipo": "ONT_ONU",
            "posicion_x": 0, "posicion_y": 0,
            "sensibilidad_min_dbm": -32.0, "potencia_sobrecarga_dbm": -8.0,
        }, headers=alumno_headers)

        r = client.post("/simulaciones/", json={
            "proyecto_id": proyecto_id, "cantidad_usuarios": 10, "tipo_consumo": "web",
        }, headers=alumno_headers)
        simulacion_id = r.json()["id"]

        r = client.post(f"/simulaciones/{simulacion_id}/calcular", headers=alumno_headers)
        assert r.status_code == 422
