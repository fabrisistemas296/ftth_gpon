"""
tests/test_calculo_trafico.py

Tests unitarios del motor de tráfico: RF-15 a RF-17.
"""

import pytest

from app.services.calculo_trafico import (
    calcular_resultado_trafico,
    ParametrosTraficoInvalidosError,
)


def test_caso_normal_sin_congestion():
    r = calcular_resultado_trafico(32, "streaming")
    assert r.throughput_mbps == pytest.approx(480.0, abs=0.01)
    assert r.throughput_por_usuario_mbps == pytest.approx(15.0, abs=0.01)
    assert r.utilizacion_pct == pytest.approx(19.29, abs=0.01)
    assert r.congestion is False


def test_caso_saturacion_marca_congestion():
    r = calcular_resultado_trafico(60, "descarga")
    # 60 * 50 Mbps = 3000 Mbps > 2488 Mbps de capacidad -> satura
    assert r.throughput_mbps == pytest.approx(2488.0, abs=0.01)
    assert r.utilizacion_pct == pytest.approx(100.0, abs=0.01)
    assert r.congestion is True


def test_tiempo_respuesta_crece_con_la_utilizacion():
    """El tiempo de respuesta debe aumentar a medida que sube la demanda."""
    bajo = calcular_resultado_trafico(10, "web")
    medio = calcular_resultado_trafico(100, "streaming")
    alto = calcular_resultado_trafico(60, "descarga")

    assert bajo.tiempo_respuesta_ms < medio.tiempo_respuesta_ms < alto.tiempo_respuesta_ms


def test_cantidad_usuarios_cero_lanza_error():
    with pytest.raises(ParametrosTraficoInvalidosError):
        calcular_resultado_trafico(0, "web")


def test_cantidad_usuarios_negativa_lanza_error():
    with pytest.raises(ParametrosTraficoInvalidosError):
        calcular_resultado_trafico(-5, "web")


def test_tipo_consumo_invalido_lanza_error():
    with pytest.raises(ParametrosTraficoInvalidosError):
        calcular_resultado_trafico(10, "tipo_inexistente")
