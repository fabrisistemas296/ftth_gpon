"""
tests/test_escenario_predefinido.py

Cubre RF-22/RF-23: autocompletado de cantidad_usuarios desde un
escenario predefinido al crear una simulación.
"""


def _obtener_escenario_por_nombre(client, headers, nombre):
    r = client.get("/escenarios/", headers=headers)
    return next(e for e in r.json() if e["nombre"] == nombre)


def test_autocompleta_cantidad_usuarios_desde_escenario(client, alumno_headers):
    zona_rural = _obtener_escenario_por_nombre(client, alumno_headers, "Zona rural")

    r = client.post("/proyectos/", json={"nombre": "Test escenario"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.post("/simulaciones/", json={
        "proyecto_id": proyecto_id,
        "escenario_id": zona_rural["id"],
        "tipo_consumo": "web",
        # sin cantidad_usuarios
    }, headers=alumno_headers)

    assert r.status_code == 200
    assert r.json()["cantidad_usuarios"] == zona_rural["cantidad_usuarios_default"]


def test_valor_manual_tiene_prioridad_sobre_escenario(client, alumno_headers):
    zona_rural = _obtener_escenario_por_nombre(client, alumno_headers, "Zona rural")

    r = client.post("/proyectos/", json={"nombre": "Test escenario override"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.post("/simulaciones/", json={
        "proyecto_id": proyecto_id,
        "escenario_id": zona_rural["id"],
        "cantidad_usuarios": 15,
        "tipo_consumo": "web",
    }, headers=alumno_headers)

    assert r.status_code == 200
    assert r.json()["cantidad_usuarios"] == 15


def test_sin_escenario_ni_cantidad_usuarios_da_422(client, alumno_headers):
    r = client.post("/proyectos/", json={"nombre": "Test sin datos"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.post("/simulaciones/", json={
        "proyecto_id": proyecto_id,
        "tipo_consumo": "web",
    }, headers=alumno_headers)

    assert r.status_code == 422


def test_escenarios_visibles_para_alumno_y_profesor(client, alumno_headers, profesor_headers):
    r1 = client.get("/escenarios/", headers=alumno_headers)
    r2 = client.get("/escenarios/", headers=profesor_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(r1.json()) == 4  # los 4 escenarios seed


def test_solo_profesor_puede_editar_escenario(client, alumno_headers, profesor_headers):
    escenarios = client.get("/escenarios/", headers=alumno_headers).json()
    escenario_id = escenarios[0]["id"]

    payload = {
        "nombre": escenarios[0]["nombre"],
        "cantidad_usuarios_default": 999,
        "distancia_tipica_km": 1.0,
    }

    r_alumno = client.put(f"/escenarios/{escenario_id}", json=payload, headers=alumno_headers)
    assert r_alumno.status_code == 403

    r_profesor = client.put(f"/escenarios/{escenario_id}", json=payload, headers=profesor_headers)
    assert r_profesor.status_code == 200
    assert r_profesor.json()["cantidad_usuarios_default"] == 999
