from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.core.deps import get_usuario_actual, requerir_rol_alumno
from app.models.models import (
    Proyecto,
    Topologia,
    Componente,
    Conexion,
    Simulacion,
    ResultadoOptico,
    ResultadoTrafico,
    Usuario,
)
from app.schemas.proyecto import ProyectoCreate, ProyectoResponse
from app.schemas.proyecto_detalle import (
    ProyectoDetalleResponse,
    TopologiaDetalleResponse,
    SimulacionDetalleResponse,
)

router = APIRouter(
    prefix="/proyectos",
    tags=["Proyectos"]
)


def _verificar_acceso_proyecto(proyecto: Proyecto, usuario: Usuario):
    """
    Un alumno solo puede acceder a sus propios proyectos.
    Un profesor puede acceder (solo lectura) a cualquier proyecto.
    """
    if usuario.rol == "alumno" and proyecto.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para acceder a este proyecto"
        )


@router.get("/", response_model=list[ProyectoResponse])
def obtener_proyectos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    """
    Alumno: ve solo sus propios proyectos.
    Profesor: ve los proyectos de todos los alumnos (RF-06).
    """
    if usuario.rol == "profesor":
        return db.query(Proyecto).all()

    return db.query(Proyecto).filter(Proyecto.usuario_id == usuario.id).all()


@router.post("/", response_model=ProyectoResponse)
def crear_proyecto(
    proyecto: ProyectoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),  # solo alumnos crean proyectos
):
    nuevo_proyecto = Proyecto(
        nombre=proyecto.nombre,
        descripcion=proyecto.descripcion,
        usuario_id=usuario.id,  # <- del token, NUNCA del body (evita crear a nombre de otro)
    )

    db.add(nuevo_proyecto)
    db.commit()
    db.refresh(nuevo_proyecto)

    return nuevo_proyecto


@router.get("/{proyecto_id}", response_model=ProyectoResponse)
def obtener_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    _verificar_acceso_proyecto(proyecto, usuario)

    return proyecto


@router.get("/{proyecto_id}/detalle", response_model=ProyectoDetalleResponse)
def obtener_detalle_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_actual),
):
    """
    Vista completa de un proyecto: topología (con sus componentes y
    conexiones) y todas sus simulaciones (con sus resultados), en una
    sola respuesta. Pensado para el Profesor, que necesita revisar el
    trabajo de un alumno sin encadenar múltiples llamadas; el Alumno
    dueño del proyecto también puede usarlo.
    """
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    _verificar_acceso_proyecto(proyecto, usuario)

    # --- Topología, componentes y conexiones ---
    topologia_db = db.query(Topologia).filter(Topologia.proyecto_id == proyecto_id).first()
    topologia_detalle = None
    if topologia_db:
        componentes = db.query(Componente).filter(
            Componente.topologia_id == topologia_db.id
        ).all()
        conexiones = db.query(Conexion).filter(
            Conexion.topologia_id == topologia_db.id
        ).all()
        topologia_detalle = TopologiaDetalleResponse(
            id=topologia_db.id,
            proyecto_id=topologia_db.proyecto_id,
            componentes=componentes,
            conexiones=conexiones,
        )

    # --- Simulaciones con sus resultados ---
    simulaciones_db = db.query(Simulacion).filter(
        Simulacion.proyecto_id == proyecto_id
    ).all()

    simulaciones_detalle = []
    for sim in simulaciones_db:
        resultado_optico = db.query(ResultadoOptico).filter(
            ResultadoOptico.simulacion_id == sim.id
        ).first()
        resultado_trafico = db.query(ResultadoTrafico).filter(
            ResultadoTrafico.simulacion_id == sim.id
        ).first()

        simulaciones_detalle.append(
            SimulacionDetalleResponse(
                id=sim.id,
                escenario_id=sim.escenario_id,
                fecha_ejecucion=sim.fecha_ejecucion,
                cantidad_usuarios=sim.cantidad_usuarios,
                tipo_consumo=sim.tipo_consumo,
                resultado_optico=resultado_optico,
                resultado_trafico=resultado_trafico,
            )
        )

    return ProyectoDetalleResponse(
        id=proyecto.id,
        nombre=proyecto.nombre,
        descripcion=proyecto.descripcion,
        usuario_id=proyecto.usuario_id,
        fecha_creacion=proyecto.fecha_creacion,
        fecha_modificacion=proyecto.fecha_modificacion,
        topologia=topologia_detalle,
        simulaciones=simulaciones_detalle,
    )


@router.put("/{proyecto_id}", response_model=ProyectoResponse)
def actualizar_proyecto(
    proyecto_id: int,
    proyecto_data: ProyectoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),  # profesores no editan (solo lectura)
):
    proyecto_existente = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto_existente:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    if proyecto_existente.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para editar este proyecto"
        )

    proyecto_existente.nombre = proyecto_data.nombre
    proyecto_existente.descripcion = proyecto_data.descripcion
    # usuario_id NO se actualiza: el dueño de un proyecto no cambia
    proyecto_existente.fecha_modificacion = datetime.now(timezone.utc).isoformat(
        sep=" ", timespec="seconds"
    )

    db.commit()
    db.refresh(proyecto_existente)

    return proyecto_existente


@router.delete("/{proyecto_id}", response_model=ProyectoResponse)
def eliminar_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requerir_rol_alumno),
):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    if proyecto.usuario_id != usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para eliminar este proyecto"
        )

    db.delete(proyecto)
    db.commit()

    return proyecto