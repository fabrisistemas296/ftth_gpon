from fastapi import FastAPI, Depends

from app.database import Base, engine, get_db
from app.routers import usuario, proyecto, topologia, componente, conexion, escenario_predefinido,simulacion, resultado_optico, resultado_trafico 
from app.routers import auth
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Network Designer API",
    description="API para diseñar redes visualmente",
    version="1.0.0"
)

#Rutas
app.include_router(usuario.router)
app.include_router(proyecto.router)
app.include_router(topologia.router)
app.include_router(componente.router)
app.include_router(conexion.router)
app.include_router(escenario_predefinido.router)
app.include_router(simulacion.router)
app.include_router(resultado_optico.router)
app.include_router(resultado_trafico.router)
app.include_router(auth.router)