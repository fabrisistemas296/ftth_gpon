"""
cargar_escenarios.py

Carga el catálogo de escenarios predefinidos (RF-22 / RF-23) en la base de
datos. La API no expone un endpoint para crearlos, así que se insertan con
este script. Ejecutarlo UNA vez desde la carpeta del backend:

    python cargar_escenarios.py

Si un escenario ya existe (mismo nombre), no se duplica.

IMPORTANTE: los valores son ilustrativos. Definan los definitivos con los
tutores y modifíquenlos acá (o después, con PUT /escenarios/{id} como profesor).

Supone que app/database.py define `SessionLocal` (la fábrica de sesiones).
Si en su proyecto tiene otro nombre, ajustá el import.
"""

from app.database import SessionLocal
from app.models.models import EscenarioPredefinido

ESCENARIOS = [
    ("Barrio urbano", 150, 2.0, "Zona residencial densa con distancias cortas a la central."),
    ("Zona rural", 40, 15.0, "Baja densidad de usuarios y tramos troncales largos."),
    ("Campus universitario", 300, 1.0, "Alta densidad de usuarios en edificios cercanos."),
    ("Operador FTTH", 64, 5.0, "Despliegue típico de un operador con splitters 1:64."),
]


def main():
    db = SessionLocal()
    try:
        creados = 0
        for nombre, usuarios, distancia, descripcion in ESCENARIOS:
            if db.query(EscenarioPredefinido).filter_by(nombre=nombre).first():
                print(f"Ya existe: {nombre}")
                continue
            db.add(EscenarioPredefinido(
                nombre=nombre,
                cantidad_usuarios_default=usuarios,
                distancia_tipica_km=distancia,
                descripcion=descripcion,
            ))
            creados += 1
            print(f"Creado: {nombre}")
        db.commit()
        print(f"Listo: {creados} escenario(s) nuevo(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
