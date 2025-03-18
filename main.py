import asyncio
import os
from contextlib import contextmanager
from datetime import date, datetime

from playwright.async_api import async_playwright

from cliente_processor import ClienteProcessor
from conectar_db import conectar_db
from config import (
    jurisdiccion_clases,
)
from database import get_session, get_sqlite_session
from functions.delete_backs import delete_zip_files_in_backup
from inputs import obtener_clientes
from logger import Logger
from models import MonitoreoBots, MonitoreoBotsBackup
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
            estado = "Erróneo"  # Estado default
            inicio = datetime.now()
            df_final = None

            try:
                cuit_cliente = group["cuit_cliente"].values[0]
                client_folder = group["client_folder"].values[0]
                processor = ClienteProcessor(
                    cliente=cliente,
                    group=group,
                    cuit_cliente=cuit_cliente,
                    inicio=inicio,
                    client_folder=client_folder,
                )
                processor.respaldar_archivos()

                # Bloque específico para proceso de jurisdicciones
                try:
                    (
                        instances,
                        encontradas,
                        no_encontradas,
                        saltadas_por_dependencia,
                        login_error_nacional,
                    ) = await processor.procesar_jurisdicciones(playwright)
                    logger.info(
                        "Cliente: %s - Jurisdicciones encontradas: %s - No encontradas: %s",
                        cliente,
                        encontradas,
                        no_encontradas,
                    )
                except Exception as e:
                    logger.error("Error al procesar jurisdicciones: %s, %s", cliente, e)
                    raise

                # Bloque específico para ejecución y reintentos
                try:
                    df_final = await processor.ejecutar_jurisdicciones(
                        instances, saltadas_por_dependencia, login_error_nacional
                    )
                    df_final = await processor.reintentar_errores(playwright, df_final)
                    logger.info("Resultados para %s:\n%s", cliente, df_final)
                except Exception as e:
                    logger.error("Error al ejecutar jurisdicciones: %s, %s", cliente, e)
                    raise

                # Bloque específico para mapas y ZIP
                try:
                    processor.generar_mapas(df_final)
                    processor.crear_zip()
                except Exception as e:
                    logger.error("Error al generar archivos: %s, %s", cliente, e)
                    raise

                # Determinar estado según resultados
                estado = (
                    "Correcto"
                    if df_final["Error"].isna().all()
                    else "Proceso terminado con errores"
                )

            except Exception as e:
                logger.error(
                    "Error general en el procesamiento del cliente %s: %s", cliente, e
                )
                # Estado ya está configurado como "Erróneo" por defecto
            finally:
                # Siempre intentar enviar correo y registrar, incluso con errores
                if df_final is not None:
                    try:
                        if (
                            (~df_final["Notificacion"].isin(["Hay notificaciones", "No hay notificaciones"]) | 
                            df_final["Notificacion"].isna())
                            .sum() > 0
                            or df_final["Screenshot"]
                            .str.contains(
                                r"No se realizó Screenshot", case=False, na=False
                            )
                            .sum() > 0
                        ):
                            logger.info("Hubo un error o falta de screenshot")

                        correo_exitoso = processor.enviar_email(df_final)
                        if not correo_exitoso:
                            estado = "Correo no enviado"
                    except Exception as email_error:
                        logger.error("Error al enviar correo: %s", email_error)
                        estado = "Correo no enviado"

                try:
                    processor.registrar_ejecucion(
                        proceso=os.getenv("PROYECTO"),
                        inicio=inicio,
                        estado=estado,
                    )
                except Exception as reg_error:
                    logger.error("Error al registrar ejecución: %s", reg_error)

        delete_zip_files_in_backup(os.getenv("PATH_ESTRUCTURA_ROBOT"))


def obtener_datos_clientes():
    df_clientes = obtener_clientes(
        jurisdiccion_clases=jurisdiccion_clases,
    )

    return df_clientes


def get_clientes_procesados_hoy() -> set[str]:
    """
    Obtiene el conjunto de clientes que ya fueron procesados correctamente hoy.

    Returns:
        set[str]: Conjunto de nombres de clientes procesados exitosamente en el día actual.
    """
    today: date = date.today()
    clientes_procesados: set[str] = set()

    try:
        # Consultar en SQL Server
        with managed_session("sqlserver") as sqlserver_session:
            clientes_sqlserver = (
                sqlserver_session.query(MonitoreoBots.cliente)
                .filter(
                    MonitoreoBots.estado == "Correcto",
                    MonitoreoBots.proceso == os.getenv("Proyecto", "NFE Alert"),
                    MonitoreoBots.iniciado
                    >= datetime.combine(today, datetime.min.time()),
                    MonitoreoBots.iniciado
                    <= datetime.combine(today, datetime.max.time()),
                )
                .all()
            )
            clientes_procesados.update(cliente[0] for cliente in clientes_sqlserver)

        # Consultar en SQLite
        with managed_session("sqlite") as sqlite_session:
            clientes_sqlite = (
                sqlite_session.query(MonitoreoBotsBackup.cliente)
                .filter(
                    MonitoreoBotsBackup.estado == "Correcto",
                    MonitoreoBotsBackup.proceso == os.getenv("Proyecto", "NFE Alert"),
                    MonitoreoBotsBackup.iniciado
                    >= datetime.combine(today, datetime.min.time()),
                    MonitoreoBotsBackup.iniciado
                    <= datetime.combine(today, datetime.max.time()),
                )
                .all()
            )
            clientes_procesados.update(cliente[0] for cliente in clientes_sqlite)

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
