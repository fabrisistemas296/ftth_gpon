"""Un lote agrupa elementos idénticos en paralelo, con parámetros por unidad."""

TIPOS_LOTE = {"LOTE_FIBRA_ONT": "ONT_ONU"}


def tipo_base(tipo: str) -> str:
    return TIPOS_LOTE.get(tipo, tipo)


def cantidad_de(componente) -> int:
    return getattr(componente, "cantidad", 1)


def tiene_fibra(tipo: str) -> bool:
    return tipo in {"FIBRA", "LOTE_FIBRA_ONT"}
