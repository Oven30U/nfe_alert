from os import getlogin
from datetime import datetime
from pyodbc import connect
from time import sleep


SERVER = "ARBAS0228\\RPA"
DATABASE = "Tecnologia"
USERNAME = "TaxTech"
PASSWORD = "T&LTechnologies"
DRIVER = "{SQL Server}"


def conectar_db(proceso, username=getlogin(), inicio_value=datetime.now(), estado_value="Erróneo"):
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
        except Exception as e:  # ? En caso de que se haya desconectado de la vpn, se registrará en el Log de errores
            print(f"Error de conexión num {i + 1}: {e}")
            if i < max_reintentos_conn - 1:
                sleep(3)
            else:
                print("Error Verifique mantenerse conectado a la VPN durante la ejecución del programa.")
                return

    fin_value = datetime.now()
    cursor = conn.cursor()
    usernames = username.split(";")
    for user in usernames:
        user_name = user.split("@")[0].strip()
        if user_name != '':
            cursor.execute(
                """
                INSERT INTO monitoreo_bots (username, proceso, estado, iniciado, finalizado)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_name,
                    proceso,
                    estado_value,
                    inicio_value,
                    fin_value,
                ),
            )

    conn.commit()

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
