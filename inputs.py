import os
import sys
import pandas as pd
import datetime
from jurisdiccion import LoggedException
from cliente_system import ClienteSystem

class InputException(LoggedException):
    """Excepción lanzada por errores en la captura de los input."""

    pass


def obtener_clientes():
    # Define la ruta al archivo
    PATH_BOT = "Estructura-robot/"
    PATH_SYSTEM = "Estructura-robot/System/"
    PATH_ERRORES = "Estructura-robot/System/errores/"
    # PATH_JURISDICCIONES = f"{PATH_SYSTEM}System-Links.xlsx"
    PATH_CLIENTES = f"{PATH_SYSTEM}System-Clientes.xlsx"
    PATH_CREDENCIALES = f"{PATH_SYSTEM}System-Credenciales.xlsm"

    # # Lee el archivo Excel y lo guarda en un DataFrame
    # try:
    #     df_path_jurisdicciones = pd.read_excel(PATH_JURISDICCIONES)
    # except Exception as e:
    #     raise InputException(
    #         f"No se pudo acceder al archivo  PATH_JURISDICCIONES, {e}"
    #     )

    # Obtenemos los clientes a verificar del archivo system/System-Clientes.xlsx
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

        if cliente_system.verificar_ejecucion(archivo_input_a_verificar):
            clientes_si_verificar.append(cliente_system)
        else:
            clientes_no_verificar.append(cliente_system)

    if not clientes_si_verificar:
        print("No hay clientes por verificar en este momento")
        sys.exit()
    else:
        print(
            f"Clientes a verificar: {', '.join([cliente.nombre for cliente in clientes_si_verificar])}"
        )


    try:
        df_credenciales = pd.read_excel(PATH_CREDENCIALES)
    except Exception as e:
        raise InputException(
            f"No se pudo acceder al archivo {PATH_CREDENCIALES}, {e}"
        )
        print("No se pudo acceder al archivo %s: %s", PATH_CREDENCIALES, str(e))

    try:
        df_correo_output = pd.read_excel(
            PATH_CLIENTES, sheet_name="System-Clientes", usecols="A:B"
        )
    except Exception as e:
        raise InputException(f"No se pudo acceder al archivo, PATH_CLIENTES, {e}")
        print("No se pudo acceder al archivo %s: %s", PATH_CLIENTES, str(e))

    # Obtiene una lista de todos los nombres de las carpetas en el directorio
    folder_names = [
        name for name in os.listdir(PATH_BOT) if os.path.isdir(os.path.join(PATH_BOT, name))
    ]

    # Elimina "System" de la lista si está presente
    if "System" in folder_names:
        folder_names.remove("System")

    #! Supongamos que tienes tus datos listos
    # clientes_si_verificar es una lista de objetos, así que la convertimos en un DataFrame
    clientes_si_verificar = [
        {'Cliente': cliente.nombre, 'Correo Output': cliente.correo_output} 
        for cliente in clientes_si_verificar
    ]
    df_clientes_si_verificar = pd.DataFrame(clientes_si_verificar)

    # archivo_input_verificar ya debería ser un DataFrame
    # df_credenciales ya es un DataFrame

    try:
        archivo_input_verificar = pd.read_excel(f"{PATH_BOT}{cliente_system.nombre}/Input")
        archivo_input_verificar.columns = ['Cliente', 'CUIT', 'rango_dias']
    except Exception as e:
        raise InputException(f"No se pudo acceder al archivo, PATH_INPUT_VERIFICAR, {e}")
        print("No se pudo acceder al archivo")

    # Asegurémonos de que los nombres de las columnas coincidan en todos los DataFrames
    archivo_input_verificar.columns = ['Cliente', 'CUIT', 'rango_dias']

    # Unir archivo_input_verificar con df_credenciales en base a Cliente
    df_merge = pd.merge(archivo_input_verificar, df_credenciales, on='Cliente', how='inner')

    # Calcular las fechas
    fecha_hasta = datetime.now()
    df_merge['fecha_hasta'] = fecha_hasta
    df_merge['fecha_desde'] = df_merge['fecha_hasta'] - pd.to_timedelta(df_merge['rango_dias'], unit='D')

    # Crear el DataFrame final con las columnas requeridas
    df_final = df_merge[['Cliente', 'CUIT', 'Password', 'fecha_desde', 'fecha_hasta']]
    df_final.rename(columns={'CUIT': 'cuit_cliente'}, inplace=True)

    # Para agregar el Usuario en base a Cliente
    df_final = df_final.merge(df_credenciales[['Cliente', 'Usuario']], on='Cliente', how='inner')

    # Renombrar columnas según lo requerido
    df_final.rename(columns={'Usuario': 'CUIT'}, inplace=True)

    print(df_final)

    #!
    data = []
    
    for cliente in clientes_si_verificar:
        nombre_cliente = cliente.nombre
        archivo_input = pd.read_excel(f"{PATH_BOT}{nombre_cliente}/Input/DFE-Input-Cliente.xlsx")
        nombre_cliente_input = archivo_input.iloc[0, 0]  # A2 cell is at index (1, 0)
        jurisdiccion_input = archivo_input['Jurisdiccion'].values[0]
    
        if nombre_cliente == nombre_cliente_input:
            credenciales_cliente = df_credenciales[(df_credenciales['Cliente'] == nombre_cliente) & (df_credenciales['Jurisdiccion'] == jurisdiccion_input)]
    
            if not credenciales_cliente.empty:
                cuit = credenciales_cliente['cuit'].values[0]
                clave_fiscal = credenciales_cliente['clave_fiscal'].values[0]
    
                dias = archivo_input.iloc[1, 2]  # C2 cell is at index (1, 2)
                fecha_hasta = datetime.date.today()
                fecha_desde = fecha_hasta - datetime.timedelta(days=dias)
                cuit_cliente = archivo_input['cuit_cliente'].values[0]
    
                data.append({
                    'Cliente': nombre_cliente,
                    'cuit': cuit,
                    'clave_fiscal': clave_fiscal,
                    'fecha_desde': fecha_desde,
                    'fecha_hasta': fecha_hasta,
                    'cuit_cliente': cuit_cliente
                })
    
    df = pd.DataFrame(data)
    print(df)


if __name__ == '__main__':
    clientes_si_verificar, clientes_no_verificar = obtener_clientes()
    # print(
    #     f"Clientes a verificar: {', '.join([cliente.nombre for cliente in clientes_si_verificar])}"
    # )
