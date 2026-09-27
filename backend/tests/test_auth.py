"""
tests/test_auth.py

Cubre RF-01 a RF-03 y RNF-08/RNF-09: registro, asignación forzada de
rol, login, y que las contraseñas nunca queden en texto plano.
"""


def test_registro_asigna_rol_alumno_automaticamente(client):
    r = client.post("/usuarios/", json={
        "nombre": "Nuevo Alumno",
        "email": "nuevo@ejemplo.com",
        "password": "clave1234",
    })
    assert r.status_code == 200
    assert r.json()["rol"] == "alumno"


def test_registro_ignora_intento_de_mandar_rol_profesor(client):
    """
    El schema UsuarioCreate no tiene campo 'rol'; si el cliente lo manda
    igual, Pydantic lo ignora (extra field) y el backend fuerza 'alumno'.
    """
    r = client.post("/usuarios/", json={
        "nombre": "Intento Colado",
        "email": "intento@ejemplo.com",
        "password": "clave1234",
        "rol": "profesor",  # no debería tener efecto
    })
    assert r.status_code == 200
    assert r.json()["rol"] == "alumno"


def test_registro_rechaza_email_duplicado(client):
    payload = {"nombre": "Test", "email": "duplicado@ejemplo.com", "password": "clave1234"}
    r1 = client.post("/usuarios/", json=payload)
    r2 = client.post("/usuarios/", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 400


def test_login_correcto_devuelve_token(client):
    client.post("/usuarios/", json={
        "nombre": "Login Test", "email": "login@ejemplo.com", "password": "clave1234"
    })
    r = client.post("/auth/login", data={"username": "login@ejemplo.com", "password": "clave1234"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["rol"] == "alumno"


def test_login_password_incorrecta_devuelve_401(client):
    client.post("/usuarios/", json={
        "nombre": "Login Test", "email": "login2@ejemplo.com", "password": "clave1234"
    })
    r = client.post("/auth/login", data={"username": "login2@ejemplo.com", "password": "otra_clave"})
    assert r.status_code == 401


def test_login_email_inexistente_devuelve_401(client):
    r = client.post("/auth/login", data={"username": "no.existe@ejemplo.com", "password": "cualquiera"})
    assert r.status_code == 401


def test_password_no_se_guarda_en_texto_plano(client, db_session):
    from app.models.models import Usuario

    client.post("/usuarios/", json={
        "nombre": "Seguridad Test", "email": "seguridad@ejemplo.com", "password": "mi_clave_secreta"
    })

    usuario = db_session.query(Usuario).filter(Usuario.email == "seguridad@ejemplo.com").first()
    assert usuario is not None
    assert usuario.password_hash != "mi_clave_secreta"
    assert usuario.password_hash.startswith("$2b$")  # formato bcrypt
