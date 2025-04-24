import asyncio
import os
from contextlib import contextmanager
from datetime import date, datetime

import pandas as pd
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
from obtener_datos_clientes.db import SessionLocal
from obtener_datos_clientes.obtener_datos_clientes import (
    Cliente,
    ObtenerDatosClientes,
    ProcesamientoGlobalManager,
)

logger = Logger.get_logger()


async def main():
    # Registrar procesamiento global y obtener su ID
    procesamiento_global = ProcesamientoGlobalManager.registrar_procesamiento()
    procesamiento_id = procesamiento_global.id if procesamiento_global else None

    # Obtener el número de procesamientos diarios máximo de las variables de entorno
    PROCESAMIENTOS_DIARIOS = int(os.getenv("PROCESAMIENTOS_DIARIOS", 3))

    async with async_playwright() as playwright:
        df_input = obtener_datos_clientes()
        if df_input.empty:
            logger.info("No se encontraron clientes para procesar.")
            registrar_sin_clientes(procesamiento_id)
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

                # Obtener el ID del cliente desde la base de datos si está disponible
                cliente_id = None
                if os.getenv("INPUT_DATA_FROM_DB").lower() == "true":
                    with SessionLocal() as db:
                        cliente_record = (
                            db.query(Cliente)
                            .filter(Cliente.client_folder == client_folder)
                            .first()
                        )
                        if cliente_record:
                            cliente_id = cliente_record.id

                processor = ClienteProcessor(
                    cliente=cliente,
                    group=group,
                    cuit_cliente=cuit_cliente,
                    inicio=inicio,
                    client_folder=client_folder,
                    cliente_id=cliente_id,
                    procesamiento_id=procesamiento_id,
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
                    df_final = processor.sort_df_final(df_final)
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
                # Verificar si necesitamos modificar los destinatarios del correo basado en el estado y número de procesamiento
                if (
                    estado != "Correcto"
                    and procesamiento_global
                    and procesamiento_global.numero_procesamiento
                    < PROCESAMIENTOS_DIARIOS
                ):
                    logger.info(
                        f"Modificando destinatarios del correo para {cliente} debido a estado '{estado}' en procesamiento {procesamiento_global.numero_procesamiento}"
                    )
                    processor.socio_responsable = os.getenv(
                        "CORREO_NOTIFICACION_ERROR", "rpa-tax-ar@deloitte.com"
                    )
                    processor.correo_output = ""

                # Siempre intentar enviar correo y registrar, incluso con errores
                if df_final is not None:
                    try:
                        if (
                            ~df_final["Notificacion"].isin(
                                ["Hay notificaciones", "No hay notificaciones"]
                            )
                            | df_final["Notificacion"].isna()
                        ).sum() > 0 or df_final["Screenshot"].str.contains(
                            r"No se realizó Screenshot", case=False, na=False
                        ).sum() > 0:
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

        # Al finalizar, actualizar el estado del procesamiento global
        if procesamiento_global:
            ProcesamientoGlobalManager.finalizar_procesamiento(
                procesamiento_global, True
            )

        delete_zip_files_in_backup(os.getenv("PATH_ESTRUCTURA_ROBOT"))


def obtener_datos_clientes() -> pd.DataFrame:
    """
    Obtiene los datos de clientes desde la base de datos o archivo de configuración.

    En modo desarrollo (DEV_MODE=true), redirige todos los correos al correo de prueba
    configurado en CORREO_RECEPTOR_TEST_MAIL.

    Returns:
        pd.DataFrame: DataFrame con la información de clientes y jurisdicciones a procesar
    """
    # Obtener datos según la fuente configurada
    if os.getenv("INPUT_DATA_FROM_DB", "false").lower() == "true":
        obtener_datos = ObtenerDatosClientes()
        obtener_datos.run()

        # Aplicar modificaciones si estamos en modo desarrollo
        if os.getenv("DEV_MODE", "false").lower() == "true":
            logger.info(
                "Ejecutando en modo desarrollo - Redirigiendo correos al correo de prueba"
            )
            test_email = os.getenv("CORREO_RECEPTOR_TEST_MAIL")

            # Verificar que el correo de prueba esté configurado
            if not test_email:
                logger.warning(
                    "CORREO_RECEPTOR_TEST_MAIL no está configurado. No se modificarán los correos."
                )
            else:
                # Reemplazar correos de destino por el correo de prueba
                if "CC: Equipo Deloitte" in obtener_datos.data.columns:
                    obtener_datos.data["CC: Equipo Deloitte"] = test_email
                    logger.info(
                        f"Correos CC: Equipo Deloitte redirigidos a {test_email}"
                    )

                # Vaciar los correos de salida primarios
                if "Correo Output" in obtener_datos.data.columns:
                    obtener_datos.data["Correo Output"] = ""
                    logger.info("Correos de salida (Correo Output) vaciados")

        return obtener_datos.data
    else:
        df_clientes = obtener_clientes(
            jurisdiccion_clases=jurisdiccion_clases,
        )

        # Aplicar modificaciones si estamos en modo desarrollo
        if os.getenv("DEV_MODE", "false").lower() == "true":
            logger.info(
                "Ejecutando en modo desarrollo - Redirigiendo correos al correo de prueba"
            )
            test_email = os.getenv("CORREO_RECEPTOR_TEST_MAIL")

            # Verificar que el correo de prueba esté configurado
            if not test_email:
                logger.warning(
                    "CORREO_RECEPTOR_TEST_MAIL no está configurado. No se modificarán los correos."
                )
            else:
                # Reemplazar correos de destino según el formato usado en inputs.obtener_clientes
                if "CC: Equipo Deloitte" in df_clientes.columns:
                    df_clientes["CC: Equipo Deloitte"] = test_email
                    logger.info(
                        f"Correos CC: Equipo Deloitte redirigidos a {test_email}"
                    )

                if "Correo Output" in df_clientes.columns:
                    df_clientes["Correo Output"] = ""
                    logger.info("Correos de salida (Correo Output) vaciados")

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


def registrar_sin_clientes(procesamiento_id=None):
    """
    Cuando no hay clientes para procesar, simplemente finaliza el procesamiento global
    sin crear registros en monitoreo_bots.

    Args:
        procesamiento_id: ID del procesamiento global que debe finalizarse
    """
    logger.info("No hay clientes para procesar hoy. Finalizando procesamiento global.")

    if procesamiento_id:
        # Buscar el procesamiento global correspondiente y marcarlo como finalizado
        try:
            ProcesamientoGlobalManager.finalizar_procesamiento_sin_clientes(
                procesamiento_id
            )
            logger.info(
                f"Procesamiento global {procesamiento_id} finalizado correctamente sin clientes."
            )
        except Exception as e:
            logger.error(
                f"Error al finalizar procesamiento global {procesamiento_id}: {str(e)}"
            )
    else:
        logger.warning(
            "No se pudo finalizar el procesamiento global: ID no proporcionado"
        )


if __name__ == "__main__":
    asyncio.run(main())
