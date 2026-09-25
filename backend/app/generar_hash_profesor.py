"""
generar_hash_profesor.py

Script standalone para generar el hash bcrypt de una contraseña,
sin depender del resto del proyecto FastAPI.

Uso:
    python generar_hash_profesor.py

Te va a pedir la contraseña que quieras usar para el usuario profesor
y te va a imprimir el UPDATE listo para pegar en DBeaver.
"""

from passlib.context import CryptContext
import getpass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    password = getpass.getpass("Contraseña para el usuario profesor: ")
    confirmacion = getpass.getpass("Repetí la contraseña: ")

    if password != confirmacion:
        print("\n❌ Las contraseñas no coinciden. Corré el script de nuevo.")
        return

    hash_generado = pwd_context.hash(password)

    print("\n✅ Hash generado correctamente.\n")
    print("Copiá y ejecutá esto en DBeaver (Execute SQL Statement):\n")
    print(
        f"UPDATE usuario SET password_hash = '{hash_generado}' "
        f"WHERE email = 'hector.correa@docentes.frm.utn.edu.ar';"
    )
    print()


if __name__ == "__main__":
    main()