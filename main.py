import asyncio
import os
from contextlib import contextmanager
from datetime import date, datetime

from playwright.async_api import async_playwright

from cliente_processor import ClienteProcessor
from conectar_db import conectar_db
from config import (
    jurisdiccion_clases,
    EJECUTAR_CLIENTES_LISTA,
    CLIENTES_CON_DOCUMENTACION,
)
from database import get_session, get_sqlite_session
from functions.delete_backs import delete_zip_files_in_backup
from inputs import obtener_clientes
from logger import Logger
from models import MonitoreoBots, MonitoreoBotsBackup #??? No tengo esta db
import pandas as pd

logger = Logger.get_logger()


async def main():
    async with async_playwright() as playwright:
        df_input = obtener_datos_clientes()
        if df_input.empty:
            logger.info("No se encontraron clientes para procesar.")
            registrar_sin_clientes()
            return

        df_por_cliente = df_input.groupby(["client_folder", "Cliente"])

        for cliente_tuple, group in df_por_cliente:
            cliente = cliente_tuple[0]
            cuit_cliente = group["cuit_cliente"].values[0]
            client_folder = group["client_folder"].values[0]
            inicio = datetime.now()
            processor = ClienteProcessor(
                cliente=cliente,
                group=group,
                cuit_cliente=cuit_cliente,
                inicio=inicio,
                client_folder=client_folder,
            )

            processor.respaldar_archivos()

            try:
                (
                    instances,
                    encontradas,
                    no_encontradas,
                ) = await processor.procesar_jurisdicciones(playwright)

                logger.info(
                    "Cliente: %s - Jurisdicciones encontradas: %s - Jurisdicciones no encontradas: %s",
                    cliente,
                    encontradas,
                    no_encontradas,
                )

                #! Esto en el caso de que Agip esté caída
                bloq = False
                # if 'Agip' in instances:
                #     print("Esta agip, borrandola...")
                #     del instances['Agip']
                #     bloq = True

                df_final: pd.DataFrame = await processor.ejecutar_jurisdicciones(instances)
                df_final = await processor.reintentar_errores(playwright, df_final)

                if bloq:
                    print("Agregar AGIP !!!!!")

                logger.info("Resultados para %s:\n%s", cliente, df_final)

                processor.generar_mapas(df_final)
                processor.crear_zip()

                estado = (
                    "Correcto"
                    if df_final["Error"].isna().all()
                    else "Proceso terminado con errores"
                )
            except Exception as e:
                logger.error("Error en el procesamiento del cliente %s, %s", cliente, e)
                estado = "Erróneo"
            finally:
                if (
                    df_final["Notificacion"]
                    .str.contains(r"error", case=False, na=False)
                    .sum()
                    > 0
                    or df_final["Screenshot"]
                    .str.contains(r"No se realizó Screenshot", case=False, na=False)
                    .sum()
                    > 0
                ):
                    logger.info("Hubo un error o falta de screenshot")
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

    if not df_clientes.empty and not EJECUTAR_CLIENTES_LISTA:
        df_clientes = df_clientes.loc[
            ~df_clientes["client_folder"].isin(clientes_procesados_hoy)
            & df_clientes["client_folder"].isin(
                CLIENTES_CON_DOCUMENTACION
            )  # ToDo: Activar a partir del viernes 7-2-25
        ]
    
    return df_clientes


def get_clientes_procesados_hoy(db_type="sqlserver"):
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
                ) #ToDo - Comentado porque no tengo esa tabla, descomentar luego
                # .union(
                #     session.query(MonitoreoBotsBackup.cliente).filter(
                #         MonitoreoBotsBackup.estado == "Correcto",
                #         MonitoreoBotsBackup.iniciado
                #         >= datetime.combine(today, datetime.min.time()),
                #         MonitoreoBotsBackup.iniciado
                #         <= datetime.combine(today, datetime.max.time()),
                #     )
                # )
                .all()
            )

            clientes_procesados = [cliente[0] for cliente in clientes_correctos]
    except Exception as e:
        logger.error(f"Error al obtener clientes procesados hoy. Detalle: {e}")

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
