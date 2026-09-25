from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./ftth_gpon"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# --------------------------------------------------------------
# Activar PRAGMA foreign_keys = ON en cada conexión.
# SQLite lo tiene deshabilitado por defecto; sin esto, las
# ForeignKey(..., ondelete="CASCADE"/"SET NULL") definidas en los
# modelos NO se respetan en tiempo de ejecución.
# --------------------------------------------------------------
@event.listens_for(engine, "connect")
def _habilitar_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base única del proyecto. Los modelos (app/models/models.py) deben
# importar este mismo Base, no redefinirlo.
Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()