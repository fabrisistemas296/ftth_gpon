"""
app/services/calculo_optico.py

Motor de cálculo del presupuesto óptico (RF-08 a RF-14, RF-18).

Recorre la topología real guardada en la base de datos (componentes +
conexiones), calcula la pérdida total desde la OLT hasta cada ONT/ONU
alcanzable, y determina el estado operativo de cada enlace.

No recibe valores calculados desde el cliente: todo se deriva de los
parámetros configurados en los componentes de la topología, evitando
que un usuario pueda enviar un resultado inventado.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.models import Componente, Conexion
from app.core.constantes import (
    PERDIDA_CONECTOR_DB,
    PERDIDA_EMPALME_DB,
    PERDIDAS_SPLITTER_DB,
)


class TopologiaInvalidaError(Exception):
    """Se lanza cuando la topología no cumple las condiciones mínimas
    para poder calcular un presupuesto óptico (RF-14)."""
    pass


@dataclass
class ResultadoEnlace:
    ont_id: int
    perdida_total_db: float
    potencia_recibida_dbm: float
    margen_db: float           # potencia_recibida - sensibilidad_min (cuánto "sobra")
    estado_operativo: str      # "operativo" | "fuera_de_rango"


# ------------------------------------------------------------------
# Cálculo de pérdida de un componente individual
# ------------------------------------------------------------------
def perdida_de_componente(componente: Componente) -> float:
    """
    Devuelve la pérdida en dB introducida por un componente puntual.
    OLT y ONT/ONU no introducen pérdida propia (son los extremos del
    enlace); solo Fibra y Splitter aportan pérdida.
    """
    if componente.tipo == "FIBRA":
        atenuacion = componente.atenuacion_db_km or 0.0
        longitud = componente.longitud_km or 0.0
        conectores = componente.cantidad_conectores or 0
        empalmes = componente.cantidad_empalmes or 0

        return (
            atenuacion * longitud
            + conectores * PERDIDA_CONECTOR_DB
            + empalmes * PERDIDA_EMPALME_DB
        )

    if componente.tipo == "SPLITTER":
        relacion = componente.relacion_division
        if relacion not in PERDIDAS_SPLITTER_DB:
            raise TopologiaInvalidaError(
                f"Relación de división no soportada en el splitter "
                f"(id={componente.id}): {relacion!r}"
            )
        return PERDIDAS_SPLITTER_DB[relacion]

    # OLT y ONT_ONU no introducen pérdida propia
    return 0.0


# ------------------------------------------------------------------
# Construcción del grafo de la topología y búsqueda de caminos
# ------------------------------------------------------------------
def _construir_grafo(componentes: list[Componente], conexiones: list[Conexion]) -> dict[int, set[int]]:
    grafo: dict[int, set[int]] = {c.id: set() for c in componentes}
    for conexion in conexiones:
        grafo.setdefault(conexion.componente_origen_id, set()).add(conexion.componente_destino_id)
        grafo.setdefault(conexion.componente_destino_id, set()).add(conexion.componente_origen_id)
    return grafo


def _bfs_camino(grafo: dict[int, set[int]], origen_id: int, destino_id: int) -> list[int] | None:
    """Búsqueda en anchura del camino entre dos componentes. Devuelve
    la lista de ids del camino (incluyendo origen y destino), o None
    si no hay conexión entre ambos."""
    if origen_id == destino_id:
        return [origen_id]

    visitados = {origen_id}
    cola: list[list[int]] = [[origen_id]]

    while cola:
        camino_actual = cola.pop(0)
        nodo_actual = camino_actual[-1]

        for vecino in grafo.get(nodo_actual, set()):
            if vecino in visitados:
                continue
            nuevo_camino = camino_actual + [vecino]
            if vecino == destino_id:
                return nuevo_camino
            visitados.add(vecino)
            cola.append(nuevo_camino)

    return None


# ------------------------------------------------------------------
# Cálculo del presupuesto óptico para toda la topología
# ------------------------------------------------------------------
def calcular_resultados_opticos(db: Session, topologia_id: int) -> list[ResultadoEnlace]:
    """
    Calcula el presupuesto óptico entre la OLT y cada ONT/ONU
    alcanzable dentro de la topología indicada.

    Lanza TopologiaInvalidaError si:
    - No hay exactamente una OLT en la topología.
    - No hay ninguna ONT/ONU.
    - Alguna ONT/ONU no está conectada (directa o indirectamente) a la OLT.
    - Se encuentra un splitter con relación de división no soportada.
    """
    componentes = db.query(Componente).filter(
        Componente.topologia_id == topologia_id
    ).all()
    conexiones = db.query(Conexion).filter(
        Conexion.topologia_id == topologia_id
    ).all()

    olts = [c for c in componentes if c.tipo == "OLT"]
    onts = [c for c in componentes if c.tipo == "ONT_ONU"]

    if len(olts) != 1:
        raise TopologiaInvalidaError(
            f"La topología debe tener exactamente una OLT (se encontraron {len(olts)})."
        )
    if not onts:
        raise TopologiaInvalidaError("La topología no tiene ninguna ONT/ONU configurada.")

    olt = olts[0]
    if olt.potencia_tx_dbm is None:
        raise TopologiaInvalidaError("La OLT no tiene configurada su potencia de transmisión.")

    grafo = _construir_grafo(componentes, conexiones)
    componentes_por_id = {c.id: c for c in componentes}

    resultados: list[ResultadoEnlace] = []

    for ont in onts:
        camino = _bfs_camino(grafo, olt.id, ont.id)
        if camino is None:
            raise TopologiaInvalidaError(
                f"La ONT/ONU (id={ont.id}) no está conectada a la OLT."
            )

        # Se excluyen los dos extremos (OLT y ONT), que no introducen pérdida propia
        perdida_total = sum(
            perdida_de_componente(componentes_por_id[cid])
            for cid in camino[1:-1]
        )

        potencia_recibida = olt.potencia_tx_dbm - perdida_total

        sensibilidad_min = ont.sensibilidad_min_dbm
        potencia_sobrecarga = ont.potencia_sobrecarga_dbm

        if sensibilidad_min is None or potencia_sobrecarga is None:
            raise TopologiaInvalidaError(
                f"La ONT/ONU (id={ont.id}) no tiene configurados sus rangos de potencia."
            )

        if sensibilidad_min <= potencia_recibida <= potencia_sobrecarga:
            estado = "operativo"
        else:
            estado = "fuera_de_rango"

        margen = potencia_recibida - sensibilidad_min

        resultados.append(
            ResultadoEnlace(
                ont_id=ont.id,
                perdida_total_db=round(perdida_total, 3),
                potencia_recibida_dbm=round(potencia_recibida, 3),
                margen_db=round(margen, 3),
                estado_operativo=estado,
            )
        )

    return resultados


def resultado_peor_caso(resultados: list[ResultadoEnlace]) -> ResultadoEnlace:
    """
    Dado que resultado_optico tiene una relación 1:1 con simulacion,
    se persiste un único resultado representativo del estado general
    de la red. Se elige así:

    1. Si algún enlace está "fuera_de_rango", se prioriza el de menor
       margen entre esos (el caso más crítico).
    2. Si todos están "operativo", se toma igualmente el de menor
       margen (el más cercano a quedar fuera de rango), como
       indicador de "cuello de botella" de la red diseñada.
    """
    fuera_de_rango = [r for r in resultados if r.estado_operativo == "fuera_de_rango"]
    candidatos = fuera_de_rango if fuera_de_rango else resultados
    return min(candidatos, key=lambda r: r.margen_db)
