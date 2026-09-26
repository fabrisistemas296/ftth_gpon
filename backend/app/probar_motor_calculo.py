"""
probar_motor_calculo.py

Script de prueba end-to-end para el Simulador FTTH-GPON.

Hace, en orden, contra la API corriendo en http://127.0.0.1:8000:
1. Registra un alumno de prueba (o usa uno existente si ya está registrado).
2. Inicia sesión y obtiene el token.
3. Crea un proyecto.
4. Crea su topología.
5. Crea los 4 componentes (OLT, Fibra, Splitter, ONT/ONU) del ejemplo
   validado en el punto 1.3 del informe.
6. Conecta los componentes en cadena.
7. Crea una simulación de tráfico.
8. Ejecuta POST /simulaciones/{id}/calcular y muestra el resultado.

Requiere el servidor corriendo (uvicorn app.main:app --reload) y la
librería 'requests' instalada:
    pip install requests
"""

import requests

BASE_URL = "http://127.0.0.1:8000"

# Datos del alumno de prueba. Si ya lo registraste antes, el script
# detecta el error de email duplicado y sigue con el login igual.
ALUMNO = {
    "nombre": "Alumno de Prueba",
    "email": "alumno.prueba@ejemplo.com",
    "password": "prueba1234"
}


def paso(titulo: str):
    print(f"\n{'=' * 60}\n{titulo}\n{'=' * 60}")


def verificar(response: requests.Response, descripcion: str):
    if response.status_code >= 400:
        print(f"❌ Error en: {descripcion}")
        print(f"   Status: {response.status_code}")
        print(f"   Detalle: {response.text}")
        raise SystemExit(1)
    print(f"✅ {descripcion} -> {response.status_code}")
    return response.json()


def main():
    # 1. Registrar alumno (si ya existe, seguimos igual)
    paso("1. Registrando alumno de prueba")
    r = requests.post(f"{BASE_URL}/usuarios/", json=ALUMNO)
    if r.status_code == 400:
        print("ℹ️  El usuario ya existía, seguimos con el login.")
    else:
        verificar(r, "Alumno registrado")

    # 2. Login
    paso("2. Iniciando sesión")
    r = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ALUMNO["email"], "password": ALUMNO["password"]},
    )
    datos_login = verificar(r, "Login exitoso")
    token = datos_login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Crear proyecto
    paso("3. Creando proyecto")
    r = requests.post(
        f"{BASE_URL}/proyectos/",
        json={"nombre": "Proyecto de prueba - motor de cálculo", "descripcion": "Test automático"},
        headers=headers,
    )
    proyecto = verificar(r, "Proyecto creado")
    proyecto_id = proyecto["id"]
    print(f"   proyecto_id = {proyecto_id}")

    # 4. Crear topología
    paso("4. Creando topología")
    r = requests.post(
        f"{BASE_URL}/topologias/",
        json={"proyecto_id": proyecto_id},
        headers=headers,
    )
    topologia = verificar(r, "Topología creada")
    topologia_id = topologia["id"]
    print(f"   topologia_id = {topologia_id}")

    # 5. Crear componentes (mismo escenario validado en el punto 1.3)
    paso("5. Creando componentes (OLT, Fibra, Splitter, ONT/ONU)")

    r = requests.post(
        f"{BASE_URL}/componentes/",
        json={
            "topologia_id": topologia_id,
            "tipo": "OLT",
            "posicion_x": 0, "posicion_y": 0,
            "potencia_tx_dbm": 5.0,
            "clase_potencia": "C+"
        },
        headers=headers,
    )
    olt = verificar(r, "OLT creada")

    r = requests.post(
        f"{BASE_URL}/componentes/",
        json={
            "topologia_id": topologia_id,
            "tipo": "FIBRA",
            "posicion_x": 100, "posicion_y": 0,
            "longitud_km": 8.0,
            "atenuacion_db_km": 0.28,
            "cantidad_conectores": 3,
            "cantidad_empalmes": 2
        },
        headers=headers,
    )
    fibra = verificar(r, "Fibra creada")

    r = requests.post(
        f"{BASE_URL}/componentes/",
        json={
            "topologia_id": topologia_id,
            "tipo": "SPLITTER",
            "posicion_x": 200, "posicion_y": 0,
            "relacion_division": "1:32"
        },
        headers=headers,
    )
    splitter = verificar(r, "Splitter creado")

    r = requests.post(
        f"{BASE_URL}/componentes/",
        json={
            "topologia_id": topologia_id,
            "tipo": "ONT_ONU",
            "posicion_x": 300, "posicion_y": 0,
            "sensibilidad_min_dbm": -32.0,
            "potencia_sobrecarga_dbm": -8.0
        },
        headers=headers,
    )
    ont = verificar(r, "ONT/ONU creada")

    # 6. Conectar en cadena: OLT -> Fibra -> Splitter -> ONT
    paso("6. Conectando componentes")

    for origen, destino, nombre in [
        (olt, fibra, "OLT -> Fibra"),
        (fibra, splitter, "Fibra -> Splitter"),
        (splitter, ont, "Splitter -> ONT"),
    ]:
        r = requests.post(
            f"{BASE_URL}/conexiones/",
            json={
                "topologia_id": topologia_id,
                "componente_origen_id": origen["id"],
                "componente_destino_id": destino["id"],
            },
            headers=headers,
        )
        verificar(r, f"Conexión {nombre}")

    # 7. Crear simulación
    paso("7. Creando simulación (32 usuarios, streaming)")
    r = requests.post(
        f"{BASE_URL}/simulaciones/",
        json={
            "proyecto_id": proyecto_id,
            "escenario_id": None,
            "cantidad_usuarios": 32, #Si no pongo valor se pone uno automatico
            "tipo_consumo": "streaming"
        },
        headers=headers,
    )
    simulacion = verificar(r, "Simulación creada")
    simulacion_id = simulacion["id"]
    print(f"   simulacion_id = {simulacion_id}")

    # 8. Ejecutar el cálculo
    paso("8. Ejecutando el motor de cálculo")
    r = requests.post(
        f"{BASE_URL}/simulaciones/{simulacion_id}/calcular",
        headers=headers,
    )
    resultado = verificar(r, "Cálculo ejecutado")

    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    print("\nResultado óptico:")
    for clave, valor in resultado["resultado_optico"].items():
        print(f"  {clave}: {valor}")

    print("\nResultado de tráfico:")
    for clave, valor in resultado["resultado_trafico"].items():
        print(f"  {clave}: {valor}")

    print("\n--- Valores esperados (según el ejemplo validado en el 1.3) ---")
    print("  perdida_total_db      ≈ 21.14")
    print("  potencia_recibida_dbm ≈ -16.14")
    print("  estado_operativo      = operativo")
    print("  throughput_mbps       = 480.0")
    print("  utilizacion_pct       ≈ 19.29")
    print("  congestion            = False")


if __name__ == "__main__":
    main()
