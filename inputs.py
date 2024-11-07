import logging
import os
from datetime import datetime

import pandas as pd
from win32com.client import Dispatch

from conectar_db import (
    get_clientes_ejecutados_hoy_with_retries,
)
from config import (
    EJECUTAR_CLIENTES_LISTA,
    NOMBRE_ARCHIVO_CLIENTE,
    PATH_ESTRUCTURA_ROBOT,
    SHEET_ARCHIVO_CLIENTE,
    clientes_si_verificar_config,
    log_file_path,
)
from jurisdicciones.jurisdiccion import LoggedException


class InputException(LoggedException):
    """Excepción lanzada por errores en la captura de los input."""

    pass


def cargar_excels():
    dataframes = []

    for root, dirs, files in os.walk(PATH_ESTRUCTURA_ROBOT):
        for file in files:
            if NOMBRE_ARCHIVO_CLIENTE in file:
                file_path = os.path.join(root, file)

                # Leer el archivo de Excel utilizando pandas
                xls = pd.ExcelFile(file_path)

                # Verificar si la hoja existe
                if SHEET_ARCHIVO_CLIENTE in xls.sheet_names:
                    # Especificar manualmente el rango de filas y columnas para las tablas
                    skiprows_jurisdiccion = 5
                    nrows_jurisdiccion = 27
                    usecols_jurisdiccion = "A:D"

                    skiprows_cliente = 1
                    nrows_cliente = 2
                    usecols_cliente = "A:G"

                    # Especificar los tipos de datos para las columnas deseadas
                    dtype_jurisdiccion = {
                        "Usuario": "str",
                    }

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


def obtener_clientes(
        # debug,
        # ejecutar_todos_clientes,
        # ejecutar_clientes_lista,
        # sin_debug_ejecutar_ejecutar_lista,
        # clientes_si_verificar_config,
        jurisdiccion_clases,
):
    cerrar_excel(NOMBRE_ARCHIVO_CLIENTE)

    try:
        # df_clientes = pd.read_excel(PATH_CLIENTES, sheet_name="System-Clientes")
        df_clientes = cargar_excels()
    except Exception as e:
        raise InputException(f"No se pudo crear el df_clientes, {e}")
        # print("No se pudo acceder al archivo %s: %s", PATH_CLIENTES, str(e))

    # Drop rows where all columns except 'Socio responsable' or 'Correos destinatarios' are NaN
    df_clientes = df_clientes.dropna(
        how="all",
        subset=[
            col
            for col in df_clientes.columns
            if col not in ["Socio responsable", "Correos destinatarios"]
        ],
    )
    # Drop rows where both 'Socio responsable' and 'Correos destinatarios' are NaN
    df_clientes = df_clientes.dropna(
        subset=["Socio responsable", "Correos destinatarios"], how="all"
    )
    df_clientes = df_clientes[df_clientes["Consultar"].str.lower() == "si"]

    if not EJECUTAR_CLIENTES_LISTA:
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
    else:
        clientes_pendientes_verificar = clientes_si_verificar_config

    if not df_clientes.empty:
        # Filtrar las filas donde el cliente no se haya ejecutado hoy
        df_clientes = df_clientes[
            df_clientes["Cliente"].isin(clientes_pendientes_verificar)
        ]

        df_clientes.rename(
            columns={
                "Código-Jurisdicción": "Jurisdiccion",
                "CUIT": "cuit_cliente",
                "Correos destinatarios": "Correo Output",
            },
            inplace=True,
        )

        # Convertir la columna 'Rango de consulta dias anteriores' a tipo entero
        df_clientes["Rango de consulta dias anteriores"] = df_clientes[
            "Rango de consulta dias anteriores"
        ].astype(int)

        # Agregar fecha_hasta' que sea de tipo datetime
        df_clientes["fecha_hasta"] = pd.to_datetime(datetime.now().date())

        # Agregar la columna fecha_desde restando el valor de 'Rango de consulta dias anteriores' a fecha_hasta
        df_clientes["fecha_desde"] = df_clientes["fecha_hasta"] - pd.to_timedelta(
            df_clientes["Rango de consulta dias anteriores"], unit="d"
        )

        # Convertimos los datetime a formato str
        df_clientes["fecha_desde"] = df_clientes["fecha_desde"].apply(
            lambda x: x.strftime("%d%m%Y")
        )

        df_clientes["fecha_hasta"] = df_clientes["fecha_hasta"].apply(
            lambda x: x.strftime("%d%m%Y")
        )

        df_clientes["cuit_cliente"] = df_clientes["cuit_cliente"].str.replace("-", "")

        df_clientes["Jurisdiccion"] = df_clientes["Jurisdiccion"].apply(lambda x: x.strip())
        df_clientes["Jurisdiccion"] = df_clientes["Jurisdiccion"].replace(
            jurisdiccion_clases
        )

        df_clientes['Password'] = df_clientes['Password'].apply(lambda x: str(x).strip())

    return df_clientes
