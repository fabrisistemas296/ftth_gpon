"""Restricciones que también se pueden comprobar mientras la red está incompleta."""

from app.core.componentes import cantidad_de, tipo_base
from app.core.constantes import PERDIDAS_SPLITTER_DB
from app.services.calculo_optico import TopologiaInvalidaError, _construir_grafo


def validar_conexiones_en_edicion(componentes, conexiones) -> None:
    grafo = _construir_grafo(componentes, conexiones)
    por_id = {c.id: c for c in componentes}
    for c in componentes:
        vecinos = grafo[c.id]
        if tipo_base(c.tipo) == "ONT_ONU":
            if len(vecinos) > 1:
                raise TopologiaInvalidaError("Cada ONT o lote fibra + ONT admite una única conexión a la red.")
            if any(tipo_base(por_id[v].tipo) == "ONT_ONU" for v in vecinos):
                raise TopologiaInvalidaError("Una ONT o lote terminal no puede conectarse a otra ONT o lote terminal.")
        if c.tipo == "FIBRA" and len(vecinos) > 2:
            raise TopologiaInvalidaError("Cada fibra tiene dos extremos; usá un splitter para dividir la señal.")
        if c.tipo == "LOTE_FIBRA_ONT" and cantidad_de(c) > 1:
            if any(por_id[v].tipo != "SPLITTER" for v in vecinos):
                raise TopologiaInvalidaError("Un lote de varios pares fibra + ONT debe conectarse a un splitter.")
        if c.tipo == "OLT" and any(por_id[v].tipo == "OLT" for v in vecinos):
            raise TopologiaInvalidaError("Dos OLT no pueden conectarse entre sí.")

    # Comprobar ciclos incluso en fragmentos que todavía no llegan a la OLT.
    visitados = set()
    for raiz in grafo:
        if raiz in visitados:
            continue
        visitados.add(raiz)
        cola = [(raiz, None)]
        for actual, padre in cola:
            for vecino in grafo[actual]:
                if vecino == padre:
                    continue
                if vecino in visitados:
                    raise TopologiaInvalidaError("La red GPON no puede contener ciclos ni conexiones adicionales entre ramas.")
                visitados.add(vecino)
                cola.append((vecino, actual))

    # La OLT define cuál es la entrada del splitter, sin depender del sentido
    # con que el usuario dibujó cada conexión.
    padres = {}
    olts = [c for c in componentes if c.tipo == "OLT"]
    if len(olts) == 1:
        padres = {olts[0].id: None}
        cola = [olts[0].id]
        for actual in cola:
            for vecino in grafo[actual]:
                if vecino not in padres:
                    padres[vecino] = actual
                    cola.append(vecino)

    for c in componentes:
        if c.tipo != "SPLITTER":
            continue
        if c.relacion_division not in PERDIDAS_SPLITTER_DB:
            raise TopologiaInvalidaError(f"El splitter (id={c.id}) tiene una relación de división inválida.")
        # En un fragmento sin OLT, sólo los terminales tienen un sentido
        # inequívoco. El resto se vuelve a comprobar al unirlo con la OLT.
        salidas = [v for v in grafo[c.id] if
                   (c.id in padres and v != padres[c.id]) or
                   (c.id not in padres and tipo_base(por_id[v].tipo) == "ONT_ONU")]
        ocupadas = sum(cantidad_de(por_id[v]) for v in salidas)
        capacidad = int(c.relacion_division.split(":")[1])
        if ocupadas > capacidad:
            raise TopologiaInvalidaError(
                f"El splitter (id={c.id}, {c.relacion_division}) tiene {capacidad} salidas "
                f"y estas conexiones requieren {ocupadas}. Cada par del lote ocupa una salida."
            )
