from pydantic import BaseModel, EmailStr
from typing import Literal


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    rol: Literal["alumno", "profesor"]


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioResponse(UsuarioBase):
    id: int
    fecha_registro: str

    class Config:
        from_attributes = True