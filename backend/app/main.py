"""
app/main.py

Punto de entrada de la aplicación FastAPI.
Registra todos los routers del sistema.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auth,
    usuario,
    proyecto,
    topologia,
    componente,
    conexion,
    escenario_predefinido,
    simulacion,
    resultado_optico,
    resultado_trafico,
)

app = FastAPI(
    title="Simulador Didáctico de Redes FTTH-GPON",
    description="API del simulador didáctico de redes FTTH basado en tecnología GPON.",
    version="0.1.0",
)

# CORS: permite que el frontend de prueba (servido en otro origen,
# ej. file:// o http://127.0.0.1:5500) pueda llamar a esta API.
# Para desarrollo se permite cualquier origen; en producción conviene
# restringir allow_origins a los dominios reales del frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# El router de auth debe registrarse para que exista POST /auth/login,
# usado por OAuth2PasswordBearer en app/core/deps.py
app.include_router(auth.router)
app.include_router(usuario.router)
app.include_router(proyecto.router)
app.include_router(topologia.router)
app.include_router(componente.router)
app.include_router(conexion.router)
app.include_router(escenario_predefinido.router)
app.include_router(simulacion.router)
app.include_router(resultado_optico.router)
app.include_router(resultado_trafico.router)


@app.get("/")
def root():
    return {"mensaje": "API del Simulador Didáctico de Redes FTTH-GPON"}