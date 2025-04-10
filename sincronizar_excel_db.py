"""
Script para sincronizar datos de los archivos Excel con la base de datos SQL Server.
Este script puede ejecutarse de forma independiente para actualizar la base de datos
con la información más reciente de los archivos Excel de configuración de clientes.
"""

import os
import sys
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import PATH_ESTRUCTURA_ROBOT
from inputs import cargar_excels
from database import get_session
from logger import Logger

# Importar los modelos correctos desde models.py
from models import Base, ClienteNFE, JurisdiccionNFE, ClienteJurisdiccionNFE

logger = Logger.get_logger()


def crear_esquema():
    """Crea las tablas en la base de datos si no existen."""
    try:
        engine = get_session().get_bind()

        # Crear solo las tablas específicas que necesitamos
        tablas = [
            ClienteNFE.__table__,
            JurisdiccionNFE.__table__,
            ClienteJurisdiccionNFE.__table__,
        ]

        Base.metadata.create_all(engine, tables=tablas)
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

    # Imprimir una muestra del DataFrame para diagnóstico
    logger.info("Muestra del DataFrame obtenido de Excel:")
    logger.info(f"Columnas disponibles: {df_clientes.columns.tolist()}")
    logger.info(f"Primeras 5 filas:\n{df_clientes.head().to_string()}")

    # Obtener sesión de base de datos
    session = get_session()

    try:
        # Procesar datos de jurisdicciones primero para tenerlas disponibles
        jurisdicciones_procesadas = {}

        # Usar el nombre de columna correcto para jurisdicciones
        jurisdiccion_columna = "Código-Jurisdicción"

        for jurisdiccion_codigo in df_clientes[jurisdiccion_columna].unique():
            jurisdiccion_db = (
                session.query(JurisdiccionNFE)
                .filter_by(codigo=jurisdiccion_codigo)
                .first()
            )

            if not jurisdiccion_db:
                # Crear nueva jurisdicción
                jurisdiccion_db = JurisdiccionNFE(
                    codigo=jurisdiccion_codigo,
                    nombre=jurisdiccion_codigo,  # Usar el código como nombre inicial
                )
                session.add(jurisdiccion_db)
                session.flush()  # Para obtener el ID
                logger.info(f"Creada nueva jurisdicción: {jurisdiccion_codigo}")

            jurisdicciones_procesadas[jurisdiccion_codigo] = jurisdiccion_db

        # Procesar datos de clientes
        clientes_procesados = []
        for client_folder, group in df_clientes.groupby("client_folder"):
            # Obtener datos del cliente
            cliente_data = group.iloc[0]

            # Buscar si el cliente ya existe
            cliente_db = (
                session.query(ClienteNFE).filter_by(client_folder=client_folder).first()
            )

            if not cliente_db:
                # Crear nuevo cliente con todos los datos disponibles
                cliente_db = ClienteNFE(
                    nombre=cliente_data["Cliente"],
                    cuit=cliente_data.get("cuit_cliente", ""),
                    client_folder=client_folder,
                    dias_ejecucion=cliente_data.get("Dia/s de ejecución", ""),
                    correo_output=cliente_data.get("Correo Output", ""),
                    socio_responsable=cliente_data.get("CC: Equipo Deloitte", ""),
                    zip_password=cliente_data.get("ZIP_Password", ""),
                    rango_consulta_dias=cliente_data.get(
                        "Rango de consulta dias anteriores", 10
                    ),
                    schedule=cliente_data.get("Schedule", "Automático"),
                )
                session.add(cliente_db)
                session.flush()  # Para obtener el ID
                logger.info(
                    f"Creado nuevo cliente: {client_folder} - {cliente_data['Cliente']}"
                )
            else:
                # Actualizar cliente existente
                cliente_db.nombre = cliente_data["Cliente"]
                if "cuit_cliente" in cliente_data:
                    cliente_db.cuit = cliente_data["cuit_cliente"]
                cliente_db.dias_ejecucion = cliente_data.get(
                    "Dia/s de ejecución", cliente_db.dias_ejecucion
                )
                cliente_db.correo_output = cliente_data.get(
                    "Correo Output", cliente_db.correo_output
                )
                cliente_db.socio_responsable = cliente_data.get(
                    "CC: Equipo Deloitte", cliente_db.socio_responsable
                )
                cliente_db.zip_password = cliente_data.get(
                    "ZIP_Password", cliente_db.zip_password
                )
                cliente_db.rango_consulta_dias = cliente_data.get(
                    "Rango de consulta dias anteriores", cliente_db.rango_consulta_dias
                )
                cliente_db.schedule = cliente_data.get("Schedule", cliente_db.schedule)
                logger.info(
                    f"Actualizado cliente existente: {client_folder} - {cliente_data['Cliente']}"
                )

            # Procesar jurisdicciones del cliente
            for _, row in group.iterrows():
                jurisdiccion_codigo = row[
                    jurisdiccion_columna
                ]  # Usar el nombre correcto de columna
                jurisdiccion_db = jurisdicciones_procesadas[jurisdiccion_codigo]

                # Buscar o crear la relación cliente-jurisdicción
                rel = (
                    session.query(ClienteJurisdiccionNFE)
                    .filter_by(
                        cliente_id=cliente_db.id, jurisdiccion_id=jurisdiccion_db.id
                    )
                    .first()
                )

                # Determinar si se debe consultar esta jurisdicción
                consultar = str(row.get("Consultar", "")).lower() == "si"

                if not rel:
                    # Nueva relación
                    rel = ClienteJurisdiccionNFE(
                        cliente_id=cliente_db.id,
                        jurisdiccion_id=jurisdiccion_db.id,
                        consultar=consultar,
                        usuario=row.get("Usuario", ""),
                        password=row.get("Password", ""),
                        fecha_desde=row.get("fecha_desde", ""),
                        fecha_hasta=row.get("fecha_hasta", ""),
                    )
                    session.add(rel)
                    logger.debug(
                        f"Creada relación cliente-jurisdicción: {client_folder} - {jurisdiccion_codigo}"
                    )
                else:
                    # Actualizar relación existente
                    rel.consultar = consultar
                    rel.usuario = row.get("Usuario", rel.usuario)
                    rel.password = row.get("Password", rel.password)
                    rel.fecha_desde = row.get("fecha_desde", rel.fecha_desde)
                    rel.fecha_hasta = row.get("fecha_hasta", rel.fecha_hasta)
                    logger.debug(
                        f"Actualizada relación cliente-jurisdicción: {client_folder} - {jurisdiccion_codigo}"
                    )

            clientes_procesados.append(client_folder)

        session.commit()
        logger.info(
            f"Sincronización completada exitosamente. {len(clientes_procesados)} clientes procesados."
        )
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Error durante la sincronización: {str(e)}")
        # Imprimir traza completa para mejor diagnóstico
        import traceback

        logger.error(traceback.format_exc())
        return False
    finally:
        session.close()


if __name__ == "__main__":
    # Crear/verificar esquema primero
    if crear_esquema():
        # Luego sincronizar datos
        sincronizar_datos_excel_db()
