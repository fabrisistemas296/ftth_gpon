"""
tests/test_autorizacion.py

Cubre RF-04 a RF-06 y RNF-07: un alumno solo accede a sus propios
proyectos; un profesor puede ver (no editar) los de cualquier alumno.
"""


def test_alumno_puede_crear_proyecto(client, alumno_headers):
    r = client.post("/proyectos/", json={"nombre": "Mi proyecto"}, headers=alumno_headers)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Mi proyecto"


def test_profesor_no_puede_crear_proyecto(client, profesor_headers):
    r = client.post("/proyectos/", json={"nombre": "Proyecto de profesor"}, headers=profesor_headers)
    assert r.status_code == 403


def test_alumno_no_puede_ver_proyecto_de_otro_alumno(client, alumno_headers, otro_alumno_headers):
    r = client.post("/proyectos/", json={"nombre": "Proyecto privado"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.get(f"/proyectos/{proyecto_id}", headers=otro_alumno_headers)
    assert r.status_code == 403


def test_alumno_no_puede_editar_proyecto_ajeno(client, alumno_headers, otro_alumno_headers):
    r = client.post("/proyectos/", json={"nombre": "Proyecto privado"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.put(
        f"/proyectos/{proyecto_id}",
        json={"nombre": "Hackeado"},
        headers=otro_alumno_headers,
    )
    assert r.status_code == 403


def test_alumno_no_puede_eliminar_proyecto_ajeno(client, alumno_headers, otro_alumno_headers):
    r = client.post("/proyectos/", json={"nombre": "Proyecto privado"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.delete(f"/proyectos/{proyecto_id}", headers=otro_alumno_headers)
    assert r.status_code == 403


def test_profesor_puede_ver_proyecto_de_cualquier_alumno(client, alumno_headers, profesor_headers):
    r = client.post("/proyectos/", json={"nombre": "Proyecto del alumno"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.get(f"/proyectos/{proyecto_id}", headers=profesor_headers)
    assert r.status_code == 200


def test_profesor_no_puede_editar_proyecto_de_alumno(client, alumno_headers, profesor_headers):
    r = client.post("/proyectos/", json={"nombre": "Proyecto del alumno"}, headers=alumno_headers)
    proyecto_id = r.json()["id"]

    r = client.put(
        f"/proyectos/{proyecto_id}",
        json={"nombre": "Modificado por profesor"},
        headers=profesor_headers,
    )
    assert r.status_code == 403


def test_alumno_solo_ve_sus_propios_proyectos_en_el_listado(client, alumno_headers, otro_alumno_headers):
    client.post("/proyectos/", json={"nombre": "Proyecto A"}, headers=alumno_headers)
    client.post("/proyectos/", json={"nombre": "Proyecto B"}, headers=otro_alumno_headers)

    r = client.get("/proyectos/", headers=alumno_headers)
    assert r.status_code == 200
    nombres = [p["nombre"] for p in r.json()]
    assert "Proyecto A" in nombres
    assert "Proyecto B" not in nombres


def test_profesor_ve_todos_los_proyectos_en_el_listado(client, alumno_headers, otro_alumno_headers, profesor_headers):
    client.post("/proyectos/", json={"nombre": "Proyecto A"}, headers=alumno_headers)
    client.post("/proyectos/", json={"nombre": "Proyecto B"}, headers=otro_alumno_headers)

    r = client.get("/proyectos/", headers=profesor_headers)
    assert r.status_code == 200
    nombres = [p["nombre"] for p in r.json()]
    assert "Proyecto A" in nombres
    assert "Proyecto B" in nombres


def test_sin_token_devuelve_401(client):
    r = client.post("/proyectos/", json={"nombre": "Sin auth"})
    assert r.status_code == 401
