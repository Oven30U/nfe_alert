from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class MonitoreoBots(Base):
    __tablename__ = 'monitoreo_bots'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    proceso = Column(String)
    estado = Column(String)
    iniciado = Column(DateTime)
    finalizado = Column(DateTime)
    cliente = Column(String)

class UsuarioAutorizado(Base):
    __tablename__ = 'usuarios_autorizados'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    fecha_autorizacion = Column(DateTime)

class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    pass_ = Column(String, name='pass')
    fecha_actualizacion_pass = Column(DateTime)

class UsuarioCliente(Base):
    __tablename__ = 'usuario_cliente'
    id = Column(Integer, primary_key=True)
    id_cliente = Column(Integer, ForeignKey('clientes.id'))
    id_usuario = Column(Integer, ForeignKey('usuarios_autorizados.id'))
    cliente = relationship('Cliente')
    usuario = relationship('UsuarioAutorizado')