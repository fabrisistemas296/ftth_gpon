# Registro de comandos de consola

Este archivo documenta los comandos usados o necesarios para trabajar con el backend.

## Comando registrado

| Comando | Para que sirve |
| --- | --- |
| `pip install sqlalchemy` | Instala SQLAlchemy, una libreria de Python para trabajar con bases de datos mediante un mapeo objeto-relacional (ORM). |

## Comandos habituales del proyecto

Estos comandos son utiles para preparar y ejecutar la API, aunque no forman parte del historial confirmado anterior.

| Comando | Para que sirve |
| --- | --- |
| `python -m venv .venv` | Crea un entorno virtual llamado `.venv` para aislar las dependencias del proyecto. |
| `.\.venv\Scripts\Activate.ps1` | Activa el entorno virtual en PowerShell. |
| `pip install fastapi uvicorn pydantic sqlalchemy` | Instala las dependencias principales de la API. |
| `uvicorn main:app --reload` | Inicia el servidor FastAPI usando el objeto `app` de `main.py` y reinicia el servidor al detectar cambios. |
| `deactivate` | Sale del entorno virtual activo. |

## Notas

- Los comandos deben ejecutarse desde la carpeta `backend`.
- La API queda disponible normalmente en `http://127.0.0.1:8000`.
- La documentacion interactiva de FastAPI se encuentra en `http://127.0.0.1:8000/docs` mientras el servidor esta activo.