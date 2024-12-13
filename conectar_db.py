from datetime import datetime, timedelta
from time import sleep
from typing import Union, List
import os
import random
import string

from sqlalchemy import DateTime, func
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from config import PATH_HTML_SET_PASS, DIAS_VIGENCIA_PASS_ZIP, CORREO_NOTIFICACION_ERROR
from database import get_session, get_sqlite_session
from pruebas.correo_cli import send_email_smtp
from models import MonitoreoBots, MonitoreoBotsBackup, UsuarioAutorizado, Cliente, UsuarioCliente

# Load environment variables from .env file
load_dotenv()

# Define a constant for the sender email
SENDER_EMAIL = os.getenv("SENDER_EMAIL")


def transfer_records_to_sql_server(session: Session, sqlite_records):
    for record in sqlite_records:
        iniciado = datetime.strptime(record[4], "%Y-%m-%d %H:%M:%S.%f") if record[4] else None
        finalizado = datetime.strptime(record[5], "%Y-%m-%d %H:%M:%S.%f") if record[5] else None
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


def insert_record(session: Session, username: str, proceso: str, estado_value: str, inicio_value: datetime, fin_value: datetime, cliente: str):
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
    cliente: str
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
    cliente: str
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
                cliente
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

def insert_records(session: Session, username: str, proceso: str, estado_value: str, inicio_value: datetime, fin_value: datetime, cliente: str):
    usernames = username.split(";")
    for user in usernames:
        user_name = user.split("@")[0].strip()
        if user_name:
            insert_record(session, user_name, proceso, estado_value, inicio_value, fin_value, cliente)
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
    username: str = os.getlogin(),
    inicio_value: datetime = datetime.now(),
    estado_value: str = "Correcto"
):
    session = None
    sqlite_session = None
    fin_value = datetime.now()
    
    try:
        session = get_session()
    except Exception as e:
        print(f"Error al conectar con la base de datos SQL Server: {e}")
    
    try:
        sqlite_session = get_sqlite_session()
    except Exception as e:
        print(f"Error al conectar con la base de datos SQLite: {e}")
    
    if session:
        insert_records(
            session,
            username,
            proceso,
            estado_value,
            inicio_value,
            fin_value,
            cliente
        )
    
    if sqlite_session:
        insert_records_sqlite(
            sqlite_session,
            username,
            proceso,
            estado_value,
            inicio_value,
            fin_value,
            cliente
        )


def get_ultimo_finalizado(cliente):
    try:
        session = get_session()
        result = session.query(MonitoreoBots.finalizado).filter(
            MonitoreoBots.proceso == 'Revision de Domicilios Fiscales Electronicos',
            MonitoreoBots.cliente == cliente,
            MonitoreoBots.estado == 'Correcto'
        ).order_by(MonitoreoBots.id.desc()).first()
        return result[0] if result else None
    except Exception as e:
        print(f"Error al obtener el último 'finalizado': {e}")
        return None
    finally:
        session.close()


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
        start_of_day = datetime.combine(today, datetime.min.time()).replace(microsecond=0)
        end_of_day = datetime.combine(today, datetime.max.time()).replace(microsecond=0)
        proceso = os.getenv("PROYECTO")

        results = session.query(MonitoreoBots.cliente).filter(
            MonitoreoBots.finalizado >= start_of_day,
            MonitoreoBots.finalizado <= end_of_day,
            MonitoreoBots.proceso == proceso,
            MonitoreoBots.cliente.in_(clientes),
            MonitoreoBots.estado == 'Correcto'
        ).group_by(MonitoreoBots.cliente).all()

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
    html_template_path = PATH_HTML_SET_PASS
    with open(html_template_path, "r", encoding="utf-8") as file:
        html_content = file.read()
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    html_content = html_content.replace("{{cliente}}", cliente)
    html_content = html_content.replace("{{new_pass}}", new_pass)
    html_content = html_content.replace("{{dias}}", str(dias))
    html_content = html_content.replace("{{username}}", username)
    html_content = html_content.replace("{{fecha_actual}}", fecha_actual)
    return html_content


def verify_and_add_users(correo_output: List[str]):
    try:
        session = get_sqlite_session()

        if isinstance(correo_output, str):
            correo_output = correo_output.split(";")

        usernames = [email for email in correo_output]

        existing_users = session.query(UsuarioAutorizado.username).filter(
            UsuarioAutorizado.username.in_(usernames)
        ).all()
        existing_users = {user[0] for user in existing_users}

        missing_users = [user for user in usernames if user not in existing_users]
        fecha_autorizacion = datetime.now()
        for user in missing_users:
            new_user = UsuarioAutorizado(username=user, fecha_autorizacion=fecha_autorizacion)
            session.add(new_user)
        session.commit()
        return existing_users, missing_users
    except Exception as e:
        print(f"Error al verificar y actualizar usuarios: {e}")
        return None, None
    finally:
        session.close()


def get_usernames(correo_output):
    if isinstance(correo_output, str):
        correo_output = correo_output.split(";")
    return [email for email in correo_output]


def get_autorizados(session: Session, usernames):
    return session.query(UsuarioAutorizado).filter(
        UsuarioAutorizado.username.in_(usernames)
    ).all()


def get_fecha_actualizacion_pass(session: Session, cliente_id):
    result = session.query(Cliente.fecha_actualizacion_pass).filter(
        Cliente.id == cliente_id
    ).first()
    return result[0] if result else None


def calculate_dias(fecha_actualizacion_pass):
    if fecha_actualizacion_pass:
        diferencia_dias = (datetime.now() - fecha_actualizacion_pass).days
        return DIAS_VIGENCIA_PASS_ZIP - diferencia_dias if diferencia_dias <= DIAS_VIGENCIA_PASS_ZIP else DIAS_VIGENCIA_PASS_ZIP
    return DIAS_VIGENCIA_PASS_ZIP


def insert_usuario_cliente(session: Session, cliente_id, usuario_id):
    relationship = UsuarioCliente(
        id_cliente=cliente_id,
        id_usuario=usuario_id
    )
    session.add(relationship)


def send_notification_email(username, cliente, new_pass, dias):
    return send_email_smtp(
        sender_email=SENDER_EMAIL,
        receiver_emails=[username],
        subject=f"Actualización de clave de seguridad para NFE Alert: Revisión de Domicilios Fiscales Electrónicos - {cliente}",
        html_file_path=None,
        zip_file_paths=None,
        html_content=read_and_modify_html(cliente, new_pass, dias, username),
    )


def verify_and_add_user_client_relationship(
        cliente_id: int, correo_output: List[str], cliente: str, new_pass: str
) -> tuple:
    session = None
    try:
        session = get_sqlite_session()
        usernames = get_usernames(correo_output)
        usuarios_autorizados = get_autorizados(session, usernames)
        usuarios_ids = {user.username: user.id for user in usuarios_autorizados}
        fecha_actualizacion_pass = get_fecha_actualizacion_pass(session, cliente_id)
        dias = calculate_dias(fecha_actualizacion_pass)

        inserted_users = []
        all_successful_emails = []
        all_failed_emails = []
        for username in usernames:
            usuario_id = usuarios_ids.get(username)
            if usuario_id:
                exists = session.query(UsuarioCliente).filter_by(
                    id_cliente=cliente_id, id_usuario=usuario_id
                ).count()
                if exists == 0:
                    insert_usuario_cliente(session, cliente_id, usuario_id)
                    inserted_users.append(username)
                    successful_emails, failed_emails = send_notification_email(
                        username, cliente, new_pass, dias
                    )
                    all_successful_emails.extend(successful_emails)
                    all_failed_emails.extend(failed_emails)
                    if failed_emails:
                        send_email_smtp(
                            sender_email=SENDER_EMAIL,
                            receiver_emails=[CORREO_NOTIFICACION_ERROR],
                            subject=f"Failed emails: {', '.join(failed_emails)}",
                            html_file_path=None,
                            zip_file_paths=None,
                            html_content="Some emails failed to send. Please check the details."
                        )
        session.commit()
        return usuarios_autorizados, dias, inserted_users, all_successful_emails, all_failed_emails
    except Exception as e:
        print(f"Error al verificar y agregar relación usuario-cliente: {e}")
        return {}, 0, [], [], []
    finally:
        if session:
            session.close()


def verify_and_delete_user_client_relationship(cliente_id: int, correo_output: List[str]) -> List[str]:
    session = None
    try:
        session = get_sqlite_session()

        if isinstance(correo_output, str):
            correo_output = correo_output.split(";")

        usernames = [email for email in correo_output]

        usuarios_autorizados = session.query(UsuarioAutorizado).filter(
            UsuarioAutorizado.username.in_(usernames)
        ).all()
        usuarios_ids = {user.username: user.id for user in usuarios_autorizados}

        relationships = session.query(UsuarioCliente).filter(
            UsuarioCliente.id_cliente == cliente_id
        ).all()
        usuarios_cliente_ids = {rel.id_usuario for rel in relationships}
        usuarios_actuales_ids = set(usuarios_ids.values())

        usuarios_a_eliminar = usuarios_cliente_ids - usuarios_actuales_ids

        deleted_users = []
        for usuario_id in usuarios_a_eliminar:
            session.query(UsuarioCliente).filter_by(
                id_cliente=cliente_id, id_usuario=usuario_id
            ).delete()
            usuario_eliminado = session.query(UsuarioAutorizado.username).filter(
                UsuarioAutorizado.id == usuario_id
            ).first()
            deleted_users.append(usuario_eliminado[0] if usuario_eliminado else None)
        session.commit()
        return deleted_users
    except Exception as e:
        print(f"Error al verificar y eliminar relación usuario-cliente: {e}")
        return []
    finally:
        if session:
            session.close()


def set_pass(cliente: str, correo_output: List[str]) -> str:
    new_pass = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    fecha_actualizacion = datetime.now()
    fecha_vencimiento = fecha_actualizacion + timedelta(days=90)
    correo_output = [correo_output] if isinstance(correo_output, str) else correo_output
    try:
        session = get_sqlite_session()
        cliente = cliente[:255]
        new_pass = new_pass[:12]

        cliente_obj = session.query(Cliente).filter_by(nombre=cliente).first()
        if cliente_obj:
            cliente_obj.pass_ = new_pass
            cliente_obj.fecha_actualizacion_pass = fecha_actualizacion
            cliente_obj.fecha_vencimiento_pass = fecha_vencimiento
        else:
            cliente_obj = Cliente(
                nombre=cliente,
                pass_=new_pass,
                fecha_actualizacion_pass=fecha_actualizacion,
                fecha_vencimiento_pass=fecha_vencimiento
            )
            session.add(cliente_obj)

        session.commit()

        cliente_id = cliente_obj.id

        existing_users, missing_users = verify_and_add_users(correo_output)

        usuarios_autorizados, dias, inserted_users, all_successful_emails, all_failed_emails = verify_and_add_user_client_relationship(
            cliente_id, correo_output, cliente, new_pass
        )

        deleted_usuario_cliente_relationship = verify_and_delete_user_client_relationship(
            cliente_id, correo_output
        )

        return new_pass
    except Exception as e:
        print(f"Error al actualizar la contraseña: {e}")
        return None
    finally:
        session.close()


def get_related_users_emails(cliente_id: int) -> List[str]:
    try:
        session = get_sqlite_session()
        results = session.query(UsuarioAutorizado.username).join(
            UsuarioCliente, UsuarioCliente.id_usuario == UsuarioAutorizado.id
        ).filter(UsuarioCliente.id_cliente == cliente_id).all()
        return [row[0] for row in results]
    except Exception as e:
        print(f"Error al obtener los correos de los usuarios relacionados: {e}")
        return []
    finally:
        session.close()


def get_pass_zip(
        cliente: str, correo_output: Union[str, List[str]] = ["lmarinaro@deloitte.com"]
) -> str:
    correo_output = [correo for correo in
                     (correo_output if isinstance(correo_output, list) else correo_output.split(";")) if
                     correo and correo.lower() != "nan"]

    try:
        session = get_sqlite_session()
        cliente = cliente[:255]

        cliente_obj = session.query(Cliente).filter_by(nombre=cliente).order_by(Cliente.id.desc()).first()
        if cliente_obj:
            pass_value = cliente_obj.pass_
            fecha_actualizacion_pass = cliente_obj.fecha_actualizacion_pass
            if fecha_actualizacion_pass:
                dias_transcurridos = (datetime.now() - fecha_actualizacion_pass).days
                dias_vigencia_actuales_pass = DIAS_VIGENCIA_PASS_ZIP - dias_transcurridos

                if dias_vigencia_actuales_pass > 0:
                    cliente_id = cliente_obj.id

                    existing_users, missing_users = verify_and_add_users(correo_output)

                    usuarios_autorizados, dias, inserted_users, all_successful_emails, all_failed_emails = verify_and_add_user_client_relationship(
                        cliente_id, correo_output, cliente, pass_value
                    )

                    deleted_usuario_cliente_relationship = verify_and_delete_user_client_relationship(
                        cliente_id, correo_output
                    )

                    return pass_value
                else:
                    cliente_id = cliente_obj.id

                    related_emails = get_related_users_emails(cliente_id)

                    pass_value = set_pass(cliente, correo_output)

                    successful_emails, failed_emails = send_email_smtp(
                        sender_email=SENDER_EMAIL,
                        receiver_emails=related_emails,
                        subject=f"Actualización de clave de seguridad para NFE Alert: Revisión de Domicilios Fiscales Electrónicos - {cliente}",
                        html_file_path=None,
                        zip_file_paths=None,
                        html_content=read_and_modify_html(
                            cliente, pass_value, DIAS_VIGENCIA_PASS_ZIP
                        ),
                    )

                    return pass_value
            else:
                pass_value = set_pass(cliente, correo_output)
                return pass_value
        else:
            print(f"No se encontró el cliente: {cliente}, se procederá a crearlo.")
            pass_value = set_pass(cliente, correo_output)
            return pass_value
    except Exception as e:
        print(f"Error al obtener la contraseña: {e}")
        return None
    finally:
        session.close()


def resend_pass_email(cliente: str) -> bool:
    """
    Función para reenviar manualmente la contraseña a los usuarios relacionados de un cliente.
    """
    try:
        session = get_sqlite_session()
        cliente = cliente[:255]  # Asegurar que el nombre del cliente no exceda la longitud máxima
        cliente_obj = session.query(Cliente).filter_by(nombre=cliente).first()
        if not cliente_obj:
            print(f"No se encontró el cliente: {cliente}")
            return False

        pass_value = cliente_obj.pass_
        fecha_actualizacion_pass = cliente_obj.fecha_actualizacion_pass
        if fecha_actualizacion_pass:
            dias_transcurridos = (datetime.now() - fecha_actualizacion_pass).days
            dias_vigencia_actuales_pass = DIAS_VIGENCIA_PASS_ZIP - dias_transcurridos
        else:
            dias_vigencia_actuales_pass = DIAS_VIGENCIA_PASS_ZIP

        cliente_id = cliente_obj.id
        related_emails = get_related_users_emails(cliente_id)
        related_emails.append(os.getenv("CORREO_RECEPTOR_TEST_MAIL"))

        if not related_emails:
            print(f"No hay usuarios relacionados para el cliente: {cliente}")
            return False

        # Enviar el correo electrónico con el pass_value a los usuarios relacionados
        successful_emails, failed_emails = send_email_smtp(
            sender_email=SENDER_EMAIL,
            receiver_emails=related_emails,
            subject=f"Clave de seguridad para NFE Alert: Revisión de Domicilios Fiscales Electrónicos - {cliente}",
            html_file_path=None,
            zip_file_paths=None,
            html_content=read_and_modify_html(
                cliente, pass_value, dias_vigencia_actuales_pass
            ),
        )

        if failed_emails:
            print(f"Error al enviar correos a: {', '.join(failed_emails)}")
            return False

        print("Correos enviados exitosamente a los usuarios relacionados.")
        return True

    except Exception as e:
        print(f"Error al reenviar la contraseña: {e}")
        return False

    finally:
        session.close()

if __name__ == "__main__":
    pass
    # verify_and_add_user_client_relationship(
    #     cliente_id=1,
    #     correo_output=["rtolaba@deloitte.com;lmarinaro@deloitte.com"],
    #     cliente="FACEBOOK ARGENTINA S.R.L",
    #     new_pass="pYn2VLClQOfa",
    # )

    # get_pass_zip(cliente='FACEBOOK ARGENTINA S.R.L', correo_output=["lmarinaro@deloitte.com", "amiriarte@deloitte.com"])
    # get_pass_zip(cliente='FACEBOOK ARGENTINA S.R.L', correo_output=["lmarinaro@deloitte.com", "rtolaba@deloitte.com"])
    # verify_and_delete_user_client_relationship(cliente_id=1, correo_output=["lmarinaro@deloitte.com", "rtolaba@deloitte.com"])
    # get_pass_zip(cliente='SIMPLOT ARGENTINA S.R.L', correo_output=["lmarinaro@deloitte.com"])
    # get_pass_zip(cliente='SIMPLOT ARGENTINA S.R.L', correo_output=["rtolaba@deloitte.com"])


    # get_pass_zip(cliente='EDGE ARGENTINA S.R.L', correo_output=["lmarinaro@deloitte.com"])
    # test_usuarios_autorizados, test_dias, test_inserted_users, test_all_successful_emails, test_all_failed_emails = verify_and_add_user_client_relationship(cliente_id=2, correo_output=['lmarinaro@deloitte.com'], cliente='EDGE ARGENTINA S.R.L' , new_pass='dSCfFiOs1pcd')

    # conectar_db(
    #     proceso='Revision de Domicilios Fiscales Electrónicos',
    #     cliente='TaxTech',
    #     username='usuario1@ejemplo.com;usuario2@ejemplo.com',
    #     inicio_value=datetime.now(),
    #     estado_value="Correcto"
    # )

    # verify_and_add_users(correo_output=["lmarinaro@deloitte.com", "rtolaba@deloitte.com"])
    
    cliente = "Europ Assistance Argentina S.A"
    resultado = resend_pass_email(cliente)
    if resultado:
        print("Correo enviado exitosamente.")
    else:
        print("Hubo un problema al enviar el correo.")