from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class MonitoreoBots(Base):
    __tablename__ = "monitoreo_bots"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    proceso = Column(Text, nullable=False)
    estado = Column(String(50), nullable=False)
    iniciado = Column(DateTime, nullable=True)
    finalizado = Column(DateTime, nullable=True)
    cliente = Column(String(50), nullable=False)


class MonitoreoBotsBackup(Base):
    __tablename__ = "monitoreo_bots_backup"

    id = Column(Integer, primary_key=True, index=True)
    proceso = Column(String(255), nullable=False)
    cliente = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    estado = Column(String(50), nullable=False)
    iniciado = Column(DateTime, nullable=True)
    finalizado = Column(DateTime, nullable=True)
    cliente_id = Column(Integer, nullable=True)  # Nuevo campo
    procesamiento_diario_global_id = Column(Integer, nullable=True)  # Nuevo campo


class UsuarioAutorizado(Base):
    __tablename__ = "usuarios_autorizados"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    fecha_autorizacion = Column(DateTime, nullable=True)


class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    pass_ = Column(String, nullable=False, name="pass")
    fecha_actualizacion_pass = Column(DateTime, nullable=True)
    fecha_vencimiento_pass = Column(DateTime, nullable=True)


class UsuarioCliente(Base):
    __tablename__ = "usuario_cliente"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    id_cliente = Column(SmallInteger, ForeignKey("clientes.id"), nullable=False)
    id_usuario = Column(
        SmallInteger, ForeignKey("usuarios_autorizados.id"), nullable=False
    )
    cliente = relationship("Cliente")
    usuario = relationship("UsuarioAutorizado")


# MODELOS CORREGIDOS PARA NFE


class ClienteNFE(Base):
    __tablename__ = "Clientes"

    id = Column("ClienteID", Integer, primary_key=True, autoincrement=True)
    nombre = Column("Nombre", String(255), nullable=False)
    cuit = Column("CUIT", String(20), nullable=False)
    client_folder = Column("ClientFolder", String(255), nullable=False)
    correo_output = Column("CorreoOutput", String(255))
    socio_responsable = Column("CCEquipoDeloitte", String(255))
    zip_password = Column("ZIPPassword", String(255))
    rango_consulta_dias = Column("RangoConsultaDiasAnteriores", Integer, default=7)
    schedule = Column("Schedule", String(100))
    dias_ejecucion = Column("DiasEjecucion", String(255))
    fecha_creacion = Column("FechaCreacion", DateTime, default=func.now())
    fecha_actualizacion = Column(
        "FechaActualizacion", DateTime, default=func.now(), onupdate=func.now()
    )

    # Relación bidireccional con ClienteJurisdiccionNFE
    cliente_jurisdicciones = relationship(
        "ClienteJurisdiccionNFE", back_populates="cliente"
    )


class JurisdiccionNFE(Base):
    __tablename__ = "Jurisdicciones"

    id = Column("JurisdiccionID", Integer, primary_key=True, autoincrement=True)
    codigo = Column("Codigo", String(50), nullable=False)
    nombre = Column("Nombre", String(255), nullable=False)
    fecha_creacion = Column("FechaCreacion", DateTime, default=func.now())
    fecha_actualizacion = Column(
        "FechaActualizacion", DateTime, default=func.now(), onupdate=func.now()
    )

    # Relación bidireccional con ClienteJurisdiccionNFE
    cliente_jurisdicciones = relationship(
        "ClienteJurisdiccionNFE", back_populates="jurisdiccion"
    )


class ClienteJurisdiccionNFE(Base):
    __tablename__ = "ClienteJurisdiccion"

    id = Column("ClienteJurisdiccionID", Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(
        "ClienteID", Integer, ForeignKey("Clientes.ClienteID"), nullable=False
    )
    jurisdiccion_id = Column(
        "JurisdiccionID",
        Integer,
        ForeignKey("Jurisdicciones.JurisdiccionID"),
        nullable=False,
    )
    usuario = Column("Usuario", String(255))
    password = Column("Password", String(255))
    consultar = Column("Consultar", Boolean, default=True)
    fecha_desde = Column(
        String(50), nullable=True
    )  # Añadido para fechas personalizadas
    fecha_hasta = Column(
        String(50), nullable=True
    )  # Añadido para fechas personalizadas
    fecha_creacion = Column("FechaCreacion", DateTime, default=func.now())
    fecha_actualizacion = Column(
        "FechaActualizacion", DateTime, default=func.now(), onupdate=func.now()
    )

    # Relaciones bidireccionales correctas
    cliente = relationship("ClienteNFE", back_populates="cliente_jurisdicciones")
    jurisdiccion = relationship(
        "JurisdiccionNFE", back_populates="cliente_jurisdicciones"
    )
