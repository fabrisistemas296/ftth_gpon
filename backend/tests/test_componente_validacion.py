"""
tests/test_componente_validacion.py

Valida las reglas de campos cruzados y obligatorios por tipo de
componente definidas en el schema (ComponenteCreate).
"""

import pytest
from pydantic import ValidationError

from app.schemas.componente import ComponenteCreate


BASE = {"topologia_id": 1, "posicion_x": 0, "posicion_y": 0}


def test_olt_valida():
    c = ComponenteCreate(**BASE, tipo="OLT", potencia_tx_dbm=5.0, clase_potencia="C+")
    assert c.tipo == "OLT"


def test_fibra_valida():
    c = ComponenteCreate(
        **BASE, tipo="FIBRA", longitud_km=8.0, atenuacion_db_km=0.28,
        cantidad_conectores=3, cantidad_empalmes=2,
    )
    assert c.longitud_km == 8.0


def test_fibra_sin_conectores_ni_empalmes_asume_cero():
    c = ComponenteCreate(**BASE, tipo="FIBRA", longitud_km=5.0, atenuacion_db_km=0.28)
    assert c.cantidad_conectores == 0
    assert c.cantidad_empalmes == 0


def test_splitter_valido():
    c = ComponenteCreate(**BASE, tipo="SPLITTER", relacion_division="1:32")
    assert c.relacion_division == "1:32"


def test_ont_onu_valida():
    c = ComponenteCreate(
        **BASE, tipo="ONT_ONU", sensibilidad_min_dbm=-32.0, potencia_sobrecarga_dbm=-8.0
    )
    assert c.sensibilidad_min_dbm == -32.0


def test_olt_con_campo_de_fibra_es_rechazada():
    with pytest.raises(ValidationError):
        ComponenteCreate(
            **BASE, tipo="OLT", potencia_tx_dbm=5.0, clase_potencia="C+", longitud_km=8.0
        )


def test_splitter_con_campo_de_ont_es_rechazado():
    with pytest.raises(ValidationError):
        ComponenteCreate(
            **BASE, tipo="SPLITTER", relacion_division="1:32", sensibilidad_min_dbm=-30.0
        )


def test_olt_sin_potencia_tx_es_rechazada():
    with pytest.raises(ValidationError):
        ComponenteCreate(**BASE, tipo="OLT", clase_potencia="C+")


def test_ont_onu_sin_potencia_sobrecarga_es_rechazada():
    with pytest.raises(ValidationError):
        ComponenteCreate(**BASE, tipo="ONT_ONU", sensibilidad_min_dbm=-32.0)


def test_fibra_sin_longitud_es_rechazada():
    with pytest.raises(ValidationError):
        ComponenteCreate(**BASE, tipo="FIBRA", atenuacion_db_km=0.28)


def test_splitter_con_relacion_no_soportada_es_rechazado():
    with pytest.raises(ValidationError):
        ComponenteCreate(**BASE, tipo="SPLITTER", relacion_division="1:128")
