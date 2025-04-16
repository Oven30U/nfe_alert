import os
from datetime import datetime

import pandas as pd
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from obtener_datos_clientes.db import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    cuit = Column(String(20), nullable=False)
    client_folder = Column(String(255), nullable=False)
    correo_output = Column(String(255), nullable=True)
    socio_responsable = Column(String(255), nullable=True)
    zip_password = Column(String(255), nullable=True)
    rango_consulta_dias = Column(Integer, default=7)
    # schedule = Column(String(100), nullable=True)
    dias_ejecucion = Column(String(255), nullable=True)
    documentacion = Column(Boolean, default=True)
    filtro_fce = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cliente_jurisdicciones = relationship(
        "ClienteJurisdiccion", back_populates="cliente"
    )
    usuarios_clientes = relationship("UsuarioCliente", back_populates="cliente")
    monitoreo_bots = relationship("MonitoreoBots", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente {self.nombre}>"


class Jurisdiccion(Base):
    __tablename__ = "jurisdicciones"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False)
    clase = Column(String(255), nullable=False)
    headless = Column(Boolean, default=True)
    # fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    # fecha_actualizacion = Column(
    #     DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    # )

    cliente_jurisdicciones = relationship(
        "ClienteJurisdiccion", back_populates="jurisdiccion"
    )

    def __repr__(self):
        return f"<Jurisdiccion {self.nombre}>"


class ClienteJurisdiccion(Base):
    __tablename__ = "cliente_jurisdiccion"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    jurisdiccion_id = Column(Integer, ForeignKey("jurisdicciones.id"))
    usuario = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    consultar = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    fecha_login_error = Column(DateTime(timezone=True), nullable=True)

    cliente = relationship("Cliente", back_populates="cliente_jurisdicciones")
    jurisdiccion = relationship("Jurisdiccion", back_populates="cliente_jurisdicciones")

    def __repr__(self):
        return f"<ClienteJurisdiccion {self.id}>"


class UsuariosAutorizados(Base):
    __tablename__ = "usuarios_autorizados"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False)
    fecha_autorizacion = Column(DateTime(timezone=True), nullable=True)

    usuarios_clientes = relationship("UsuarioCliente", back_populates="usuario")

    def __repr__(self):
        return f"<UsuariosAutorizados {self.username}>"


class UsuarioCliente(Base):
    __tablename__ = "usuario_cliente"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios_autorizados.id"))
    id_cliente = Column(Integer, ForeignKey("clientes.id"))

    usuario = relationship("UsuariosAutorizados", back_populates="usuarios_clientes")
    cliente = relationship("Cliente", back_populates="usuarios_clientes")

    def __repr__(self):
        return f"<UsuarioCliente {self.id}>"


class MonitoreoBots(Base):
    __tablename__ = "monitoreo_bots"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False)
    estado = Column(String(50), nullable=False)
    iniciado = Column(DateTime(timezone=True), nullable=True)
    finalizado = Column(DateTime(timezone=True), nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    id_procesamiento_diario_global = Column(
        Integer, ForeignKey("procesamientos_diarios_global.id")
    )  # Relación con procesamientos_diarios_global

    cliente = relationship("Cliente", back_populates="monitoreo_bots")
    procesamiento_global = relationship(
        "ProcesamientosDiariosGlobal", back_populates="monitoreos"
    )

    def __repr__(self):
        return f"<MonitoreoBots {self.id} - {self.cliente.nombre if self.cliente else 'No cliente'} - {self.estado}>"


class ProcesamientosDiariosGlobal(Base):
    __tablename__ = "procesamientos_diarios_global"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime(timezone=False), nullable=False)  # Removed timezone
    numero_procesamiento = Column(Integer, nullable=False)
    iniciado = Column(DateTime(timezone=False), nullable=False)  # Removed timezone
    finalizado = Column(DateTime(timezone=False), nullable=True)  # Removed timezone
    procesamiento_correcto = Column(
        Boolean, default=True
    )  # Cambiado de 'estado' a 'procesamiento_correcto'

    monitoreos = relationship(
        "MonitoreoBots", back_populates="procesamiento_global"
    )  # Relación con MonitoreoBots

    def __repr__(self):
        return f"<ProcesamientosDiariosGlobal {self.numero_procesamiento} - {self.procesamiento_correcto}>"


class ClienteProcessor:
    def __init__(
        self,
        cliente: str,
        group: pd.DataFrame,
        cuit_cliente: str,
        inicio: datetime,
        client_folder: str,
    ):
        self.cliente: str = cliente
        self.client_folder = client_folder
        self.group: pd.DataFrame = group
        self.cuit_cliente: str = cuit_cliente
        self.inicio: datetime = inicio
        self.client_folder: str = client_folder
        self.output_folder, self.backup_folder = self.preparar_directorios()
        self.correo_output: str = self.obtener_correo()
        self.socio_responsable: str = self.obtener_socio()
        self.zip_path: str = None
        self.zip_name: str = None

    def preparar_directorios(self):
        """Prepare output and backup directories for the client"""
        base_dir = self.client_folder
        output_dir = os.path.join(base_dir, "output")
        backup_dir = os.path.join(base_dir, "backup")

        # Create directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)

        return output_dir, backup_dir

    def obtener_correo(self):
        """Get email from the first row of the group DataFrame if available"""
        if not self.group.empty and "correo_output" in self.group.columns:
            return self.group.iloc[0]["correo_output"]
        return ""

    def obtener_socio(self):
        """Get responsible partner from the first row of the group DataFrame if available"""
        if not self.group.empty and "socio_responsable" in self.group.columns:
            return self.group.iloc[0]["socio_responsable"]
        return ""
