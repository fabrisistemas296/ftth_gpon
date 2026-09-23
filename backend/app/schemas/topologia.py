from pydantic import BaseModel


class TopologiaCreate(BaseModel):
    proyecto_id: int


class TopologiaResponse(BaseModel):
    id: int
    proyecto_id: int

    class Config:
        from_attributes = True