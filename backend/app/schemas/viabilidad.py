from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.constantes import ALCANCE_MAXIMO_GPON_KM
from app.schemas.componente import ComponenteResponse
from app.schemas.conexion import ConexionResponse


class TopologiaPrevia(BaseModel):
    # Es una fotografía temporal; nunca se guarda ni se usa para ejecutar tráfico.
    componentes: list[ComponenteResponse]
    conexiones: list[ConexionResponse]


class EnlaceViabilidad(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ont_id: int
    cantidad_onts: int = 1
    longitud_total_km: float
    perdida_total_db: float
    potencia_recibida_dbm: float
    margen_db: float
    margen_sobrecarga_db: float
    estado_operativo: str
    motivos: list[str]


class ViabilidadResponse(BaseModel):
    estado: Literal["viable", "no_viable", "incompleta"]
    alcance_maximo_km: float = ALCANCE_MAXIMO_GPON_KM
    motivos: list[str]
    enlaces: list[EnlaceViabilidad]
    cantidad_onts: int = 0
