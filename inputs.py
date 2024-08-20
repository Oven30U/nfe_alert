import os
import pandas as pd
from datetime import datetime
from jurisdicciones.jurisdiccion import LoggedException
from cliente_system import ClienteSystem
from win32com.client import Dispatch


class InputException(LoggedException):
    """Excepción lanzada por errores en la captura de los input."""

    pass


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
                    if (nombre in libro.Name):
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


def verificar_cliente(cliente_system, archivo_input_a_verificar, clientes_si_verificar_config, clientes_si_verificar,
                      clientes_no_verificar):
    if cliente_system.nombre in clientes_si_verificar_config:
        clientes_si_verificar.append(cliente_system)
    else:
        clientes_no_verificar.append(cliente_system)


def verificar_clientes(cliente_system, archivo_input_a_verificar, debug, ejecutar_todos_clientes,
                       ejecutar_clientes_lista, sin_debug_ejecutar_ejecutar_lista, clientes_si_verificar_config,
                       clientes_si_verificar,
                       clientes_no_verificar):
    """
    Verifica los clientes según las configuraciones y los agrega a las listas correspondientes.

    Parámetros:
    - cliente_system: Objeto ClienteSystem que representa al cliente a verificar.
    - archivo_input_a_verificar: Ruta del archivo de input a verificar.
    - debug: Booleano que indica si el modo debug está activado.
    - ejecutar_todos_clientes: Booleano que indica si se deben ejecutar todos los clientes.
    - ejecutar_clientes_lista: Booleano que indica si se deben ejecutar los clientes de la lista.
    - clientes_si_verificar_config: Lista de nombres de clientes que se deben verificar.
    - clientes_si_verificar: Lista donde se agregarán los clientes que se deben verificar.
    - clientes_no_verificar: Lista donde se agregarán los clientes que no se deben verificar.
    """
    if debug:
        if ejecutar_todos_clientes:
            clientes_si_verificar.append(cliente_system)
        elif ejecutar_clientes_lista:
            verificar_cliente(cliente_system, archivo_input_a_verificar, clientes_si_verificar_config,
                              clientes_si_verificar, clientes_no_verificar)
        else:
            verificar_cliente(cliente_system, archivo_input_a_verificar, clientes_si_verificar_config,
                              clientes_si_verificar, clientes_no_verificar)
    else:
        if sin_debug_ejecutar_ejecutar_lista:
            verificar_cliente(cliente_system, archivo_input_a_verificar, clientes_si_verificar_config,
                              clientes_si_verificar, clientes_no_verificar)
        elif cliente_system.verificar_ejecucion(archivo_input_a_verificar):
            clientes_si_verificar.append(cliente_system)
        else:
            clientes_no_verificar.append(cliente_system)


def obtener_clientes(debug, ejecutar_todos_clientes, ejecutar_clientes_lista, sin_debug_ejecutar_ejecutar_lista,
                     clientes_si_verificar_config,
                     jurisdiccion_clases):
    PATH_BOT = "Estructura-robot/"
    PATH_SYSTEM = "Estructura-robot/System/"
    PATH_ERRORES = "Estructura-robot/System/errores/"
    PATH_CLIENTES = f"{PATH_SYSTEM}System-Clientes.xlsx"
    PATH_CREDENCIALES = f"{PATH_SYSTEM}System-Credenciales.xlsm"

    nombres_archivos_excel = [
        "System-Clientes.xlsx",
        "System-Credenciales.xlsm",
        "DFE - Input - Cliente.xlsx"
    ]
    cerrar_excel(nombres_archivos_excel)

    try:
        df_clientes = pd.read_excel(PATH_CLIENTES, sheet_name="System-Clientes")
    except Exception as e:
        raise InputException(f"No se pudo acceder al archivo, PATH_CLIENTES, {e}")
        print("No se pudo acceder al archivo %s: %s", PATH_CLIENTES, str(e))

    clientes_si_verificar = []
    clientes_no_verificar = []

    for cliente_system in df_clientes.iterrows():
        cliente_system = ClienteSystem(
            cliente_system[1]["Cliente"],
            cliente_system[1]["Correo Output"],
            cliente_system[1]["Personas autorizadas"],
            cliente_system[1]["Schedule"],
            cliente_system[1]["Dia/s de ejecución"],
            cliente_system[1]["Hora de inicio"],
            cliente_system[1]["Última verificación"],
        )
        archivo_input_a_verificar = f"{PATH_BOT}{cliente_system.nombre}/Input"

        verificar_clientes(cliente_system, archivo_input_a_verificar, debug, ejecutar_todos_clientes,
                           ejecutar_clientes_lista, sin_debug_ejecutar_ejecutar_lista, clientes_si_verificar_config,
                           clientes_si_verificar,
                           clientes_no_verificar)

    df_final = pd.DataFrame()
    if not clientes_si_verificar:
        print("No hay clientes por verificar en este momento")
        return df_final
    else:
        print(
            f"\nClientes SI verificar: {', '.join([cliente.nombre for cliente in clientes_si_verificar])}\n"
        )
        print(
            f"\nClientes NO verificar: {', '.join([cliente.nombre for cliente in clientes_no_verificar])}\n"
        )

    try:
        df_credenciales = pd.read_excel(PATH_CREDENCIALES)
    except Exception as e:
        raise InputException(f"No se pudo acceder al archivo {PATH_CREDENCIALES}, {e}")
        print("No se pudo acceder al archivo %s: %s", PATH_CREDENCIALES, str(e))
    df_credenciales["Cliente"] = df_credenciales["Cliente"].str.rstrip('.')

    # Obtiene una lista de todos los nombres de las carpetas en el directorio
    folder_names = [
        name
        for name in os.listdir(PATH_BOT)
        if os.path.isdir(os.path.join(PATH_BOT, name))
    ]

    if "System" in folder_names:
        folder_names.remove("System")

    clientes_si_verificar = [
        {"Cliente": cliente.nombre, "Correo Output": cliente.correo_output}
        for cliente in clientes_si_verificar
    ]
    df_clientes_si_verificar = pd.DataFrame(clientes_si_verificar)

    fecha_actual = datetime.today()
    for index, row in df_clientes_si_verificar.iterrows():
        cliente_nombre = row["Cliente"]
        correo_output = row["Correo Output"]
        try:
            path_archivo_input = (
                f"{PATH_BOT}{cliente_nombre}/Input/DFE-Input-Cliente.xlsx"
            )
            archivo_input = pd.read_excel(path_archivo_input)
            df_input = pd.read_excel(path_archivo_input, header=4)

        except Exception as e:
            raise InputException(
                cliente_nombre,
                f"No se pudo acceder al archivo, PATH_INPUT_VERIFICAR, {e}",
            )
            print("No se pudo acceder al archivo")

        df_input = df_input[df_input["Consultar"] == "Si"]
        df_input["Cliente"] = cliente_nombre
        df_input["Correo Output"] = correo_output
        df_input["fecha_hasta"] = fecha_actual
        rango_dias = archivo_input.iloc[0, 2]
        df_input['cuit_cliente'] = archivo_input.iloc[0, 1].replace('-', '')
        df_input["fecha_desde"] = df_input["fecha_hasta"] - pd.to_timedelta(
            rango_dias, unit="D"
        )
        df_input["fecha_desde"] = df_input["fecha_desde"].dt.strftime("%d/%m/%Y")
        df_input["fecha_hasta"] = df_input["fecha_hasta"].dt.strftime("%d/%m/%Y")
        df_final = pd.concat([df_final, df_input])

    # Resetea el índice del DataFrame final
    df_final.reset_index(drop=True, inplace=True)

    df_final = df_final.merge(
        df_credenciales[["Cliente", "Jurisdiccion", "Usuario", "Password"]],
        on=["Cliente", "Jurisdiccion"],
        how="left",
    )
    # Crear df_sin_credenciales con las filas donde 'Usuario' y 'Password' son NaN
    df_sin_credenciales = df_final[
        df_final["Usuario"].isna() & df_final["Password"].isna()
        ]

    # Eliminar las filas de df_final donde 'Usuario' y 'Password' son NaN
    df_final = df_final.dropna(subset=["Usuario", "Password"])

    # Reemplazamos df_final['Jurisdiccion'], por el nombre de la clase
    df_final['Jurisdiccion'] = df_final['Jurisdiccion'].replace(jurisdiccion_clases)

    return df_final


if __name__ == "__main__":
    df_final = obtener_clientes()
    print(df_final)
