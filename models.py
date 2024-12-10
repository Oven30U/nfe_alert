from sqlalchemy import Column, SmallInteger, String, DateTime, ForeignKey, Text
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
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    proceso = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    iniciado = Column(DateTime, nullable=True)
    finalizado = Column(DateTime, nullable=True)
    cliente = Column(String, nullable=False)


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
