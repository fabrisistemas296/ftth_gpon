from typing import Literal

from pydantic import BaseModel, model_validator


# Campos propios de cada tipo de componente. Se usa para validar que
# no se llenen campos que no correspondan (ej. longitud_km en un OLT).
CAMPOS_POR_TIPO = {
    "OLT": {"potencia_tx_dbm", "clase_potencia"},
    "FIBRA": {"longitud_km", "atenuacion_db_km", "cantidad_conectores", "cantidad_empalmes"},
    "SPLITTER": {"relacion_division"},
    "ONT_ONU": {"sensibilidad_min_dbm", "potencia_sobrecarga_dbm"},
}

# Campos obligatorios (no None) para que el componente sea utilizable
# por el motor de cálculo (ver app/services/calculo_optico.py).
CAMPOS_OBLIGATORIOS_POR_TIPO = {
    "OLT": {"potencia_tx_dbm"},
    "FIBRA": {"longitud_km", "atenuacion_db_km"},
    "SPLITTER": {"relacion_division"},
    "ONT_ONU": {"sensibilidad_min_dbm", "potencia_sobrecarga_dbm"},
}

TODOS_LOS_CAMPOS_ESPECIFICOS = {
    "potencia_tx_dbm", "clase_potencia",
    "longitud_km", "atenuacion_db_km", "cantidad_conectores", "cantidad_empalmes",
    "relacion_division",
    "sensibilidad_min_dbm", "potencia_sobrecarga_dbm",
}


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

    @model_validator(mode="after")
    def _validar_campos_segun_tipo(self):
        campos_permitidos = CAMPOS_POR_TIPO[self.tipo]
        campos_obligatorios = CAMPOS_OBLIGATORIOS_POR_TIPO[self.tipo]

        # 1. Ningún campo de OTRO tipo puede venir cargado (no None)
        campos_no_permitidos_cargados = [
            campo
            for campo in TODOS_LOS_CAMPOS_ESPECIFICOS - campos_permitidos
            if getattr(self, campo) is not None
        ]
        if campos_no_permitidos_cargados:
            raise ValueError(
                f"Los siguientes campos no corresponden a un componente de tipo "
                f"'{self.tipo}' y deben quedar vacíos: {sorted(campos_no_permitidos_cargados)}"
            )

        # 2. Los campos obligatorios del tipo elegido deben estar presentes
        campos_faltantes = [
            campo for campo in campos_obligatorios
            if getattr(self, campo) is None
        ]
        if campos_faltantes:
            raise ValueError(
                f"Faltan campos obligatorios para un componente de tipo "
                f"'{self.tipo}': {sorted(campos_faltantes)}"
            )

        # 3. cantidad_conectores/cantidad_empalmes en FIBRA: si no se
        # especifican, se asumen 0 en vez de exigirlos como obligatorios
        if self.tipo == "FIBRA":
            if self.cantidad_conectores is None:
                self.cantidad_conectores = 0
            if self.cantidad_empalmes is None:
                self.cantidad_empalmes = 0

        return self


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