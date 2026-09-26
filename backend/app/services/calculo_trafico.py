"""
app/services/calculo_trafico.py

Motor de cálculo de indicadores de tráfico (RF-19 a RF-24).

Estima el throughput agregado demandado por los usuarios de la red
según su cantidad y perfil de consumo, y lo compara contra la
capacidad total del puerto PON para determinar utilización,
congestión, throughput individual y tiempo de respuesta estimado.
"""

from dataclasses import dataclass

from app.core.constantes import (
    CAPACIDAD_DOWNSTREAM_MBPS,
    CONSUMO_PROMEDIO_MBPS,
    UMBRAL_CONGESTION_PCT,
    LATENCIA_BASE_MS,
    UTILIZACION_MAX_PARA_CALCULO,
)


class ParametrosTraficoInvalidosError(Exception):
    pass


@dataclass
class ResultadoTrafico:
    throughput_mbps: float              # throughput total efectivo de la red
    throughput_por_usuario_mbps: float  # throughput promedio disponible por usuario
    utilizacion_pct: float
    congestion: bool
    tiempo_respuesta_ms: float           # latencia estimada, incluye efecto de cola


def calcular_resultado_trafico(cantidad_usuarios: int, tipo_consumo: str) -> ResultadoTrafico:
    """
    Calcula throughput estimado (total y por usuario), utilización del
    enlace, congestión y tiempo de respuesta estimado, a partir de la
    cantidad de usuarios y su perfil de consumo predominante.

    Simplificación didáctica (ver 1.1 del informe): se asume consumo
    simultáneo homogéneo entre todos los usuarios según el perfil
    seleccionado, sin modelar ráfagas ni distribución estadística real
    de tráfico. El tiempo de respuesta se estima con un modelo
    simplificado inspirado en la teoría de colas M/M/1, no en una
    simulación física de la red.
    """
    if cantidad_usuarios <= 0:
        raise ParametrosTraficoInvalidosError("La cantidad de usuarios debe ser mayor a 0.")

    if tipo_consumo not in CONSUMO_PROMEDIO_MBPS:
        raise ParametrosTraficoInvalidosError(f"Tipo de consumo no soportado: {tipo_consumo!r}")

    demanda_total_mbps = cantidad_usuarios * CONSUMO_PROMEDIO_MBPS[tipo_consumo]

    # El throughput real no puede superar la capacidad física del puerto PON
    throughput_mbps = min(demanda_total_mbps, CAPACIDAD_DOWNSTREAM_MBPS)

    throughput_por_usuario_mbps = throughput_mbps / cantidad_usuarios

    utilizacion_pct = min(100.0, (demanda_total_mbps / CAPACIDAD_DOWNSTREAM_MBPS) * 100.0)

    congestion = utilizacion_pct >= UMBRAL_CONGESTION_PCT

    # Tiempo de respuesta estimado: crece de forma no lineal a medida
    # que la utilización se acerca al 100% (efecto de cola/congestión).
    utilizacion_fraccion = min(utilizacion_pct / 100.0, UTILIZACION_MAX_PARA_CALCULO)
    tiempo_respuesta_ms = LATENCIA_BASE_MS / (1 - utilizacion_fraccion)

    return ResultadoTrafico(
        throughput_mbps=round(throughput_mbps, 2),
        throughput_por_usuario_mbps=round(throughput_por_usuario_mbps, 3),
        utilizacion_pct=round(utilizacion_pct, 2),
        congestion=congestion,
        tiempo_respuesta_ms=round(tiempo_respuesta_ms, 2),
    )