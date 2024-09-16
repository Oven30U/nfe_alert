import os
import pandas as pd
from datetime import datetime
from win32com.client import Dispatch

from jurisdicciones.jurisdiccion import LoggedException
from conectar_db import (
    get_clientes_ejecutados_hoy_with_retries,
)  # get_ultimo_finalizado,

# from openpyxl import load_workbook
from cliente_system import ClienteSystem
import logging
from config import (
    PATH_ESTRUCTURA_ROBOT,
    NOMBRE_ARCHIVO_CLIENTE,
    SHEET_ARCHIVO_CLIENTE,
    log_file_path,
)


class InputException(LoggedException):
    """Excepción lanzada por errores en la captura de los input."""

    pass


def cargar_excels():
    dataframes = []

    for root, dirs, files in os.walk(PATH_ESTRUCTURA_ROBOT):
        for file in files:
            if file == NOMBRE_ARCHIVO_CLIENTE:
                file_path = os.path.join(root, file)

                # Leer el archivo de Excel utilizando pandas
                xls = pd.ExcelFile(file_path)

                # Verificar si la hoja existe
                if SHEET_ARCHIVO_CLIENTE in xls.sheet_names:
                    # Especificar manualmente el rango de filas y columnas para las tablas
                    skiprows_jurisdiccion = 4
                    nrows_jurisdiccion = 27
                    usecols_jurisdiccion = "A:D"

                    skiprows_cliente = 0
                    nrows_cliente = 2
                    usecols_cliente = "A:G"

                    # Especificar los tipos de datos para las columnas deseadas
                    dtype_jurisdiccion = {}

                    dtype_cliente = {
                        "CUIT": "str",
                    }

                    # Leer las tablas utilizando pandas
                    df_tabla_jurisdiccion = pd.read_excel(
                        file_path,
                        sheet_name=SHEET_ARCHIVO_CLIENTE,
                        skiprows=skiprows_jurisdiccion,
                        nrows=nrows_jurisdiccion,
                        usecols=usecols_jurisdiccion,
                        dtype=dtype_jurisdiccion,
                    )
                    df_tabla_cliente = pd.read_excel(
                        file_path,
                        sheet_name=SHEET_ARCHIVO_CLIENTE,
                        skiprows=skiprows_cliente,
                        nrows=nrows_cliente,
                        usecols=usecols_cliente,
                        dtype=dtype_cliente,
                    )

                    # Repetir los valores de df_tabla_cliente para que coincidan con el número de filas de df_tabla_jurisdiccion
                    repeated_cliente_values = df_tabla_cliente.loc[
                        df_tabla_cliente.index.repeat(len(df_tabla_jurisdiccion))
                    ].reset_index(drop=True)

                    # Añadir las columnas de df_tabla_cliente a df_tabla_jurisdiccion
                    for col in df_tabla_cliente.columns:
                        df_tabla_jurisdiccion[col] = repeated_cliente_values[col]

                    dataframes.append(df_tabla_jurisdiccion)

    if dataframes:
        df_final = pd.concat(dataframes, ignore_index=True)
        return df_final
    else:
        return pd.DataFrame()


def cerrar_excel(nombres_archivos):
    """
    Cierra las instancias de Excel de los archivos especificados.

    Esta función intenta cerrar las instancias de Excel para una lista dada de nombres de archivos.
    Guarda los cambios realizados en los libros antes de cerrarlos y maneja excepciones para evitar
    interrupciones durante el proceso. Si no puede cerrar un libro específico o finalizar la instancia
    de Excel, simplemente omite el error y continúa con el siguiente archivo o paso.

    Parámetros:
    nombres_archivos (list): Una lista de cadenas que contiene los nombres de los archivos de Excel
                             que se intentarán cerrar.

    Notas:
    - La función no devuelve ningún valor.
    - Los libros se cierran sin guardar cambios.
    - Se manejan excepciones de manera genérica para evitar interrupciones, pero no se proporciona
      retroalimentación detallada sobre las excepciones capturadas.
    """
    try:
        excel = Dispatch("Excel.Application")
        for libro in excel.Workbooks:
            for nombre in nombres_archivos:
                try:
                    if nombre in libro.Name:
                        libro.Save()  # Guardar el libro antes de cerrarlo
                        libro.Close(SaveChanges=False)
                except:
                    pass
        try:
            del excel, nombres_archivos
        except:
            pass
    except:
        pass


# def verificar_cliente(
#     cliente_system,
#     archivo_input_a_verificar,
#     clientes_si_verificar_config,
#     clientes_si_verificar,
#     clientes_no_verificar,
# ):
#     if cliente_system.nombre in clientes_si_verificar_config:
#         clientes_si_verificar.append(cliente_system)
#     else:
#         clientes_no_verificar.append(cliente_system)


# def verificar_clientes(
#     cliente_system,
#     archivo_input_a_verificar,
#     debug,
#     ejecutar_todos_clientes,
#     ejecutar_clientes_lista,
#     sin_debug_ejecutar_ejecutar_lista,
#     clientes_si_verificar_config,
#     clientes_si_verificar,
#     clientes_no_verificar,
# ):
#     """
#     Verifica los clientes según las configuraciones y los agrega a las listas correspondientes.

#     Parámetros:
#     - cliente_system: Objeto ClienteSystem que representa al cliente a verificar.
#     - archivo_input_a_verificar: Ruta del archivo de input a verificar.
#     - debug: Booleano que indica si el modo debug está activado.
#     - ejecutar_todos_clientes: Booleano que indica si se deben ejecutar todos los clientes.
#     - ejecutar_clientes_lista: Booleano que indica si se deben ejecutar los clientes de la lista.
#     - clientes_si_verificar_config: Lista de nombres de clientes que se deben verificar.
#     - clientes_si_verificar: Lista donde se agregarán los clientes que se deben verificar.
#     - clientes_no_verificar: Lista donde se agregarán los clientes que no se deben verificar.
#     """
#     if debug:
#         if ejecutar_todos_clientes:
#             clientes_si_verificar.append(cliente_system)
#         elif ejecutar_clientes_lista:
#             verificar_cliente(
#                 cliente_system,
#                 archivo_input_a_verificar,
#                 clientes_si_verificar_config,
#                 clientes_si_verificar,
#                 clientes_no_verificar,
#             )
#         else:
#             verificar_cliente(
#                 cliente_system,
#                 archivo_input_a_verificar,
#                 clientes_si_verificar_config,
#                 clientes_si_verificar,
#                 clientes_no_verificar,
#             )
#     else:
#         if sin_debug_ejecutar_ejecutar_lista:
#             verificar_cliente(
#                 cliente_system,
#                 archivo_input_a_verificar,
#                 clientes_si_verificar_config,
#                 clientes_si_verificar,
#                 clientes_no_verificar,
#             )
#         elif cliente_system.verificar_ejecucion(archivo_input_a_verificar):
#             clientes_si_verificar.append(cliente_system)
#         else:
#             clientes_no_verificar.append(cliente_system)


def obtener_clientes(
    debug,
    ejecutar_todos_clientes,
    ejecutar_clientes_lista,
    sin_debug_ejecutar_ejecutar_lista,
    clientes_si_verificar_config,
    jurisdiccion_clases,
):
    # PATH_BOT = "Estructura-robot/"
    # PATH_SYSTEM = "Estructura-robot/System/"
    # PATH_ERRORES = "Estructura-robot/System/errores/"
    # PATH_CLIENTES = f"{PATH_SYSTEM}System-Clientes.xlsx"
    # PATH_CREDENCIALES_DIR = f"{PATH_SYSTEM}credenciales/"

    cerrar_excel(NOMBRE_ARCHIVO_CLIENTE)

    try:
        # df_clientes = pd.read_excel(PATH_CLIENTES, sheet_name="System-Clientes")
        df_clientes = cargar_excels()
    except Exception as e:
        raise InputException(f"No se pudo crear el df_clientes, {e}")
        # print("No se pudo acceder al archivo %s: %s", PATH_CLIENTES, str(e))

    # Limpiamos todas las filas que contengan algun valor vacio
    df_clientes = df_clientes.dropna(how="any")
    df_clientes = df_clientes[df_clientes["Consultar"].str.lower() == "si"]

    # ToDo - Verificar si el dia de hoy se encuentra en dias de ejecución
    # Obtener el día de hoy en formato español
    dias_semana_es = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    hoy = dias_semana_es[datetime.today().weekday()]
    # Filtrar las filas donde la columna "Día/s de ejecución" contenga el día de hoy
    df_clientes = df_clientes[
        df_clientes[df_clientes.columns[-1]].str.contains(hoy, case=False, na=False)
    ]

    clientes_si_verificar = df_clientes["Cliente"].unique().tolist()
    # clientes_no_verificar = []
    # Todo: Ver que hacer en caso de faya de conexión del server
    try:
        clientes_pendientes_verificar = get_clientes_ejecutados_hoy_with_retries(
            clientes_si_verificar
        )
    except Exception as e:
        logging.exception(
            "Error al intentar clientes_pendientes_verificar en inputs.py"
        )
        # clientes_pendientes_verificar = []
        clientes_pendientes_verificar = df_clientes
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Exception: {str(e)}\n")

    # Filtrar las filas donde el cliente no se haya ejecutado hoy
    df_clientes = df_clientes[df_clientes["Cliente"].isin(clientes_pendientes_verificar)]



    df_clientes.rename(columns={"Código-Jurisdicción": "Jurisdiccion", "CUIT": "cuit_cliente","Correos destinatarios": "Correo Output"}, inplace=True)
    #Index(['Jurisdiccion', 'Consultar', 'Usuario', 'Password', 'Cliente', 'CUIT',
    #    'Socio responsable', 'Correos destinatarios',
    #    'Rango de consulta dias anteriores', 'Schedule', 'Dia/s de ejecución'],
    #   dtype='object')
    
    # Convertir la columna 'Rango de consulta dias anteriores' a tipo entero
    df_clientes["Rango de consulta dias anteriores"] = df_clientes["Rango de consulta dias anteriores"].astype(int)
    # Agregar la columna fecha_hasta con la fecha actual
    df_clientes["fecha_hasta"] = datetime.now().date()
    # Agregar la columna fecha_desde restando el valor de 'Rango de consulta dias anteriores' a fecha_hasta
    df_clientes["fecha_desde"] = df_clientes["fecha_hasta"] - pd.to_timedelta(df_clientes["Rango de consulta dias anteriores"], unit='d')
    # Convertimos los datetime a formato str
    df_clientes["fecha_desde"] = df_clientes["fecha_desde"].apply(lambda x: x.strftime("%d%m%Y"))
    df_clientes["fecha_hasta"] = df_clientes["fecha_hasta"].apply(lambda x: x.strftime("%d%m%Y"))
    
    df_clientes["cuit_cliente"] = df_clientes["cuit_cliente"].str.replace("-", "")

    df_clientes["Jurisdiccion"] = df_clientes["Jurisdiccion"].replace(
        jurisdiccion_clases
    )

    return df_clientes

    # for _, row in df_clientes.iterrows():
    #     # obtenemos ultima verificacion de la bbdd, si es distinta a la fecha actual -> instanciamos el cliente
    #     ultima_verificacion_cliente = get_ultimo_finalizado(row["Cliente"])
    #     if ultima_verificacion_cliente is not None:
    #         if isinstance(ultima_verificacion_cliente, str):
    #             ultima_verificacion_cliente = datetime.strptime(
    #                 ultima_verificacion_cliente, "%d/%m/%Y %H:%M:%S"
    #             )
    #         elif isinstance(ultima_verificacion_cliente, pd.Timestamp):
    #             ultima_verificacion_cliente = (
    #                 ultima_verificacion_cliente.to_pydatetime()
    #             )

    #         if ultima_verificacion_cliente.date() != datetime.now().date():
    #             cliente_system = ClienteSystem(
    #                 row["Cliente"],
    #                 row["Correos destinatarios"],
    #                 row["Socio responsable"],
    #                 row["Schedule"],
    #                 row["Dia/s de ejecución"],
    #                 # row["Hora de inicio"],
    #                 # row["Última verificación"],
    #                 ultima_verificacion_cliente,
    #             )  #     archivo_input_a_verificar = f"{PATH_BOT}{cliente_system.nombre}/Input"

    #     verificar_clientes(
    #         cliente_system,
    #         archivo_input_a_verificar,
    #         debug,
    #         ejecutar_todos_clientes,
    #         ejecutar_clientes_lista,
    #         sin_debug_ejecutar_ejecutar_lista,
    #         clientes_si_verificar_config,
    #         clientes_si_verificar,
    #         clientes_no_verificar,
    #     )

    # df_final = pd.DataFrame()
    # if not clientes_si_verificar:
    #     print("No hay clientes por verificar en este momento")
    #     return df_final
    # else:
    #     print(
    #         f"\nClientes SI verificar: {', '.join([cliente.nombre for cliente in clientes_si_verificar])}\n"
    #     )
    #     print(
    #         f"\nClientes NO verificar: {', '.join([cliente.nombre for cliente in clientes_no_verificar])}\n"
    #     )

    # df_credenciales = pd.DataFrame()
    # for cliente in clientes_si_verificar:
    #     try:
    #         credenciales_files = [
    #             f for f in os.listdir(PATH_CREDENCIALES_DIR) if cliente.nombre in f
    #         ]
    #         if not credenciales_files:
    #             raise InputException(
    #                 f"No se encontró archivo de credenciales para {cliente.nombre}"
    #             )
    #         credenciales_file = os.path.join(
    #             PATH_CREDENCIALES_DIR, credenciales_files[0]
    #         )
    #         cerrar_excel(credenciales_file)
    #         df_nuevas_credenciales = pd.read_excel(credenciales_file)
    #         df_credenciales = pd.concat(
    #             [df_credenciales, df_nuevas_credenciales], ignore_index=True
    #         )
    #     except Exception as e:
    #         raise InputException(
    #             f"No se pudo acceder al archivo de credenciales para {cliente.nombre}, {e}"
    #         )
    #         print(
    #             "No se pudo acceder al archivo de credenciales para %s: %s",
    #             cliente.nombre,
    #             str(e),
    #         )

    # df_credenciales["Cliente"] = df_credenciales["Cliente"].str.rstrip(".")

    # # Obtiene una lista de todos los nombres de las carpetas en el directorio
    # folder_names = [
    #     name
    #     for name in os.listdir(PATH_BOT)
    #     if os.path.isdir(os.path.join(PATH_BOT, name))
    # ]

    # if "System" in folder_names:
    #     folder_names.remove("System")

    # clientes_si_verificar_dict = [
    #     {"Cliente": cliente.nombre, "Correo Output": cliente.correo_output}
    #     for cliente in clientes_si_verificar
    # ]
    # df_clientes_si_verificar = pd.DataFrame(clientes_si_verificar_dict)

    # fecha_actual = datetime.today()
    # for index, row in df_clientes_si_verificar.iterrows():
    #     cliente_nombre = row["Cliente"]
    #     correo_output = row["Correo Output"]
    #     try:
    #         path_archivo_input = (
    #             f"{PATH_BOT}{cliente_nombre}/Input/DFE-Input-Cliente.xlsx"
    #         )
    #         archivo_input = pd.read_excel(path_archivo_input)
    #         df_input = pd.read_excel(path_archivo_input, header=4)

    #     except Exception as e:
    #         raise InputException(
    #             cliente_nombre,
    #             f"No se pudo acceder al archivo, PATH_INPUT_VERIFICAR, {e}",
    #         )
    #         # print("No se pudo acceder al archivo")

    #     # Definir que jurisdicciones se deben consultar
    #     df_input = df_input[df_input["Consultar"].str.strip().str.lower() != "no"]
    #     df_input["Cliente"] = cliente_nombre
    #     df_input["Correo Output"] = correo_output
    #     df_input["fecha_hasta"] = fecha_actual
    #     rango_dias = archivo_input.iloc[0, 2]
    #     df_input["cuit_cliente"] = archivo_input.iloc[0, 1].replace("-", "")
    #     df_input["fecha_desde"] = df_input["fecha_hasta"] - pd.to_timedelta(
    #         rango_dias, unit="D"
    #     )
    #     df_input["fecha_desde"] = df_input["fecha_desde"].dt.strftime("%d/%m/%Y")
    #     df_input["fecha_hasta"] = df_input["fecha_hasta"].dt.strftime("%d/%m/%Y")
    #     df_final = pd.concat([df_final, df_input])

    # # Resetea el índice del DataFrame final
    # df_final.reset_index(drop=True, inplace=True)

    # # Aplicamos stripa las columnas relevantes para el merge en ambos df
    # df_final["Cliente"] = df_final["Cliente"].str.strip()
    # df_final["Jurisdiccion"] = df_final["Jurisdiccion"].str.strip()
    # df_credenciales["Cliente"] = df_credenciales["Cliente"].str.strip()
    # df_credenciales["Jurisdiccion"] = df_credenciales["Jurisdiccion"].str.strip()

    # # Perform the merge operation
    # df_final = df_final.merge(
    #     df_credenciales[["Cliente", "Jurisdiccion", "Usuario", "Password"]],
    #     on=["Cliente", "Jurisdiccion"],
    #     how="left",
    # )
    # # Crear df_sin_credenciales con las filas donde 'Usuario' o 'Password' son NaN
    # df_sin_credenciales = df_final[
    #     df_final["Usuario"].isna() | df_final["Password"].isna()
    # ]
    # # Check si hay filas en df_sin_credenciales
    # if not df_sin_credenciales.empty:
    #     print(df_sin_credenciales)

    # # Eliminar las filas de df_final donde 'Usuario' o 'Password' son NaN
    # df_final = df_final.dropna(subset=["Usuario", "Password"], how="any")

    # Reemplazamos df_final['Jurisdiccion'], por el nombre de la clase
    # df_final["Jurisdiccion"] = df_final["Jurisdiccion"].replace(jurisdiccion_clases)

    # return df_final


# if __name__ == "__main__":
#     df_final = obtener_clientes()
#     print(df_final)
