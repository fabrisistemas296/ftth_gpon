from pydantic import BaseModel, EmailStr
from typing import Literal


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr


class UsuarioCreate(UsuarioBase):
    password: str
    # Sin campo 'rol': se asigna "alumno" en el servidor (ver router).
    # El rol "profesor" solo se crea directamente en la base de datos.


class UsuarioResponse(UsuarioBase):
    id: int
    rol: Literal["alumno", "profesor"]
    fecha_registro: str

    class Config:
        from_attributes = True