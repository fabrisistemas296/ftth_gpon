from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, String, text, Float
from app.database import Base

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    rol = Column(String, nullable=False)
    fecha_registro = Column(String,nullable=False,server_default=text("(datetime('now'))"))

class Proyecto(Base):
    __tablename__ = "proyecto"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    usuario_id = Column(
        Integer,
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False
    )
    fecha_creacion = Column(
        String,
        nullable=False,
        server_default=text("(datetime('now'))")
    )
    fecha_modificacion = Column(
        String,
        nullable=False,
        server_default=text("(datetime('now'))")
    )


class Topologia(Base):
    __tablename__ = "topologia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proyecto_id = Column(
        Integer,
        ForeignKey("proyecto.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )


class Componente(Base):
    __tablename__ = "componente"

    id = Column(Integer, primary_key=True, autoincrement=True)

    topologia_id = Column(
        Integer,
        ForeignKey("topologia.id", ondelete="CASCADE"),
        nullable=False
    )

    tipo = Column(String, nullable=False)

    posicion_x = Column(Float, nullable=False)
    posicion_y = Column(Float, nullable=False)

    potencia_tx_dbm = Column(Float, nullable=True)
    clase_potencia = Column(String, nullable=True)

    longitud_km = Column(Float, nullable=True)
    atenuacion_db_km = Column(Float, nullable=True)

    cantidad_conectores = Column(Integer, nullable=True)
    cantidad_empalmes = Column(Integer, nullable=True)

    relacion_division = Column(String, nullable=True)

    sensibilidad_min_dbm = Column(Float, nullable=True)
    potencia_sobrecarga_dbm = Column(Float, nullable=True)


class Conexion(Base):
    __tablename__ = "conexion"

    id = Column(Integer, primary_key=True, autoincrement=True)

    topologia_id = Column(
        Integer,
        ForeignKey("topologia.id", ondelete="CASCADE"),
        nullable=False
    )

    componente_origen_id = Column(
        Integer,
        ForeignKey("componente.id", ondelete="CASCADE"),
        nullable=False
    )

    componente_destino_id = Column(
        Integer,
        ForeignKey("componente.id", ondelete="CASCADE"),
        nullable=False
    )


class EscenarioPredefinido(Base):
    __tablename__ = "escenario_predefinido"

    id = Column(Integer, primary_key=True, autoincrement=True)

    nombre = Column(
        String,
        nullable=False,
        unique=True
    )

    cantidad_usuarios_default = Column(
        Integer,
        nullable=False
    )

    distancia_tipica_km = Column(
        Float,
        nullable=False
    )

    descripcion = Column(
        String,
        nullable=True
    )


class Simulacion(Base):
    __tablename__ = "simulacion"

    id = Column(Integer, primary_key=True, autoincrement=True)

    proyecto_id = Column(
        Integer,
        ForeignKey("proyecto.id", ondelete="CASCADE"),
        nullable=False
    )

    escenario_id = Column(
        Integer,
        ForeignKey("escenario_predefinido.id", ondelete="SET NULL"),
        nullable=True
    )

    fecha_ejecucion = Column(
        String,
        nullable=False,
        server_default=text("(datetime('now'))")
    )

    cantidad_usuarios = Column(
        Integer,
        nullable=False
    )

    tipo_consumo = Column(
        String,
        nullable=False
    )


class ResultadoOptico(Base):
    __tablename__ = "resultado_optico"

    id = Column(Integer, primary_key=True, autoincrement=True)

    simulacion_id = Column(
        Integer,
        ForeignKey("simulacion.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    perdida_total_db = Column(
        Float,
        nullable=False
    )

    potencia_recibida_dbm = Column(
        Float,
        nullable=False
    )

    estado_operativo = Column(
        String,
        nullable=False
    )


class ResultadoTrafico(Base):
    __tablename__ = "resultado_trafico"

    id = Column(Integer, primary_key=True, autoincrement=True)

    simulacion_id = Column(
        Integer,
        ForeignKey("simulacion.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    throughput_mbps = Column(
        Float,
        nullable=False
    )

    throughput_por_usuario_mbps = Column(
        Float,
        nullable=True
    )

    utilizacion_pct = Column(
        Float,
        nullable=False
    )

    congestion = Column(
        Integer,
        nullable=False
    )

    tiempo_respuesta_ms = Column(
        Float,
        nullable=True
    )