import asyncio
import os
from contextlib import contextmanager
from datetime import date, datetime

from playwright.async_api import async_playwright

from cliente_processor import ClienteProcessor
from conectar_db import conectar_db
from config import jurisdiccion_clases
from database import get_session, get_sqlite_session
from functions.delete_backs import delete_zip_files_in_backup
from inputs import obtener_clientes
from logger import Logger
from models import MonitoreoBots, MonitoreoBotsBackup

logger = Logger.get_logger()


async def main():
    async with async_playwright() as playwright:
        df_input = obtener_datos_clientes()
        if df_input.empty:
            logger.info("No se encontraron clientes para procesar.")
            registrar_sin_clientes()
            return

        df_por_cliente = df_input.groupby("Cliente")

        for cliente, group in df_por_cliente:
            inicio = datetime.now()
            processor = ClienteProcessor(cliente, group)
            processor.respaldar_archivos()

            try:
                (
                    instances,
                    encontradas,
                    no_encontradas,
                ) = await processor.procesar_jurisdicciones(playwright)

                logger.info(
                    "Cliente: %s - Jurisdicciones encontradas: %s - Jurisdicciones no encontradas: %s",
                    cliente, encontradas, no_encontradas
                )

                df_final = await processor.ejecutar_jurisdicciones(instances)
                df_final = await processor.reintentar_errores(playwright, df_final)

                logger.info("Resultados para %s:\n%s", cliente, df_final)

                processor.generar_mapas(df_final)
                processor.zip_path, processor.zip_name = processor.crear_zip()

                estado = (
                    "Correcto"
                    if df_final["Error"].isna().all()
                    else "Proceso terminado con errores"
                )
            except Exception:
                logger.error("Error en el procesamiento del cliente %s", cliente)
                estado = "Erróneo"
            finally:
                correo_exitoso = processor.enviar_email(df_final)
                if not correo_exitoso:
                    estado = "Correo no enviado"
                processor.registrar_ejecucion(
                    proceso=os.getenv("PROYECTO"),
                    inicio=inicio,
                    estado=estado,
                )

        delete_zip_files_in_backup(os.getenv("PATH_ESTRUCTURA_ROBOT"))


def obtener_datos_clientes():
    df_clientes = obtener_clientes(
        jurisdiccion_clases=jurisdiccion_clases,
    )

    clientes_procesados_hoy = get_clientes_procesados_hoy()

    if not df_clientes.empty and clientes_procesados_hoy:
        df_clientes = df_clientes[~df_clientes["Cliente"].isin(clientes_procesados_hoy)]

    return df_clientes


def get_clientes_procesados_hoy(db_type="sqlite"):
    today = date.today()
    clientes_procesados = []

    try:
        with managed_session(db_type) as session:
            clientes_correctos = (
                session.query(MonitoreoBots.cliente)
                .filter(
                    MonitoreoBots.estado == "Correcto",
                    MonitoreoBots.iniciado
                    >= datetime.combine(today, datetime.min.time()),
                    MonitoreoBots.iniciado
                    <= datetime.combine(today, datetime.max.time()),
                )
                .union(
                    session.query(MonitoreoBotsBackup.cliente).filter(
                        MonitoreoBotsBackup.estado == "Correcto",
                        MonitoreoBotsBackup.iniciado
                        >= datetime.combine(today, datetime.min.time()),
                        MonitoreoBotsBackup.iniciado
                        <= datetime.combine(today, datetime.max.time()),
                    )
                )
                .all()
            )

            clientes_procesados = [cliente[0] for cliente in clientes_correctos]
    except Exception:
        logger.error("Error al obtener clientes procesados hoy")

    return clientes_procesados


@contextmanager
def managed_session(db_type="sqlserver"):
    session = None
    try:
        if db_type == "sqlserver":
            session = get_session()
        elif db_type == "sqlite":
            session = get_sqlite_session()
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.error("Error para obtener una sesión de sql's en main.")
        raise
    finally:
        if session:
            session.close()


def registrar_sin_clientes():
    proceso = "Revision de Domicilios Fiscales Electronicos"
    cliente = "TaxTech"
    username = "TaxTech"
    estado_value = "Correcto"
    inicio_value = datetime.now()

    conectar_db(
        proceso=proceso,
        cliente=cliente,
        username=username,
        inicio_value=inicio_value,
        estado_value=estado_value,
    )


if __name__ == "__main__":
    asyncio.run(main())
