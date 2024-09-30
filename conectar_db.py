import os
import random
import string
from datetime import datetime, timedelta
from time import sleep

from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text

from database import get_session, get_sqlite_session
from pruebas.correo_cli import send_email_smtp
from config import PATH_HTML_SET_PASS, DIAS_VIGENCIA_PASS_ZIP

from typing import Union, List


def conectar_db(
        proceso: str,
        cliente: str,
        username: str = os.getlogin(),
        inicio_value: datetime = datetime.now(),
        estado_value: str = "Erróneo",
):
    """Se conecta a la base de datos interna para hacer un seguimiento de las ejecuciones.

    Args:
        proceso (str): valor del proceso para monitoreo_bots
        cliente (str): cliente para monitoreo_bots
        username (str, optional): nombre de usuario. Defaults to os.getlogin().
        inicio_value (datetime, optional): hora de inicio del proceso. Defaults to datetime.now().
        estado_value (str, optional): hora de finalizacion del proceso. Defaults to "Erróneo".
    """
    try:
        session = get_session()
        sqlite_session = get_sqlite_session()

        if sqlite_session:
            # Check for records in SQLite
            sqlite_records = sqlite_session.execute(
                str(text("SELECT * FROM monitoreo_bots"))
            ).fetchall()

            if sqlite_records:
                # Insert records into the main database
                for record in sqlite_records:
                    session.execute(
                        str(text(
                            """
                            INSERT INTO monitoreo_bots (username, proceso, estado, iniciado, finalizado, cliente)
                            VALUES (:username, :proceso, :estado, :iniciado, :finalizado, :cliente)
                            """
                        )),
                        {
                            "username": record.username,
                            "proceso": record.proceso,
                            "estado": record.estado,
                            "iniciado": record.iniciado,
                            "finalizado": record.finalizado,
                            "cliente": record.cliente,
                        },
                    )
                session.commit()

                # Transfer records to monitoreo_bots_backup
                for record in sqlite_records:
                    sqlite_session.execute(
                        str(text(
                            """
                            INSERT INTO monitoreo_bots_backup (username, proceso, estado, iniciado, finalizado, cliente)
                            VALUES (:username, :proceso, :estado, :iniciado, :finalizado, :cliente)
                            """
                        )),
                        {
                            "username": record.username,
                            "proceso": record.proceso,
                            "estado": record.estado,
                            "iniciado": record.iniciado,
                            "finalizado": record.finalizado,
                            "cliente": record.cliente,
                        },
                    )
                sqlite_session.commit()

                # Delete records from SQLite
                sqlite_session.execute(str(text("DELETE FROM monitoreo_bots")))
                sqlite_session.commit()

    except Exception as e:
        print(f"Error al conectar con la base de datos interna: {e}. Intentando conectar con SQLite.")
        session = get_sqlite_session()

    if session is None:
        print("No se pudo establecer la conexión con ninguna base de datos.")
        return

    fin_value = datetime.now()
    usernames = username.split(";")
    for user in usernames:
        user_name = user.split("@")[0].strip()
        if user_name:
            session.execute(
                text(
                    """
                INSERT INTO monitoreo_bots (username, proceso, estado, iniciado, finalizado, cliente)
                VALUES (:username, :proceso, :estado, :iniciado, :finalizado, :cliente)
                """
                ),
                {
                    "username": user_name,
                    "proceso": proceso,
                    "estado": estado_value,
                    "iniciado": inicio_value,
                    "finalizado": fin_value,
                    "cliente": cliente,
                },
            )
    session.commit()
    session.close()


def get_ultimo_finalizado(cliente):
    """Obtiene el valor de 'finalizado' más reciente para el proceso y cliente especificados."""
    try:
        session = get_session()
        result = session.execute(
            text(
                """
            SELECT finalizado
            FROM monitoreo_bots
            WHERE proceso = 'Revision de Domicilios Fiscales Electronicos' 
              AND cliente = :cliente 
              AND estado = 'Correcto'
            ORDER BY id DESC
            LIMIT 1
            """
            ),
            {"cliente": cliente},
        ).fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error al obtener el último 'finalizado': {e}")
        return None
    finally:
        session.close()


def get_clientes_ejecutados_hoy_with_retries(
        clientes_si_verificar: list[str], retries=10, delay=30
) -> list[str]:
    """Intenta obtener los clientes ejecutados hoy hasta 10 veces con intervalos de 30 segundos."""
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


def get_clientes_ejecutados_hoy(clientes: list[str]) -> list[str]:
    """
    Verifica si hay datos en 'finalizado' para una lista de clientes el día de hoy y trae el más reciente de cada uno.

    Args:
        clientes (list[str]): lista de clientes a verificar

    Returns:
        list[str]: lista de clientes a verificar, que faltan verificarse hoy
    """
    try:
        session = get_session()
        placeholders = ", ".join([":cliente" + str(i) for i in range(len(clientes))])
        query = text(
            f"""
            SELECT cliente, MAX(finalizado) AS finalizado
            FROM monitoreo_bots
            WHERE CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)
            AND proceso = 'Revision de Domicilios Fiscales Electronicos' 
            AND cliente IN ({placeholders})
            GROUP BY cliente
        """
        )
        params = {f"cliente{i}": cliente for i, cliente in enumerate(clientes)}
        results = session.execute(query, params).fetchall()
        clientes_hoy = [row.cliente for row in results]
        return [cliente for cliente in clientes if cliente not in clientes_hoy]
    except Exception as e:
        print(f"Error al obtener el último 'finalizado': {e}")
        return []
    finally:
        session.close()


def read_and_modify_html(
        cliente: str, new_pass: str, dias: int, username: str = "usuario"
) -> str:
    """Lee y modifica el contenido HTML."""
    # html_template_path = os.path.join("pruebas", "mail_plantilla_set_pass.html")
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


def verify_and_add_users(correo_output: list[str]):
    """Verifica si los items de correo_output se encuentran en la tabla usuarios_autorizados. Si falta alguno, lo agrega y elimina los que ya no están."""
    try:
        session = get_sqlite_session()
        # Split the string by semicolons to get individual email addresses
        if isinstance(correo_output, str):
            correo_output = correo_output.split(";")

        # usernames = [email.split("@")[0] for email in correo_output]
        usernames = [email for email in correo_output]

        # Verificar si los usuarios existen en usuarios_autorizados
        query = text("SELECT username FROM usuarios_autorizados")
        existing_users = {row[0] for row in session.execute(str(query)).fetchall()}

        # Agregar los usuarios que no existen
        missing_users = [user for user in usernames if user not in existing_users]
        fecha_autorizacion = datetime.now()
        for user in missing_users:
            query = text(
                "INSERT INTO usuarios_autorizados (username, fecha_autorizacion) VALUES (:username, :fecha_autorizacion)"
            )
            session.execute(
                str(query), {"username": user, "fecha_autorizacion": fecha_autorizacion}
            )

        # Eliminar los usuarios que ya no están en correo_output
        users_to_remove = [user for user in existing_users if user not in usernames]
        for user in users_to_remove:
            query = text("DELETE FROM usuarios_autorizados WHERE username = :username")
            session.execute(str(query), {"username": user})

        session.commit()
        return existing_users, missing_users, users_to_remove
    except Exception as e:
        print(f"Error al verificar y actualizar usuarios: {e}")
        return None, None, None
    finally:
        if session:
            session.close()


def verify_and_add_user_client_relationship(
        cliente_id: int, correo_output: list[str], cliente: str, new_pass: str
) -> tuple[dict, int, list[str]]:
    """Verifica que todos los usuarios_autorizados tengan relación con el cliente. Si no tienen relación, la agrega y envía un correo."""
    session = None
    try:
        session = get_sqlite_session()
        # Split the string by semicolons to get individual email addresses
        if isinstance(correo_output, str):
            correo_output = correo_output.split(";")

        # usernames = [email.split("@")[0] for email in correo_output]
        usernames = [email for email in correo_output]

        # Obtener los ids de los usuarios autorizados
        query = text(
            "SELECT id, username FROM usuarios_autorizados WHERE username IN ({})".format(
                ",".join([f":username{i}" for i in range(len(usernames))])
            )
        )
        params = {f"username{i}": username for i, username in enumerate(usernames)}
        usuarios_autorizados = session.execute(str(query), params).fetchall()
        usuarios_ids = {row[1]: row[0] for row in usuarios_autorizados}

        # Obtener la fecha de actualización de la contraseña
        query = text(
            "SELECT fecha_actualizacion_pass FROM clientes WHERE id = :cliente_id"
        )
        result = session.execute(str(query), {"cliente_id": cliente_id}).fetchone()
        if result:
            fecha_actualizacion_pass = result[0]
        else:
            fecha_actualizacion_pass = None
        if fecha_actualizacion_pass:
            # Convertir fecha_actualizacion_pass a un objeto datetime
            fecha_actualizacion_pass = datetime.strptime(fecha_actualizacion_pass, '%Y-%m-%d %H:%M:%S.%f')

            diferencia_dias = (datetime.now() - fecha_actualizacion_pass).days
            if diferencia_dias > DIAS_VIGENCIA_PASS_ZIP:
                dias = DIAS_VIGENCIA_PASS_ZIP
            else:
                dias = DIAS_VIGENCIA_PASS_ZIP - diferencia_dias
        else:
            dias = DIAS_VIGENCIA_PASS_ZIP

        # Insertar en usuario_cliente si no existe la relación
        inserted_users = []
        for username in usernames:
            usuario_id = usuarios_ids.get(username)
            if (usuario_id):
                query = text(
                    """
                    SELECT COUNT(*)
                    FROM usuario_cliente
                    WHERE id_cliente = :cliente_id AND id_usuario = :usuario_id
                """
                )
                count = session.execute(
                    str(query), {"cliente_id": cliente_id, "usuario_id": usuario_id}
                ).fetchone()[0]
                if count == 0:
                    query = text(
                        "INSERT INTO usuario_cliente (id_cliente, id_usuario) VALUES (:cliente_id, :usuario_id)"
                    )
                    session.execute(
                        str(query), {"cliente_id": cliente_id, "usuario_id": usuario_id}
                    )
                    inserted_users.append(username)
                    # ToDo si hay failed_emails dentro de send_email_smtp deberia hacer rollback o avisar por mail a tech
                    # Enviar correo solo si hubo un insert
                    # correo = f"{username}@deloitte.com"
                    successful_emails, failed_emails = send_email_smtp(
                        sender_email="robot-Tax-AR@deloitte.com",
                        receiver_emails=[username],
                        subject=f"Actualización de clave de seguridad para Revisión de Domicilios Fiscales Electrónicos - {cliente}",
                        html_file_path=None,
                        zip_file_paths=None,
                        html_content=read_and_modify_html(
                            cliente, new_pass, dias, username
                        ),
                    )
        session.commit()
        return usuarios_autorizados, dias, inserted_users
    except Exception as e:
        print(f"Error al verificar y agregar relación usuario-cliente: {e}")
        return {}, 0, []
    finally:
        if session:
            session.close()


def set_pass(cliente: str, correo_output: list[str]) -> str:
    """Genera una nueva contraseña, actualiza la base de datos y devuelve la nueva contraseña."""
    new_pass = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    fecha_actualizacion = datetime.now()
    fecha_vencimiento = fecha_actualizacion + timedelta(days=90)
    correo_output = [correo_output] if isinstance(correo_output, str) else correo_output
    try:
        session = get_sqlite_session()
        # Asegurarse de que los valores no excedan las longitudes permitidas
        cliente = cliente[:255]
        new_pass = new_pass[:12]

        query = """
            UPDATE clientes
            SET [pass] = :new_pass, [fecha_actualizacion_pass] = :fecha_actualizacion, [fecha_vencimiento_pass] = :fecha_vencimiento
            WHERE nombre = :cliente
            """
        session.execute(
            query,
            {
                "new_pass": new_pass,
                "fecha_actualizacion": fecha_actualizacion,
                "fecha_vencimiento": fecha_vencimiento,
                "cliente": cliente,
            },
        )
        if (
                # session.execute(str(text("SELECT @@ROWCOUNT"))).fetchone()[0] == 0  # SQL Server
                # session.execute(str(text("SELECT changes()"))).fetchone()[0] == 0  # SQLite
                session.execute("SELECT changes()").fetchone()[0] == 0  # SQLite
        ):  # Si no se actualizó ninguna fila, insertar un nuevo cliente
            query = text(
                """
                INSERT INTO clientes (nombre, pass, fecha_actualizacion_pass, fecha_vencimiento_pass)
                VALUES (:cliente, :new_pass, :fecha_actualizacion, :fecha_vencimiento)
                """
            )
            session.execute(
                str(query),
                {
                    "cliente": cliente,
                    "new_pass": new_pass,
                    "fecha_actualizacion": fecha_actualizacion,
                    "fecha_vencimiento": fecha_vencimiento,
                },
            )

        # Obtener el id del cliente
        query = text("SELECT id FROM clientes WHERE nombre = :cliente")
        cliente_id = session.execute(str(query), {"cliente": cliente}).fetchone()[0]

        session.commit()

        # Verificar y agregar usuarios
        existing_users, missing_users, users_to_remove = verify_and_add_users(correo_output)

        # Verificar y agregar relación usuario-cliente
        usuarios_autorizados, dias, inserted_users = verify_and_add_user_client_relationship(
            cliente_id, correo_output, cliente, new_pass
        )

        # session.commit()
        return new_pass
    except Exception as e:
        print(f"Error al actualizar la contraseña: {e}")
        return None
    finally:
        session.close()


def get_related_users_emails(cliente_id: int) -> list[str]:
    """Obtiene los correos de los usuarios relacionados con el cliente."""
    try:
        session = get_sqlite_session()
        query = text(
            """
            SELECT ua.username
            FROM usuario_cliente uc
            JOIN usuarios_autorizados ua ON uc.id_usuario = ua.id
            WHERE uc.id_cliente = :cliente_id
            """
        )
        results = session.execute(str(query), {"cliente_id": cliente_id}).fetchall()
        return [f"{row[0]}" for row in results]
    except Exception as e:
        print(f"Error al obtener los correos de los usuarios relacionados: {e}")
        return []
    finally:
        session.close()


def get_pass_zip(
        cliente: str, correo_output: Union[str, List[str]] = ["lmarinaro@deloitte.com"]
) -> str:
    """Consulta el valor de [pass] y [fecha_actualizacion_pass] para el cliente especificado."""

    # Limpiamos correo_output en caso de tener vacios
    correo_output = [correo for correo in
                     (correo_output if isinstance(correo_output, list) else correo_output.split(";")) if
                     correo and correo.lower() != "nan"]

    try:
        session = get_sqlite_session()
        # Asegurarse de que el valor no exceda la longitud permitida
        cliente = cliente[:255]

        # Obtener la contraseña y la fecha de actualización de la contraseña
        query = text(
            """
            SELECT [pass], [fecha_actualizacion_pass]
            FROM clientes
            WHERE nombre = :cliente
            ORDER BY id DESC
            LIMIT 1
            """
        )
        result = session.execute(str(query), {"cliente": cliente}).fetchone()
        if result:
            pass_value, fecha_actualizacion_pass = result
            if fecha_actualizacion_pass:
                # Convertir fecha_actualizacion_pass a un objeto datetime
                fecha_actualizacion_pass = datetime.strptime(fecha_actualizacion_pass, '%Y-%m-%d %H:%M:%S.%f')

                # Calcular la diferencia en días
                dias_transcurridos = (datetime.now() - fecha_actualizacion_pass).days
                dias_vigencia_actuales_pass = DIAS_VIGENCIA_PASS_ZIP - dias_transcurridos

                # Devolver la contraseña si está vigente
                if dias_vigencia_actuales_pass > 0:
                    # Obtener el id del cliente
                    query = text("SELECT id FROM clientes WHERE nombre = :cliente")
                    cliente_id = session.execute(
                        str(query), {"cliente": cliente}
                    ).fetchone()[0]

                    # Verificar y agregar usuarios
                    existing_users, missing_users, users_to_remove = verify_and_add_users(correo_output)

                    # Verificar y agregar relación usuario-cliente
                    usuarios_autorizados, dias, inserted_users = verify_and_add_user_client_relationship(
                        cliente_id, correo_output, cliente, pass_value
                    )

                    return pass_value
                else:
                    # Obtener el id del cliente
                    query = text("SELECT id FROM clientes WHERE nombre = :cliente")
                    cliente_id = session.execute(
                        str(query), {"cliente": cliente}
                    ).fetchone()[0]

                    # Obtener correos de usuarios relacionados
                    related_emails = get_related_users_emails(cliente_id)

                    pass_value = set_pass(cliente, correo_output)

                    # Enviar correo a todos los usuarios relacionados
                    successful_emails, failed_emails = send_email_smtp(
                        sender_email="robot-Tax-AR@deloitte.com",
                        receiver_emails=related_emails,
                        subject=f"Actualización de clave de seguridad para Revisión de Domicilios Fiscales Electrónicos - {cliente}",
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


if __name__ == "__main__":
    # verify_and_add_user_client_relationship(
    #     cliente_id=1,
    #     correo_output=["rtolaba@deloitte.com;lmarinaro@deloitte.com"],
    #     cliente="FACEBOOK ARGENTINA S.R.L",
    #     new_pass="pYn2VLClQOfa",
    # )

    get_pass_zip(cliente='FACEBOOK ARGENTINA S.R.L', correo_output=["lmarinaro@deloitte.com", "pueba_agrego_nuevo@deloitte.com"])
