from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_alumno
from app.models.models import (
    Simulacion,
    Proyecto,
    Topologia,
    EscenarioPredefinido,
    ResultadoOptico,
    ResultadoTrafico,
    Usuario
)
from app.schemas.simulacion import (
    SimulacionCreate,
    SimulacionResponse
)
from app.schemas.resultado_optico import ResultadoOpticoResponse
from app.schemas.resultado_trafico import ResultadoTraficoResponse

from app.services.calculo_optico import (
    calcular_resultados_opticos,
    resultado_peor_caso,
    TopologiaInvalidaError,
)
from app.services.calculo_trafico import (
    calcular_resultado_trafico,
    ParametrosTraficoInvalidosError,
)


router = APIRouter(
    prefix="/simulaciones",
    tags=["Simulaciones"]
)


class ResultadoCalculoResponse(BaseModel):
    resultado_optico: ResultadoOpticoResponse
    resultado_trafico: ResultadoTraficoResponse


def _verificar_acceso_proyecto(proyecto: Proyecto, usuario: Usuario):
    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre este proyecto")


@router.get("/{simulacion_id}", response_model=SimulacionResponse)
def obtener_simulacion(
    simulacion_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    simulacion = db.query(Simulacion).filter(Simulacion.id == simulacion_id).first()
    if not simulacion:
        raise HTTPException(status_code=404, detail="La simulación no existe")

    proyecto = db.query(Proyecto).filter(Proyecto.id == simulacion.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto asociado no existe")

    _verificar_acceso_proyecto(proyecto, usuario)

    return simulacion


@router.get("/", response_model=list[SimulacionResponse])
def obtener_simulaciones_por_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    """
    Lista las simulaciones de un proyecto puntual.
    Se exige proyecto_id como query param para no listar simulaciones
    de todos los proyectos sin filtro de dueño.
    """
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto no existe")

    _verificar_acceso_proyecto(proyecto, usuario)

    return db.query(Simulacion).filter(Simulacion.proyecto_id == proyecto_id).all()


@router.post("/", response_model=SimulacionResponse)
def crear_simulacion(
    datos: SimulacionCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == datos.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto no existe")

    if proyecto.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para simular sobre este proyecto"
        )

    escenario = None
    if datos.escenario_id is not None:
        escenario = db.query(EscenarioPredefinido).filter(
            EscenarioPredefinido.id == datos.escenario_id
        ).first()
        if not escenario:
            raise HTTPException(status_code=404, detail="El escenario no existe")

    # RF-22/RF-23: si no se especificó cantidad_usuarios, se autocompleta
    # con el valor por defecto del escenario elegido. Si se especificó,
    # se respeta el valor dado por el usuario (el escenario es solo un
    # punto de partida sugerido, no una restricción).
    cantidad_usuarios = datos.cantidad_usuarios
    if cantidad_usuarios is None:
        cantidad_usuarios = escenario.cantidad_usuarios_default

    nueva_simulacion = Simulacion(
        proyecto_id=datos.proyecto_id,
        escenario_id=datos.escenario_id,
        cantidad_usuarios=cantidad_usuarios,
        tipo_consumo=datos.tipo_consumo
    )

    db.add(nueva_simulacion)
    db.commit()
    db.refresh(nueva_simulacion)

    return nueva_simulacion


@router.post("/{simulacion_id}/calcular", response_model=ResultadoCalculoResponse)
def calcular_simulacion(
    simulacion_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    """
    Ejecuta el motor de cálculo (óptico + tráfico) sobre la simulación
    indicada, a partir de la topología real del proyecto, y persiste
    (o actualiza) sus resultados.
    """
    simulacion = db.query(Simulacion).filter(Simulacion.id == simulacion_id).first()
    if not simulacion:
        raise HTTPException(status_code=404, detail="La simulación no existe")

    proyecto = db.query(Proyecto).filter(Proyecto.id == simulacion.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="El proyecto asociado no existe")

    if proyecto.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tenés permiso sobre esta simulación")

    topologia = db.query(Topologia).filter(Topologia.proyecto_id == proyecto.id).first()
    if not topologia:
        raise HTTPException(status_code=404, detail="El proyecto no tiene una topología definida")

    # --- Cálculo óptico ---
    try:
        resultados_enlaces = calcular_resultados_opticos(db, topologia.id)
        peor_caso = resultado_peor_caso(resultados_enlaces)
    except TopologiaInvalidaError as e:
        raise HTTPException(status_code=422, detail=f"Topología inválida: {e}")

    # --- Cálculo de tráfico ---
    try:
        resultado_trafico_calc = calcular_resultado_trafico(
            cantidad_usuarios=simulacion.cantidad_usuarios,
            tipo_consumo=simulacion.tipo_consumo,
        )
    except ParametrosTraficoInvalidosError as e:
        raise HTTPException(status_code=422, detail=f"Parámetros de tráfico inválidos: {e}")

    # --- Persistencia (crea o actualiza, relación 1:1 con la simulación) ---
    resultado_optico_db = db.query(ResultadoOptico).filter(
        ResultadoOptico.simulacion_id == simulacion_id
    ).first()

    if resultado_optico_db is None:
        resultado_optico_db = ResultadoOptico(simulacion_id=simulacion_id)
        db.add(resultado_optico_db)

    resultado_optico_db.perdida_total_db = peor_caso.perdida_total_db
    resultado_optico_db.potencia_recibida_dbm = peor_caso.potencia_recibida_dbm
    resultado_optico_db.estado_operativo = peor_caso.estado_operativo

    resultado_trafico_db = db.query(ResultadoTrafico).filter(
        ResultadoTrafico.simulacion_id == simulacion_id
    ).first()

    if resultado_trafico_db is None:
        resultado_trafico_db = ResultadoTrafico(simulacion_id=simulacion_id)
        db.add(resultado_trafico_db)

    resultado_trafico_db.throughput_mbps = resultado_trafico_calc.throughput_mbps
    resultado_trafico_db.throughput_por_usuario_mbps = resultado_trafico_calc.throughput_por_usuario_mbps
    resultado_trafico_db.utilizacion_pct = resultado_trafico_calc.utilizacion_pct
    resultado_trafico_db.congestion = int(resultado_trafico_calc.congestion)
    resultado_trafico_db.tiempo_respuesta_ms = resultado_trafico_calc.tiempo_respuesta_ms

    db.commit()
    db.refresh(resultado_optico_db)
    db.refresh(resultado_trafico_db)

    return ResultadoCalculoResponse(
        resultado_optico=resultado_optico_db,
        resultado_trafico=resultado_trafico_db,
    )