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

from dataclasses import dataclass, field
from math import isfinite, fsum

from sqlalchemy.orm import Session

from app.models.models import Componente, Conexion
from app.core.componentes import TIPOS_LOTE, cantidad_de, tipo_base, tiene_fibra
from app.core.constantes import (
    PERDIDA_CONECTOR_DB,
    PERDIDA_EMPALME_DB,
    PERDIDAS_SPLITTER_DB,
    ALCANCE_MAXIMO_GPON_KM,
    PRESUPUESTOS_OPTICOS_DB,
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
    longitud_total_km: float
    margen_sobrecarga_db: float
    motivos: list[str] = field(default_factory=list)
    cantidad_onts: int = 1


# ------------------------------------------------------------------
# Cálculo de pérdida de un componente individual
# ------------------------------------------------------------------
def perdida_de_componente(componente: Componente) -> float:
    """
    Devuelve la pérdida en dB introducida por un componente puntual.
    El bloque fibra + ONT aporta la pérdida de su cable por cada recorrido,
    independientemente de cuántos pares idénticos represente.
    """
    if tiene_fibra(componente.tipo):
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
    if len(grafo) != len(componentes):
        raise TopologiaInvalidaError("Hay componentes con identificadores repetidos.")
    for conexion in conexiones:
        origen, destino = conexion.componente_origen_id, conexion.componente_destino_id
        if origen not in grafo or destino not in grafo:
            raise TopologiaInvalidaError("Una conexión referencia componentes ajenos a la topología.")
        if origen == destino or destino in grafo[origen]:
            raise TopologiaInvalidaError("Hay conexiones repetidas o de un componente consigo mismo.")
        grafo[origen].add(destino)
        grafo[destino].add(origen)
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

    return calcular_enlaces(componentes, conexiones)


def calcular_enlaces(componentes: list[Componente], conexiones: list[Conexion]) -> list[ResultadoEnlace]:
    """Motor compartido por la vista previa sin persistencia y la simulación.

    Acepta también objetos Pydantic con los mismos atributos que los modelos.
    Los datos históricos se validan aquí: no se asumen válidos por estar guardados.
    """
    olts = [c for c in componentes if c.tipo == "OLT"]
    onts = [c for c in componentes if tipo_base(c.tipo) == "ONT_ONU"]

    if len(olts) != 1:
        raise TopologiaInvalidaError(
            f"La topología debe tener exactamente una OLT (se encontraron {len(olts)})."
        )
    if not onts:
        raise TopologiaInvalidaError("La topología no tiene ninguna ONT/ONU configurada.")

    olt = olts[0]
    if olt.potencia_tx_dbm is None or not isfinite(olt.potencia_tx_dbm):
        raise TopologiaInvalidaError("La OLT no tiene configurada su potencia de transmisión.")

    grafo = _construir_grafo(componentes, conexiones)
    componentes_por_id = {c.id: c for c in componentes}

    # GPON se representa como un árbol: un camino único hacia cada receptor.
    # Un BFS sobre un ciclo elegiría arbitrariamente un camino y sus pérdidas.
    padres = {olt.id: None}
    cola = [olt.id]
    for actual in cola:
        for vecino in sorted(grafo[actual]):
            if vecino == padres[actual]:
                continue
            if vecino in padres:
                raise TopologiaInvalidaError("La red GPON no puede contener ciclos ni caminos alternativos.")
            padres[vecino] = actual
            cola.append(vecino)

    for c in componentes:
        if c.tipo not in {"OLT", "FIBRA", "SPLITTER", "ONT_ONU", *TIPOS_LOTE}:
            raise TopologiaInvalidaError(f"Tipo de componente no soportado (id={c.id}).")
        cantidad = cantidad_de(c)
        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or not 1 <= cantidad <= 2147483647:
            raise TopologiaInvalidaError(f"El componente (id={c.id}) debe tener una cantidad entera mayor que cero.")
        if c.tipo not in TIPOS_LOTE and cantidad != 1:
            raise TopologiaInvalidaError(f"El componente individual (id={c.id}) debe tener cantidad 1.")
        if c.id not in padres:
            raise TopologiaInvalidaError(f"El componente (id={c.id}) no está conectado a la OLT.")
        grado = len(grafo[c.id])
        if c.tipo == "FIBRA":
            if grado != 2:
                raise TopologiaInvalidaError(f"La fibra (id={c.id}) debe conectar dos extremos; la división requiere un splitter.")
        if tiene_fibra(c.tipo):
            if (c.longitud_km is None or not isfinite(c.longitud_km) or c.longitud_km <= 0
                    or c.atenuacion_db_km is None or not isfinite(c.atenuacion_db_km)
                    or not 0 <= c.atenuacion_db_km <= 2):
                raise TopologiaInvalidaError(f"La fibra (id={c.id}) tiene longitud o atenuación inválidas.")
            for campo, maximo in (("cantidad_conectores", 50), ("cantidad_empalmes", 100)):
                valor = getattr(c, campo)
                if valor is not None and (not isfinite(valor) or int(valor) != valor or not 0 <= valor <= maximo):
                    raise TopologiaInvalidaError(f"La fibra (id={c.id}) tiene {campo} inválida.")
        if tipo_base(c.tipo) == "ONT_ONU" and grado != 1:
            raise TopologiaInvalidaError(f"La ONT/ONU (id={c.id}) debe tener un único enlace y no puede actuar como tránsito.")
        if c.tipo == "LOTE_FIBRA_ONT" and cantidad > 1:
            padre = componentes_por_id[padres[c.id]]
            if padre.tipo != "SPLITTER":
                raise TopologiaInvalidaError(
                    f"El lote fibra + ONT (id={c.id}) representa {cantidad} pares y debe conectarse "
                    "a un splitter con esa cantidad de salidas disponibles. Una fibra individual no puede dividir la señal."
                )
        if c.tipo == "SPLITTER":
            perdida_de_componente(c)  # valida la relación antes de interpretarla
            ocupadas = sum(cantidad_de(componentes_por_id[v]) for v in grafo[c.id] if v != padres[c.id])
            if ocupadas > int(c.relacion_division.split(":")[1]):
                raise TopologiaInvalidaError(
                    f"El splitter (id={c.id}) solicita {ocupadas} salidas y excede sus salidas {c.relacion_division}."
                )

    resultados: list[ResultadoEnlace] = []

    for ont in onts:
        camino = _bfs_camino(grafo, olt.id, ont.id)
        if camino is None:
            raise TopologiaInvalidaError(
                f"La ONT/ONU (id={ont.id}) no está conectada a la OLT."
            )

        # La ONT individual aporta cero; el bloque terminal incluye su fibra.
        perdida_total = sum(
            perdida_de_componente(componentes_por_id[cid])
            for cid in camino[1:]
        )
        longitud_total = fsum(
            componentes_por_id[cid].longitud_km
            for cid in camino[1:] if tiene_fibra(componentes_por_id[cid].tipo)
        )

        if not isfinite(perdida_total) or not isfinite(longitud_total):
            raise TopologiaInvalidaError(f"El recorrido hacia la ONT/ONU (id={ont.id}) tiene valores fuera de escala.")

        potencia_recibida = olt.potencia_tx_dbm - perdida_total

        sensibilidad_min = ont.sensibilidad_min_dbm
        potencia_sobrecarga = ont.potencia_sobrecarga_dbm

        if (sensibilidad_min is None or potencia_sobrecarga is None
                or not isfinite(sensibilidad_min) or not isfinite(potencia_sobrecarga)
                or sensibilidad_min >= potencia_sobrecarga):
            raise TopologiaInvalidaError(
                f"La ONT/ONU (id={ont.id}) no tiene configurados sus rangos de potencia."
            )

        motivos = []
        if longitud_total > ALCANCE_MAXIMO_GPON_KM:
            motivos.append(f"El recorrido OLT–ONT suma {longitud_total:.6g} km y supera los {ALCANCE_MAXIMO_GPON_KM:g} km del perfil GPON.")
        if potencia_recibida < sensibilidad_min:
            motivos.append("Potencia recibida por debajo de la sensibilidad mínima.")
        if potencia_recibida > potencia_sobrecarga:
            motivos.append("Potencia recibida por encima del límite de sobrecarga del receptor.")
        presupuesto = PRESUPUESTOS_OPTICOS_DB.get(olt.clase_potencia)
        if presupuesto is not None and perdida_total > presupuesto:
            motivos.append(f"Las pérdidas superan el presupuesto de {presupuesto:g} dB de clase {olt.clase_potencia}.")
        estado = "fuera_de_rango" if motivos else "operativo"

        margen = potencia_recibida - sensibilidad_min

        resultados.append(
            ResultadoEnlace(
                ont_id=ont.id,
                perdida_total_db=round(perdida_total, 3),
                potencia_recibida_dbm=round(potencia_recibida, 3),
                margen_db=round(margen, 3),
                estado_operativo=estado,
                longitud_total_km=longitud_total,
                margen_sobrecarga_db=round(potencia_sobrecarga - potencia_recibida, 3),
                motivos=motivos,
                cantidad_onts=cantidad_de(ont),
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
    El margen crítico es el menor entre sensibilidad y sobrecarga.
    """
    fuera_de_rango = [r for r in resultados if r.estado_operativo == "fuera_de_rango"]
    candidatos = fuera_de_rango if fuera_de_rango else resultados
    return min(candidatos, key=lambda r: min(r.margen_db, r.margen_sobrecarga_db))
