from app.schemas.viabilidad import EnlaceViabilidad, ViabilidadResponse
from app.services.calculo_optico import TopologiaInvalidaError, calcular_enlaces


def evaluar_viabilidad(componentes, conexiones) -> ViabilidadResponse:
    try:
        enlaces = calcular_enlaces(componentes, conexiones)
    except TopologiaInvalidaError as exc:
        return ViabilidadResponse(estado="incompleta", motivos=[str(exc)], enlaces=[])
    motivos = [f"ONT/ONU {e.ont_id}: {motivo}" for e in enlaces for motivo in e.motivos]
    return ViabilidadResponse(
        estado="no_viable" if motivos else "viable",
        motivos=motivos,
        enlaces=[EnlaceViabilidad.model_validate(e) for e in enlaces],
    )
