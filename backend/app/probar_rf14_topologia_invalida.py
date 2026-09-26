"""
probar_rf14_topologia_invalida.py

Prueba el RF-14 (detección de errores de diseño en la red) contra
varios casos de topología inválida:

1. Topología sin ninguna OLT.
2. Topología con dos OLT (debería tener exactamente una).
3. Topología con OLT pero sin ninguna ONT/ONU.
4. Topología con una ONT/ONU que no está conectada a la OLT.
5. Intento de crear un splitter con relación de división no soportada
   (bloqueado a nivel de schema, antes de llegar al motor de cálculo).

En cada caso se espera un error 422 con un mensaje descriptivo, NUNCA
un 500 (que indicaría una excepción no controlada) ni un 200 (que
indicaría que el sistema no detectó el problema).

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


def esperar_error(response: requests.Response, status_esperado: int, descripcion: str):
    if response.status_code == status_esperado:
        print(f"✅ {descripcion} -> {response.status_code} (esperado)")
        print(f"   Detalle: {response.json()}")
    else:
        print(f"❌ {descripcion} -> {response.status_code} (se esperaba {status_esperado})")
        print(f"   Body: {response.text}")


def login() -> dict:
    r = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ALUMNO["email"], "password": ALUMNO["password"]},
    )
    if r.status_code != 200:
        raise SystemExit(f"No se pudo loguear: {r.status_code} - {r.text}")
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def crear_proyecto_y_topologia(headers: dict, nombre: str) -> tuple[int, int]:
    r = requests.post(
        f"{BASE_URL}/proyectos/",
        json={"nombre": nombre, "descripcion": "Test RF-14"},
        headers=headers,
    )
    proyecto_id = r.json()["id"]

    r = requests.post(
        f"{BASE_URL}/topologias/",
        json={"proyecto_id": proyecto_id},
        headers=headers,
    )
    topologia_id = r.json()["id"]

    return proyecto_id, topologia_id


def crear_componente(headers: dict, topologia_id: int, **kwargs) -> dict:
    payload = {"topologia_id": topologia_id, "posicion_x": 0, "posicion_y": 0, **kwargs}
    r = requests.post(f"{BASE_URL}/componentes/", json=payload, headers=headers)
    if r.status_code != 200:
        print(f"   ⚠️  No se pudo crear componente {kwargs.get('tipo')}: {r.status_code} - {r.text}")
        return {}
    return r.json()


def crear_simulacion_y_calcular(headers: dict, proyecto_id: int) -> requests.Response:
    r = requests.post(
        f"{BASE_URL}/simulaciones/",
        json={
            "proyecto_id": proyecto_id,
            "cantidad_usuarios": 10,
            "tipo_consumo": "web"
        },
        headers=headers,
    )
    simulacion_id = r.json()["id"]
    return requests.post(f"{BASE_URL}/simulaciones/{simulacion_id}/calcular", headers=headers)


def main():
    paso("Login")
    headers = login()
    print("✅ Login OK")

    # ------------------------------------------------------------------
    # Caso 1: topología sin ninguna OLT (solo una ONT suelta)
    # ------------------------------------------------------------------
    paso("Caso 1: topología sin OLT")
    proyecto_id, topologia_id = crear_proyecto_y_topologia(headers, "Test - sin OLT")
    crear_componente(
        headers, topologia_id,
        tipo="ONT_ONU", sensibilidad_min_dbm=-32.0, potencia_sobrecarga_dbm=-8.0
    )
    r = crear_simulacion_y_calcular(headers, proyecto_id)
    esperar_error(r, 422, "Sin OLT")

    # ------------------------------------------------------------------
    # Caso 2: topología con DOS OLT
    # ------------------------------------------------------------------
    paso("Caso 2: topología con dos OLT")
    proyecto_id, topologia_id = crear_proyecto_y_topologia(headers, "Test - dos OLT")
    crear_componente(headers, topologia_id, tipo="OLT", potencia_tx_dbm=5.0, clase_potencia="C+")
    crear_componente(headers, topologia_id, tipo="OLT", potencia_tx_dbm=5.0, clase_potencia="C+")
    crear_componente(
        headers, topologia_id,
        tipo="ONT_ONU", sensibilidad_min_dbm=-32.0, potencia_sobrecarga_dbm=-8.0
    )
    r = crear_simulacion_y_calcular(headers, proyecto_id)
    esperar_error(r, 422, "Dos OLT")

    # ------------------------------------------------------------------
    # Caso 3: topología con OLT pero sin ninguna ONT/ONU
    # ------------------------------------------------------------------
    paso("Caso 3: topología sin ninguna ONT/ONU")
    proyecto_id, topologia_id = crear_proyecto_y_topologia(headers, "Test - sin ONT")
    crear_componente(headers, topologia_id, tipo="OLT", potencia_tx_dbm=5.0, clase_potencia="C+")
    r = crear_simulacion_y_calcular(headers, proyecto_id)
    esperar_error(r, 422, "Sin ONT/ONU")

    # ------------------------------------------------------------------
    # Caso 4: OLT y ONT existen, pero NO están conectadas entre sí
    # ------------------------------------------------------------------
    paso("Caso 4: ONT/ONU no conectada a la OLT")
    proyecto_id, topologia_id = crear_proyecto_y_topologia(headers, "Test - ONT desconectada")
    crear_componente(headers, topologia_id, tipo="OLT", potencia_tx_dbm=5.0, clase_potencia="C+")
    crear_componente(
        headers, topologia_id,
        tipo="ONT_ONU", sensibilidad_min_dbm=-32.0, potencia_sobrecarga_dbm=-8.0
    )
    # A propósito, no se crea ninguna conexión entre ellas
    r = crear_simulacion_y_calcular(headers, proyecto_id)
    esperar_error(r, 422, "ONT desconectada de la OLT")

    # ------------------------------------------------------------------
    # Caso 5: splitter con relación de división no soportada
    # (debe rechazarse a nivel de schema, antes de llegar al motor)
    # ------------------------------------------------------------------
    paso("Caso 5: splitter con relación de división no soportada (ej. '1:128')")
    _, topologia_id = crear_proyecto_y_topologia(headers, "Test - splitter inválido")
    r = requests.post(
        f"{BASE_URL}/componentes/",
        json={
            "topologia_id": topologia_id,
            "tipo": "SPLITTER",
            "posicion_x": 0, "posicion_y": 0,
            "relacion_division": "1:128"  # no está en la lista soportada
        },
        headers=headers,
    )
    esperar_error(r, 422, "Splitter con relación no soportada")

    print("\n" + "=" * 60)
    print("PRUEBA RF-14 FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
