"""
probar_autocompletado_escenario.py

Prueba puntual del autocompletado de cantidad_usuarios desde un
escenario predefinido (RF-22, RF-23).

No necesita una topología completa: crea un proyecto y prueba
directamente sobre /simulaciones/, en 3 casos:

1. Con escenario_id, SIN cantidad_usuarios -> debe autocompletar
   con el valor por defecto del escenario.
2. Con escenario_id Y cantidad_usuarios -> debe respetar el valor
   manual (el escenario no lo sobreescribe).
3. SIN escenario_id y SIN cantidad_usuarios -> debe fallar con 422.

Requiere el servidor corriendo y 'requests' instalado.
"""

import requests

BASE_URL = "http://127.0.0.1:8000"

ALUMNO = {
    "nombre": "Alumno de Prueba",
    "email": "alumno.prueba@ejemplo.com",
    "password": "prueba1234"
}


def paso(titulo: str):
    print(f"\n{'=' * 60}\n{titulo}\n{'=' * 60}")


def main():
    # Login (asume que el alumno ya existe, como en probar_motor_calculo.py)
    paso("Iniciando sesión")
    r = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ALUMNO["email"], "password": ALUMNO["password"]},
    )
    if r.status_code != 200:
        print(f"❌ No se pudo loguear: {r.status_code} - {r.text}")
        return
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login OK")

    # Obtener el escenario "Zona rural" desde el catálogo real (no hardcodeado)
    paso("Buscando el escenario 'Zona rural' en el catálogo")
    r = requests.get(f"{BASE_URL}/escenarios/", headers=headers)
    if r.status_code != 200:
        print(f"❌ No se pudo obtener el catálogo de escenarios: {r.status_code} - {r.text}")
        return

    escenarios = r.json()
    zona_rural = next((e for e in escenarios if e["nombre"] == "Zona rural"), None)
    if zona_rural is None:
        print("❌ No se encontró el escenario 'Zona rural'. ¿Se cargó el seed data?")
        print(f"   Escenarios disponibles: {[e['nombre'] for e in escenarios]}")
        return

    print(f"✅ Escenario encontrado: {zona_rural['nombre']} "
          f"(id={zona_rural['id']}, default={zona_rural['cantidad_usuarios_default']} usuarios)")

    # Crear un proyecto de prueba (crear_simulacion solo necesita que exista)
    paso("Creando proyecto de prueba")
    r = requests.post(
        f"{BASE_URL}/proyectos/",
        json={"nombre": "Proyecto - test autocompletado", "descripcion": "Test RF-22/RF-23"},
        headers=headers,
    )
    if r.status_code != 200:
        print(f"❌ No se pudo crear el proyecto: {r.status_code} - {r.text}")
        return
    proyecto_id = r.json()["id"]
    print(f"✅ Proyecto creado (id={proyecto_id})")

    # --- Caso 1: escenario_id, SIN cantidad_usuarios -> debe autocompletar ---
    paso("Caso 1: escenario_id sin cantidad_usuarios (debe autocompletar)")
    r = requests.post(
        f"{BASE_URL}/simulaciones/",
        json={
            "proyecto_id": proyecto_id,
            "escenario_id": zona_rural["id"],
            "tipo_consumo": "web"
            # sin cantidad_usuarios
        },
        headers=headers,
    )
    if r.status_code != 200:
        print(f"❌ Falló (no debería): {r.status_code} - {r.text}")
    else:
        cantidad = r.json()["cantidad_usuarios"]
        esperado = zona_rural["cantidad_usuarios_default"]
        if cantidad == esperado:
            print(f"✅ Autocompletó correctamente: cantidad_usuarios = {cantidad} (esperado: {esperado})")
        else:
            print(f"❌ Valor incorrecto: obtuvo {cantidad}, esperaba {esperado}")

    # --- Caso 2: escenario_id Y cantidad_usuarios manual -> debe respetar el manual ---
    paso("Caso 2: escenario_id CON cantidad_usuarios manual (debe respetar el valor manual)")
    r = requests.post(
        f"{BASE_URL}/simulaciones/",
        json={
            "proyecto_id": proyecto_id,
            "escenario_id": zona_rural["id"],
            "cantidad_usuarios": 15,
            "tipo_consumo": "web"
        },
        headers=headers,
    )
    if r.status_code != 200:
        print(f"❌ Falló (no debería): {r.status_code} - {r.text}")
    else:
        cantidad = r.json()["cantidad_usuarios"]
        if cantidad == 15:
            print(f"✅ Respetó el valor manual: cantidad_usuarios = {cantidad} (esperado: 15)")
        else:
            print(f"❌ Valor incorrecto: obtuvo {cantidad}, esperaba 15 (¿el escenario lo sobreescribió?)")

    # --- Caso 3: SIN escenario_id y SIN cantidad_usuarios -> debe fallar con 422 ---
    paso("Caso 3: sin escenario_id y sin cantidad_usuarios (debe fallar con 422)")
    r = requests.post(
        f"{BASE_URL}/simulaciones/",
        json={
            "proyecto_id": proyecto_id,
            "tipo_consumo": "web"
            # sin escenario_id ni cantidad_usuarios
        },
        headers=headers,
    )
    if r.status_code == 422:
        print(f"✅ Rechazó correctamente con 422: {r.json()}")
    else:
        print(f"❌ Debería haber fallado con 422, pero devolvió {r.status_code}: {r.text}")

    print("\n" + "=" * 60)
    print("PRUEBA FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
