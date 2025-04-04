"""
Script para sincronizar datos de los archivos Excel con la base de datos SQL Server.
Este script puede ejecutarse de forma independiente para actualizar la base de datos
con la información más reciente de los archivos Excel de configuración de clientes.
"""
import os
import sys
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from config import PATH_ESTRUCTURA_ROBOT
from inputs import cargar_excels
from database import get_session
from logger import Logger
from models import Base

logger = Logger.get_logger()

# Definir modelos específicos para las tablas que almacenarán los datos de Excel
# Si estos modelos ya existen en models.py, puedes importarlos en lugar de redefinirlos
class ClienteDFE(Base):
    __tablename__ = 'clientes_dfe'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    client_folder = Column(String(255), nullable=False, unique=True)
    cuit = Column(String(20), nullable=False)
    correo_output = Column(String(255))
    correo_destinatarios = Column(String(255))
    socio_responsable = Column(String(255))
    rango_consulta_dias = Column(Integer)
    schedule = Column(String(50))
    dias_ejecucion = Column(String(100))
    fecha_actualizacion = Column(DateTime, default=datetime.now)
    
    jurisdicciones = relationship("ClienteJurisdiccionDFE", back_populates="cliente")

class JurisdiccionDFE(Base):
    __tablename__ = 'jurisdicciones_dfe'
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    
    clientes = relationship("ClienteJurisdiccionDFE", back_populates="jurisdiccion")

class ClienteJurisdiccionDFE(Base):
    __tablename__ = 'cliente_jurisdiccion_dfe'
    
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes_dfe.id'))
    jurisdiccion_id = Column(Integer, ForeignKey('jurisdicciones_dfe.id'))
    consultar = Column(Boolean, default=True)
    usuario = Column(String(100))
    password = Column(String(100))
    fecha_desde = Column(String(10))
    fecha_hasta = Column(String(10))
    
    cliente = relationship("ClienteDFE", back_populates="jurisdicciones")
    jurisdiccion = relationship("JurisdiccionDFE", back_populates="clientes")

def crear_esquema():
    """Crea las tablas en la base de datos si no existen."""
    try:
        engine = get_session().get_bind()
        Base.metadata.create_all(engine)
        logger.info("Esquema de base de datos verificado/creado correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error al crear el esquema de la base de datos: {e}")
        return False

def sincronizar_datos_excel_db():
    """
    Lee los datos de los archivos Excel y los sincroniza con la base de datos.
    Si el cliente/jurisdicción ya existe, actualiza sus datos.
    Si no existe, crea un nuevo registro.
    """
    logger.info("Iniciando sincronización de datos Excel a base de datos")
    
    # Cargar datos desde Excel utilizando la función existente
    df_clientes = cargar_excels()
    
    if df_clientes.empty:
        logger.warning("No se encontraron datos en los archivos Excel para sincronizar")
        return False
    
    # Obtener sesión de base de datos
    session = get_session()
    
    try:
        # Procesar datos de jurisdicciones primero para tenerlas disponibles
        jurisdicciones_procesadas = {}
        for jurisdiccion_codigo in df_clientes['Jurisdiccion'].unique():
            jurisdiccion_db = session.query(JurisdiccionDFE).filter_by(codigo=jurisdiccion_codigo).first()
            
            if not jurisdiccion_db:
                # Crear nueva jurisdicción
                jurisdiccion_db = JurisdiccionDFE(
                    codigo=jurisdiccion_codigo,
                    nombre=jurisdiccion_codigo
                )
                session.add(jurisdiccion_db)
                session.flush()  # Para obtener el ID
            
            jurisdicciones_procesadas[jurisdiccion_codigo] = jurisdiccion_db
        
        # Procesar datos de clientes
        clientes_procesados = []
        for client_folder, group in df_clientes.groupby('client_folder'):
            # Obtener datos del cliente
            cliente_data = group.iloc[0]
            
            # Buscar si el cliente ya existe
            cliente_db = session.query(ClienteDFE).filter_by(client_folder=client_folder).first()
            
            if not cliente_db:
                # Crear nuevo cliente
                cliente_db = ClienteDFE(
                    nombre=cliente_data['Cliente'],
                    client_folder=client_folder,
                    cuit=cliente_data['cuit_cliente'],
                    correo_output=cliente_data.get('Correo Output', None),
                    correo_destinatarios=cliente_data.get('Correos destinatarios', None),
                    socio_responsable=cliente_data.get('CC: Equipo Deloitte', None),
                    rango_consulta_dias=cliente_data.get('Rango de consulta dias anteriores', 10),
                    schedule=cliente_data.get('Schedule', 'Automático'),
                    dias_ejecucion=cliente_data.get('Dia/s de ejecución', '')
                )
                session.add(cliente_db)
                session.flush()  # Para obtener el ID
                logger.info(f"Creado nuevo cliente: {client_folder}")
            else:
                # Actualizar cliente existente
                cliente_db.nombre = cliente_data['Cliente']
                cliente_db.cuit = cliente_data['cuit_cliente']
                cliente_db.correo_output = cliente_data.get('Correo Output', cliente_db.correo_output)
                cliente_db.correo_destinatarios = cliente_data.get('Correos destinatarios', cliente_db.correo_destinatarios)
                cliente_db.socio_responsable = cliente_data.get('CC: Equipo Deloitte', cliente_db.socio_responsable)
                cliente_db.rango_consulta_dias = cliente_data.get('Rango de consulta dias anteriores', cliente_db.rango_consulta_dias)
                cliente_db.schedule = cliente_data.get('Schedule', cliente_db.schedule)
                cliente_db.dias_ejecucion = cliente_data.get('Dia/s de ejecución', cliente_db.dias_ejecucion)
                cliente_db.fecha_actualizacion = datetime.now()
                logger.info(f"Actualizado cliente existente: {client_folder}")
            
            # Procesar jurisdicciones del cliente
            for _, row in group.iterrows():
                jurisdiccion_codigo = row['Jurisdiccion']
                jurisdiccion_db = jurisdicciones_procesadas[jurisdiccion_codigo]
                
                # Buscar o crear la relación cliente-jurisdicción
                rel = session.query(ClienteJurisdiccionDFE).filter_by(
                    cliente_id=cliente_db.id,
                    jurisdiccion_id=jurisdiccion_db.id
                ).first()
                
                # Determinar si se debe consultar esta jurisdicción
                consultar = row.get('Consultar', '').lower() == 'si'
                
                if not rel:
                    # Nueva relación
                    rel = ClienteJurisdiccionDFE(
                        cliente_id=cliente_db.id,
                        jurisdiccion_id=jurisdiccion_db.id,
                        consultar=consultar,
                        usuario=row.get('Usuario', ''),
                        password=row.get('Password', ''),
                        fecha_desde=row.get('fecha_desde', ''),
                        fecha_hasta=row.get('fecha_hasta', '')
                    )
                    session.add(rel)
                    logger.debug(f"Creada relación cliente-jurisdicción: {client_folder} - {jurisdiccion_codigo}")
                else:
                    # Actualizar relación existente
                    rel.consultar = consultar
                    rel.usuario = row.get('Usuario', rel.usuario)
                    rel.password = row.get('Password', rel.password)
                    rel.fecha_desde = row.get('fecha_desde', rel.fecha_desde)
                    rel.fecha_hasta = row.get('fecha_hasta', rel.fecha_hasta)
                    logger.debug(f"Actualizada relación cliente-jurisdicción: {client_folder} - {jurisdiccion_codigo}")
            
            clientes_procesados.append(client_folder)
        
        session.commit()
        logger.info(f"Sincronización completada exitosamente. {len(clientes_procesados)} clientes procesados.")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Error durante la sincronización: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    # Crear/verificar esquema primero
    if crear_esquema():
        # Luego sincronizar datos
        sincronizar_datos_excel_db()