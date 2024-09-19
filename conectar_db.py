import os
import random
import string
from datetime import datetime, timedelta
from time import sleep

from pyodbc import connect

from pruebas.correo_cli import send_email_smtp

SERVER = "ARBAS0228\\RPA"
DATABASE = "Tecnologia"
USERNAME = "TaxTech"
PASSWORD = "T&LTechnologies"
DRIVER = "{SQL Server}"


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
    max_reintentos_conn = 10
    for i in range(max_reintentos_conn):
        try:
            conn = connect(
                f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
            )
            break
        except Exception as e:
            print(f"Error de conexión num {i + 1}: {e}")
            if i < max_reintentos_conn - 1:
                sleep(3)
            else:
                print(
                    "Error: Verifique mantenerse conectado a la VPN durante la ejecución del programa."
                )
                return

    fin_value = datetime.now()
    cursor = conn.cursor()
    usernames = username.split(";")
    for user in usernames:
        user_name = user.split("@")[0].strip()
        if user_name:
            cursor.execute(
                """
                INSERT INTO monitoreo_bots (username, proceso, estado, iniciado, finalizado, cliente)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_name, proceso, estado_value, inicio_value, fin_value, cliente),
            )
    conn.commit()
    conn.close()


def get_ultimo_finalizado(cliente):
    """Obtiene el valor de 'finalizado' más reciente para el proceso y cliente especificados."""
    try:
        conn = connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TOP 1 finalizado
            FROM monitoreo_bots
            WHERE proceso = 'Revision de Domicilios Fiscales Electronicos' 
              AND cliente = ? 
              AND estado = 'Correcto'
            ORDER BY id DESC
            """,
            (cliente,),
        )
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error al obtener el último 'finalizado': {e}")
        return None
    finally:
        conn.close()


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
        conn = connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        )
        cursor = conn.cursor()
        placeholders = ", ".join(["?"] * len(clientes))
        query = f"""
            SELECT cliente, MAX(finalizado) AS finalizado
            FROM monitoreo_bots
            WHERE CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)
            AND proceso = 'Revision de Domicilios Fiscales Electronicos' 
            AND cliente IN ({placeholders})
            GROUP BY cliente
        """
        cursor.execute(query, clientes)
        results = cursor.fetchall()
        clientes_hoy = [row.cliente for row in results]
        return [cliente for cliente in clientes if cliente not in clientes_hoy]
    except Exception as e:
        print(f"Error al obtener el último 'finalizado': {e}")
        return []
    finally:
        conn.close()


def read_and_modify_html(
    cliente: str, new_pass: str, dias: int, username: str = "usuario"
) -> str:
    """Lee y modifica el contenido HTML."""
    html_template_path = os.path.join("pruebas", "mail_plantilla_set_pass.html")
    with open(html_template_path, "r", encoding="utf-8") as file:
        html_content = file.read()
    html_content = html_content.replace("{{cliente}}", cliente)
    html_content = html_content.replace("{{new_pass}}", new_pass)
    html_content = html_content.replace("{{dias}}", str(dias))
    html_content = html_content.replace("{{username}}", username)
    return html_content


def verify_and_add_users(correo_output: list[str]):
    """Verifica si los items de correo_output se encuentran en la tabla usuarios_autorizados. Si falta alguno, lo agrega."""
    try:
        with connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        ) as conn:
            with conn.cursor() as cursor:
                # Split the string by semicolons to get individual email addresses
                if isinstance(correo_output, str):
                    correo_output = correo_output.split(";")

                usernames = [email.split("@")[0] for email in correo_output]

                # Verificar si los usuarios existen en usuarios_autorizados
                query = "SELECT username FROM usuarios_autorizados WHERE username IN ({})".format(
                    ",".join("?" * len(usernames))
                )
                cursor.execute(query, usernames)
                existing_users = {row[0] for row in cursor.fetchall()}

                # Agregar los usuarios que no existen
                missing_users = [
                    user for user in usernames if user not in existing_users
                ]
                fecha_autorizacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for user in missing_users:
                    query = "INSERT INTO usuarios_autorizados (username, fecha_autorizacion) VALUES (?, ?)"
                    cursor.execute(query, (user, fecha_autorizacion))

                conn.commit()
    except Exception as e:
        print(f"Error al verificar y agregar usuarios: {e}")


def verify_and_add_user_client_relationship(
    cliente_id: int, correo_output: list[str], cliente: str, new_pass: str
):
    """Verifica que todos los usuarios_autorizados tengan relación con el cliente. Si no tienen relación, la agrega y envía un correo."""
    try:
        with connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        ) as conn:
            with conn.cursor() as cursor:
                # Split the string by semicolons to get individual email addresses
                if isinstance(correo_output, str):
                    correo_output = correo_output.split(";")

                usernames = [email.split("@")[0] for email in correo_output]

                # Obtener los ids de los usuarios autorizados
                query = "SELECT id, username FROM usuarios_autorizados WHERE username IN ({})".format(
                    ",".join("?" * len(usernames))
                )
                cursor.execute(query, usernames)
                usuarios_autorizados = cursor.fetchall()
                usuarios_ids = {row[1]: row[0] for row in usuarios_autorizados}

                # Obtener la fecha de actualización de la contraseña
                query = "SELECT fecha_actualizacion_pass FROM clientes WHERE id = ?"
                cursor.execute(query, (cliente_id,))
                fecha_actualizacion_pass = cursor.fetchone()[0]
                if fecha_actualizacion_pass:
                    fecha_actualizacion_pass = datetime.strptime(
                        fecha_actualizacion_pass, "%d-%m-%Y"
                    )
                    # ToDo arreglar calculo
                    # Calcular la diferencia en días
                    # diferencia_dias = (datetime.now() - fecha_actualizacion_pass).days
                    # dias = 90 - diferencia_dias
                    dias = 90
                else:
                    dias = 90

                # Insertar en usuario_cliente si no existe la relación
                for username in usernames:
                    usuario_id = usuarios_ids.get(username)
                    if usuario_id:
                        query = """
                            SELECT COUNT(*)
                            FROM usuario_cliente
                            WHERE id_cliente = ? AND id_usuario = ?
                        """
                        cursor.execute(query, (cliente_id, usuario_id))
                        if cursor.fetchone()[0] == 0:
                            query = "INSERT INTO usuario_cliente (id_cliente, id_usuario) VALUES (?, ?)"
                            cursor.execute(query, (cliente_id, usuario_id))
                            # Enviar correo solo si hubo un insert
                            correo = f"{username}@deloitte.com"
                            send_email_smtp(
                                sender_email="robot-Tax-AR@deloitte.com",
                                receiver_emails=[correo],
                                subject=f"Actualización de clave de seguridad para Revisión de Domicilios Fiscales Electrónicos - {cliente}",
                                html_file_path=None,
                                zip_file_paths=None,
                                html_content=read_and_modify_html(
                                    cliente, new_pass, dias, username
                                ),
                            )
                conn.commit()
    except Exception as e:
        print(f"Error al verificar y agregar relación usuario-cliente: {e}")


def set_pass(cliente: str, correo_output: list[str]) -> str:
    """Genera una nueva contraseña, actualiza la base de datos y devuelve la nueva contraseña."""
    new_pass = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    fecha_actualizacion = datetime.now().strftime("%d-%m-%Y")
    correo_output = [correo_output] if isinstance(correo_output, str) else correo_output
    try:
        with connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        ) as conn:
            with conn.cursor() as cursor:
                # Asegurarse de que los valores no excedan las longitudes permitidas
                cliente = cliente[:255]
                new_pass = new_pass[:255]

                query = """
                    UPDATE clientes
                    SET [pass] = ?, [fecha_actualizacion_pass] = ?
                    WHERE nombre = ?
                """
                cursor.execute(query, (new_pass, fecha_actualizacion, cliente))
                if (
                    cursor.rowcount == 0
                ):  # Si no se actualizó ninguna fila, insertar un nuevo cliente
                    query = """
                        INSERT INTO clientes (nombre, pass, fecha_actualizacion_pass)
                        VALUES (?, ?, ?)
                    """
                    cursor.execute(query, (cliente, new_pass, fecha_actualizacion))

                # Obtener el id del cliente
                query = "SELECT id FROM clientes WHERE nombre = ?"
                cursor.execute(query, (cliente,))
                cliente_id = cursor.fetchone()[0]

                # Verificar y agregar usuarios
                verify_and_add_users(correo_output)

                # Verificar y agregar relación usuario-cliente
                verify_and_add_user_client_relationship(
                    cliente_id, correo_output, cliente, new_pass
                )

        return new_pass
    except Exception as e:
        print(f"Error al actualizar la contraseña: {e}")
        return None


def get_related_users_emails(cliente_id: int) -> list[str]:
    """Obtiene los correos de los usuarios relacionados con el cliente."""
    try:
        conn = connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        )
        cursor = conn.cursor()
        query = """
            SELECT ua.username
            FROM usuario_cliente uc
            JOIN usuarios_autorizados ua ON uc.id_usuario = ua.id
            WHERE uc.id_cliente = ?
        """
        cursor.execute(query, (cliente_id,))
        results = cursor.fetchall()
        return [f"{row[0]}@deloitte.com" for row in results]
    except Exception as e:
        print(f"Error al obtener los correos de los usuarios relacionados: {e}")
        return []
    finally:
        conn.close()


def get_pass_zip(
    cliente: str, correo_output: str | list[str] = ["lmarinaro@deloitte.com"]
) -> str:
    """Consulta el valor de [pass] y [fecha_actualizacion_pass] para el cliente especificado."""
    try:
        conn = connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        )
        cursor = conn.cursor()

        # Asegurarse de que el valor no exceda la longitud permitida
        cliente = cliente[:255]

        query = """
            SELECT TOP 1 [pass], [fecha_actualizacion_pass]
            FROM clientes
            WHERE nombre = ?
            ORDER BY id DESC
        """
        cursor.execute(query, (cliente,))
        result = cursor.fetchone()
        if result:
            pass_value, fecha_actualizacion_pass = result
            if fecha_actualizacion_pass:
                fecha_actualizacion_pass = datetime.strptime(
                    fecha_actualizacion_pass, "%d-%m-%Y"
                )

                # ToDo arreglar el calculo de "dias" si se genera la new_pass siempre es 90, si no se genera entonces es diferencia de dias
                # Calcular la diferencia en días
                # diferencia_dias = (datetime.now() - fecha_actualizacion_pass).days
                # dias = 90 - diferencia_dias
                dias = 90

                # Si la contraseña se actualizó hace menos de 90 días, devolverla
                if fecha_actualizacion_pass >= datetime.now() - timedelta(days=90):
                    # Obtener el id del cliente
                    query = "SELECT id FROM clientes WHERE nombre = ?"
                    cursor.execute(query, (cliente,))
                    cliente_id = cursor.fetchone()[0]

                    # Verificar y agregar usuarios
                    verify_and_add_users(correo_output)

                    # Verificar y agregar relación usuario-cliente
                    verify_and_add_user_client_relationship(
                        cliente_id, correo_output, cliente, pass_value
                    )

                    return pass_value
                else:
                    # Obtener el id del cliente
                    query = "SELECT id FROM clientes WHERE nombre = ?"
                    cursor.execute(query, (cliente,))
                    cliente_id = cursor.fetchone()[0]

                    # Obtener correos de usuarios relacionados
                    related_emails = get_related_users_emails(cliente_id)

                    pass_value = set_pass(cliente, correo_output)

                    # Enviar correo a todos los usuarios relacionados
                    send_email_smtp(
                        sender_email="robot-Tax-AR@deloitte.com",
                        receiver_emails=related_emails,
                        subject=f"Actualización de clave de seguridad para Revisión de Domicilios Fiscales Electrónicos - {cliente}",
                        html_file_path=None,
                        zip_file_paths=None,
                        html_content=read_and_modify_html(cliente, pass_value, dias),
                    )

                    return pass_value
            else:
                return set_pass(cliente, correo_output)
        else:
            print(f"No se encontró el cliente: {cliente}, se procederá a crearlo.")
            return set_pass(cliente, correo_output)
    except Exception as e:
        print(f"Error al obtener la contraseña: {e}")
        return None
    finally:
        conn.close()


if __name__ == "__main__":
    verify_and_add_user_client_relationship(
        cliente_id=1,
        correo_output=["rtolaba@deloitte.com;lmarinaro@deloitte.com"],
        cliente="FACEBOOK ARGENTINA S.R.L",
        new_pass="pYn2VLClQOfa",
    )
