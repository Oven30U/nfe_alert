from datetime import datetime, timedelta
from time import sleep
from typing import Union, List
import os

from sqlalchemy import DateTime, func
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_session, get_sqlite_session
from models import MonitoreoBotsBackup
from obtener_datos_clientes.models import (
    MonitoreoBots,
)  # Importar desde obtener_datos_clientes
from logger import Logger

# Load environment variables from .env file
load_dotenv()

# Define a constant for the sender email
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

logger = Logger.get_logger()


def transfer_records_to_sql_server(session: Session, sqlite_records):
    for record in sqlite_records:
        iniciado = (
            datetime.strptime(record[4], "%Y-%m-%d %H:%M:%S.%f") if record[4] else None
        )
        finalizado = (
            datetime.strptime(record[5], "%Y-%m-%d %H:%M:%S.%f") if record[5] else None
        )
        new_record = MonitoreoBots(
            username=record[1],
            proceso=record[2],
            estado=record[3],
            iniciado=iniciado,
            finalizado=finalizado,
            cliente=record[6],
        )
        session.add(new_record)
    session.commit()


def transfer_records_to_sqlite_backup(sqlite_session: Session, sqlite_records):
    for record in sqlite_records:
        new_record = MonitoreoBotsBackup(
            username=record[1],
            proceso=record[2],
            estado=record[3],
            iniciado=record[4],
            finalizado=record[5],
            cliente=record[6],
        )
        sqlite_session.add(new_record)
    sqlite_session.commit()


def delete_records_from_sqlite(sqlite_session: Session):
    sqlite_session.query(MonitoreoBots).delete()
    sqlite_session.commit()


def insert_record(
    session: Session,
    username: str,
    proceso: str,
    estado_value: str,
    inicio_value: datetime,
    fin_value: datetime,
    cliente: str,
):
    # Truncate microseconds to match SQL Server's DATETIME precision (milliseconds)
    if inicio_value:
        inicio_value = inicio_value.replace(microsecond=0)
    if fin_value:
        fin_value = fin_value.replace(microsecond=0)

    # Ensure string lengths do not exceed database limits
    username = username[:50]
    estado_value = estado_value[:50]
    cliente = cliente[:50]

    # Create a new MonitoreoBots record
    record = MonitoreoBots(
        username=username,
        proceso=proceso,
        estado=estado_value,
        iniciado=inicio_value,
        finalizado=fin_value,
        cliente=cliente,
    )

    # Add the record to the session
    session.add(record)


def insert_record_sqlite(
    sqlite_session: Session,
    username: str,
    proceso: str,
    estado_value: str,
    inicio_value: datetime,
    fin_value: datetime,
    cliente: str,
):
    # Truncate microseconds si es necesario
    if inicio_value:
        inicio_value = inicio_value.replace(microsecond=0)
    if fin_value:
        fin_value = fin_value.replace(microsecond=0)

    # Asegurarse de que las longitudes de las cadenas no excedan los límites de la base de datos
    username = username[:50]
    estado_value = estado_value[:50]
    cliente = cliente[:50]

    # Crear un nuevo registro en MonitoreoBotsBackup
    record = MonitoreoBotsBackup(
        username=username,
        proceso=proceso,
        estado=estado_value,
        iniciado=inicio_value,
        finalizado=fin_value,
        cliente=cliente,
    )

    # Agregar el registro a la sesión
    sqlite_session.add(record)


def insert_records_sqlite(
    sqlite_session: Session,
    username: str,
    proceso: str,
    estado_value: str,
    inicio_value: datetime,
    fin_value: datetime,
    cliente: str,
):
    # Dividir los usernames si hay múltiples separados por ";"
    usernames = username.split(";")
    for user in usernames:
        user_name = user.split("@")[0].strip()
        if user_name:
            insert_record_sqlite(
                sqlite_session,
                user_name,
                proceso,
                estado_value,
                inicio_value,
                fin_value,
                cliente,
            )
    try:
        # Confirmar la transacción
        sqlite_session.commit()
    except DBAPIError as e:
        # Revertir en caso de error
        sqlite_session.rollback()
        print(f"Error en la base de datos SQLite durante el commit: {e}")
        raise
    finally:
        # Cerrar la sesión
        sqlite_session.close()


def insert_records(
    session: Session,
    username: str,
    proceso: str,
    estado_value: str,
    inicio_value: datetime,
    fin_value: datetime,
    cliente: str,
):
    usernames = username.split(";")
    for user in usernames:
        user_name = user.split("@")[0].strip()
        if user_name:
            insert_record(
                session,
                user_name,
                proceso,
                estado_value,
                inicio_value,
                fin_value,
                cliente,
            )
    try:
        session.commit()
    except DBAPIError as e:
        session.rollback()
        print(f"Database error during commit: {e}")
        raise
    finally:
        session.close()


def conectar_db(
    proceso: str,
    cliente: str,
    username: str,
    inicio_value: datetime,
    estado_value: str,
    cliente_id: int = None,
    procesamiento_id: int = None,
) -> None:
    """
    Registra la ejecución en la base de datos SQL Server y en SQLite como respaldo.

    Args:
        proceso: Nombre del proceso ejecutado
        cliente: Nombre del cliente procesado (solo informativo)
        username: Usuario que ejecutó el proceso
        inicio_value: Fecha y hora de inicio del proceso
        estado_value: Estado final del proceso
        cliente_id: ID del cliente en la base de datos
        procesamiento_id: ID del procesamiento diario global
    """
    # Primero intentar registrar en SQL Server
    try:
        session = None
        try:
            session = get_session()
            monitoreo_bots = MonitoreoBots(
                proceso=proceso,
                username=username,
                iniciado=inicio_value,
                finalizado=datetime.now(),
                estado=estado_value,
                cliente_id=cliente_id,
                id_procesamiento_diario_global=procesamiento_id,
            )

            session.add(monitoreo_bots)
            session.commit()
            logger.info(f"Registro exitoso en SQL Server para {cliente}")

        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"Error al registrar en SQL Server para {cliente}: {str(e)}")
            raise

        finally:
            if session:
                session.close()

    except Exception:
        # Si hay error en SQL Server, registrar en SQLite como respaldo
        try:
            session = None
            try:
                session = get_sqlite_session()
                monitoreo_bots_backup = MonitoreoBotsBackup(
                    proceso=proceso,
                    cliente=cliente,  # Aquí sí puede ser string si el modelo lo permite
                    username=username,
                    iniciado=inicio_value,
                    finalizado=datetime.now(),
                    estado=estado_value,
                    cliente_id=cliente_id,
                    procesamiento_diario_global_id=procesamiento_id,
                )

                session.add(monitoreo_bots_backup)
                session.commit()
                logger.info(f"Registro respaldo exitoso en SQLite para {cliente}")

            except Exception as e:
                if session:
                    session.rollback()
                logger.error(f"Error al registrar en SQLite para {cliente}: {str(e)}")

            finally:
                if session:
                    session.close()

        except Exception as e:
            logger.error(
                f"Error general en conexión a bases de datos para {cliente}: {str(e)}"
            )


def get_clientes_ejecutados_hoy_with_retries(
    clientes_si_verificar: List[str], retries=10, delay=30
) -> List[str]:
    for attempt in range(retries):
        try:
            return get_clientes_ejecutados_hoy(clientes_si_verificar)
        except OperationalError as e:
            print(f"Intento {attempt + 1} fallido: {e}")
            if attempt < retries - 1:
                sleep(delay)
            else:
                print("Todos los intentos fallaron. Devolviendo clientes_si_verificar.")
                return clientes_si_verificar


def get_clientes_ejecutados_hoy(clientes: List[str]) -> List[str]:
    try:
        session = get_session()
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time()).replace(
            microsecond=0
        )
        end_of_day = datetime.combine(today, datetime.max.time()).replace(microsecond=0)
        proceso = os.getenv("PROYECTO")

        results = (
            session.query(MonitoreoBots.cliente)
            .filter(
                MonitoreoBots.finalizado >= start_of_day,
                MonitoreoBots.finalizado <= end_of_day,
                MonitoreoBots.proceso == proceso,
                MonitoreoBots.cliente.in_(clientes),
                MonitoreoBots.estado == "Correcto",
            )
            .group_by(MonitoreoBots.cliente)
            .all()
        )

        clientes_hoy = [row[0] for row in results]
        return [cliente for cliente in clientes if cliente not in clientes_hoy]
    except Exception as e:
        print(f"Error al obtener los clientes ejecutados hoy: {e}")
        return []
    finally:
        session.close()


def read_and_modify_html(
    cliente: str, new_pass: str, dias: int, username: str = "usuario"
) -> str:
    html_template_path = os.getenv(
        "PATH_HTML_SET_PASS", "C:/Users/lmarinaro/Documents/dfe/DFEPW/html/mail_plantilla_set_pass.html"
    )
    with open(html_template_path, "r", encoding="utf-8") as file:
        html_content = file.read()
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    html_content = html_content.replace("{{cliente}}", cliente)
    html_content = html_content.replace("{{new_pass}}", new_pass)
    html_content = html_content.replace("{{dias}}", str(dias))
    html_content = html_content.replace("{{username}}", username)
    html_content = html_content.replace("{{fecha_actual}}", fecha_actual)
    return html_content
