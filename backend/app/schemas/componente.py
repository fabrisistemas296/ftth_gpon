from typing import Literal

from pydantic import BaseModel


class ComponenteCreate(BaseModel):
    topologia_id: int

    tipo: Literal["OLT", "FIBRA", "SPLITTER", "ONT_ONU"]

    posicion_x: float
    posicion_y: float

    potencia_tx_dbm: float | None = None
    clase_potencia: Literal["B+", "C+"] | None = None

    longitud_km: float | None = None
    atenuacion_db_km: float | None = None

    cantidad_conectores: int | None = None
    cantidad_empalmes: int | None = None

    relacion_division: Literal[
        "1:2",
        "1:4",
        "1:8",
        "1:16",
        "1:32",
        "1:64"
    ] | None = None

    sensibilidad_min_dbm: float | None = None
    potencia_sobrecarga_dbm: float | None = None


class ComponenteResponse(BaseModel):
    id: int
    topologia_id: int

    tipo: str

    posicion_x: float
    posicion_y: float

    potencia_tx_dbm: float | None
    clase_potencia: str | None

    longitud_km: float | None
    atenuacion_db_km: float | None

    cantidad_conectores: int | None
    cantidad_empalmes: int | None

    relacion_division: str | None

    sensibilidad_min_dbm: float | None
    potencia_sobrecarga_dbm: float | None

    class Config:
        from_attributes = True