from os import getlogin
from datetime import datetime
from pyodbc import connect, OperationalError
from time import sleep
from typing import List

# import pyodbc

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
                f"Driver={DRIVER};"
                f"Server={SERVER};"
                f"Database={DATABASE};"
                f"UID={USERNAME};"
                f"PWD={PASSWORD};"
            )
        except (
            Exception
        ) as e:  # ? En caso de que se haya desconectado de la vpn, se registrará en el Log de errores
            print(f"Error de conexión num {i + 1}: {e}")
            if i < max_reintentos_conn - 1:
                sleep(3)
            else:
                print(
                    "Error Verifique mantenerse conectado a la VPN durante la ejecución del programa."
                )
                return

    fin_value = datetime.now()
    cursor = conn.cursor()
    usernames = username.split(";")
    for user in usernames:
        user_name = user.split("@")[0].strip()
        if user_name != "":
            cursor.execute(
                """
                INSERT INTO monitoreo_bots (username, proceso, estado, iniciado, finalizado, cliente)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_name, proceso, estado_value, inicio_value, fin_value, cliente),
            )

    conn.commit()


# ToDo - Revisar si no esta depreciada esta función por get_clientes_ejecutados_hoy
def get_ultimo_finalizado(cliente):
    """Obtiene el valor de 'finalizado' más reciente para el proceso y cliente especificados."""
    try:
        conn = connect(
            f"Driver={DRIVER};"
            f"Server={SERVER};"
            f"Database={DATABASE};"
            f"UID={USERNAME};"
            f"PWD={PASSWORD};"
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
        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        print(f"Error al obtener el último 'finalizado': {e}")
        return None
    finally:
        conn.close()


def get_clientes_ejecutados_hoy_with_retries(
    clientes_si_verificar: List[str], retries=10, delay=30
) -> List[str]:
    """
    Intenta obtener los clientes ejecutados hoy hasta 10 veces con intervalos de 30 segundos.
    Si falla, devuelve clientes_si_verificar.
    """
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
    """
    Verifica si hay datos en 'finalizado' para
    una lista de clientes el dia de hoy
    y trae el más reciente de cada uno.
    """
    try:
        conn = connect(
            f"Driver={DRIVER};"
            f"Server={SERVER};"
            f"Database={DATABASE};"
            f"UID={USERNAME};"
            f"PWD={PASSWORD};"
        )
        cursor = conn.cursor()

        # Crear una cadena de marcadores de posición para la lista de clientes
        placeholders = ", ".join(["?"] * len(clientes))

        # Modificar la consulta SQL para usar los marcadores de posición
        query = f"""
            SELECT cliente, MAX(finalizado) AS finalizado
            FROM monitoreo_bots
            WHERE CAST(finalizado AS DATE) = CAST(GETDATE() AS DATE)
            AND proceso = 'Revision de Domicilios Fiscales Electronicos' 
            AND cliente IN ({placeholders})
            GROUP BY cliente
        """

        # Ejecutar la consulta con la lista de clientes
        cursor.execute(query, clientes)
        results = cursor.fetchall()

        # Procesar los resultados
        clientes_hoy = [row.cliente for row in results]
        # Crear una lista de clientes que no se encuentran en clientes_hoy
        clientes_no_ejecutados_hoy = [
            cliente for cliente in clientes if cliente not in clientes_hoy
        ]

        return clientes_no_ejecutados_hoy

    except Exception as e:
        print(f"Error al obtener el último 'finalizado': {e}")
        return []
    finally:
        conn.close()


# ? Función para crear un error en un 'log de errores'
# def crear_error(titulo, conexion=True):
#     """Registra el error pasado como parámetro en un txt dentro de la carpeta System"""
#     #* Hace un conteo de la cantidad de errores que hay registrados (si el archivo existe)
#     registro = 1
#     if exists(ARCHIVO_ERRORES):
#         with open(ARCHIVO_ERRORES, "r") as archivo_error:
#             for linea in archivo_error:
#                 if "Registro" in linea:
#                     registro += 1

#     #* Abre el archivo y escribe el error con el número de registro actual
#     error_text = format_exc()
#     fecha_error = datetime.now()
#     fecha_error_form = fecha_error.strftime(f"%d-%m-%Y (%H:%M:%S)") # Formatea la fecha
#     with open(ARCHIVO_ERRORES, "a") as archivo_error: # Abre el archivo en modo adición (no sobreescribe el texto existente)
#         archivo_error.write(f"Registro {registro}: {titulo}\n")
#         archivo_error.write(f"Fecha del error: {fecha_error_form}\n")
#         archivo_error.write(error_text)
#         archivo_error.write("\n----------------------------------------------------\n\n")

#     if conexion: # Registra el error en la base de datos si conexion = True
#         conectar_db()
