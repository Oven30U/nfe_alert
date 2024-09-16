from os import getlogin
from datetime import datetime, timedelta
from pyodbc import connect, OperationalError
from time import sleep
from typing import List
import random
import string

SERVER = "ARBAS0228\\RPA"
DATABASE = "Tecnologia"
USERNAME = "TaxTech"
PASSWORD = "T&LTechnologies"
DRIVER = "{SQL Server}"


def conectar_db(
    proceso,
    cliente,
    username=getlogin(),
    inicio_value=datetime.now(),
    estado_value="Erróneo",
):
    """Se conecta a la base de datos interna para hacer un seguimiento de las ejecuciones."""
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
    clientes_si_verificar: List[str], retries=10, delay=30
) -> List[str]:
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


def get_clientes_ejecutados_hoy(clientes: List[str]) -> List[str]:
    """Verifica si hay datos en 'finalizado' para una lista de clientes el día de hoy y trae el más reciente de cada uno."""
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


# ToDo luego de setear un password, se debe dar aviso por mail al usuario principal del clte
def set_pass(cliente: str) -> str:
    """Genera una nueva contraseña, actualiza la base de datos y devuelve la nueva contraseña."""
    new_pass = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    fecha_actualizacion = datetime.now().strftime("%d-%m-%Y")
    try:
        conn = connect(
            f"Driver={DRIVER};Server={SERVER};Database={DATABASE};UID={USERNAME};PWD={PASSWORD};"
        )
        cursor = conn.cursor()

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
        conn.commit()
        return new_pass
    except Exception as e:
        print(f"Error al actualizar la contraseña: {e}")
        return None
    finally:
        conn.close()


def get_pass_zip(cliente: str) -> str:
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
                if fecha_actualizacion_pass >= datetime.now() - timedelta(days=90):
                    return pass_value
                else:
                    return set_pass(cliente)
            else:
                return set_pass(cliente)
        else:
            print(f"No se encontró el cliente: {cliente}, se procederá a crearlo.")
            return set_pass(cliente)
    except Exception as e:
        print(f"Error al obtener la contraseña: {e}")
        return None
    finally:
        conn.close()
