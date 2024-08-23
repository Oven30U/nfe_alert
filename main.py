import asyncio
import glob
import os
import shutil
import zipfile
from datetime import datetime

import pandas as pd
from playwright.async_api import async_playwright

from config import PATH_ESTRUCTURA_ROBOT, CORREO_TEST, LIMITES_REINTENTO, jurisdiccion_clases
from functions.delete_backs import delete_zip_files_in_backup
from conectar_db import conectar_db
from inputs import obtener_clientes
from mail import enviar_correo
from mapa_plot import crear_mapa, crear_mapa_argentina

from jurisdicciones import *


async def main(debug: bool = False, enviar_correo_test: bool = False, headless_state: bool = True,
               ejecutar_todos_clientes: bool = False, ejecutar_clientes_lista: bool = False,
               sin_debug_ejecutar_lista: bool = False,
               clientes_si_verificar_config=None):
    if clientes_si_verificar_config is None:
        clientes_si_verificar_config = []
    async with async_playwright() as playwright:
        df_input = obtener_clientes(debug, ejecutar_todos_clientes, ejecutar_clientes_lista, sin_debug_ejecutar_lista,
                                    clientes_si_verificar_config, jurisdiccion_clases)
        if not df_input.empty:
            # print("df_input esta vacio, finaliza el programa.")
            # return
            df_input_por_cliente = df_input.groupby("Cliente")

            for cliente, group in df_input_por_cliente:
                # Registrar el estado de la ejecución para conectar_db
                inicio_value = datetime.now()
                try:
                    instances = {}
                    jurisdicciones_encontradas = []
                    jurisdicciones_no_encontradas = []
                    for index, row in group.iterrows():
                        jurisdiction = row["Jurisdiccion"]
                        if jurisdiction not in globals():
                            # print(f"Jurisdiccion {jurisdiction} no encontrada, se omite.")
                            jurisdicciones_no_encontradas.append(jurisdiction)
                            continue
                        # print(f"Jurisdiccion {jurisdiction}, se procesará.")
                        jurisdicciones_encontradas.append(jurisdiction)
                        cliente = row["Cliente"]
                        usuario = int(row["Usuario"])
                        password = row["Password"]
                        fecha_desde = row["fecha_desde"].replace("/", "")
                        fecha_hasta = row["fecha_hasta"].replace("/", "")
                        cuit_cliente = int(row["cuit_cliente"])
                        correo_output = row["Correo Output"]

                        # Define the source and destination directories
                        output_folder = f"Estructura-robot/{cliente}/Output"
                        backup_folder = f"Estructura-robot/{cliente}/Backup"
                        # Create the backup folder if it doesn't exist
                        os.makedirs(backup_folder, exist_ok=True)
                        # Get a list of all files in the output folder
                        files = os.listdir(output_folder)
                        # Move each .zip file to the backup folder and delete the rest
                        for file in files:
                            if file.endswith('.zip'):
                                shutil.move(os.path.join(output_folder, file), backup_folder)
                            else:
                                os.remove(os.path.join(output_folder, file))

                        JurisdictionClass = globals()[jurisdiction]

                        create_args = {
                            "playwright": playwright,
                            "cliente": cliente,
                            "cuit": usuario,
                            "clave_fiscal": password,
                            "fecha_desde": fecha_desde,
                            "fecha_hasta": fecha_hasta,
                            "cuit_cliente_input": cuit_cliente,
                        }
                        # Sólo en debug se considera el argumento headless_state,
                        # en producción se utiliza el valor por defecto
                        if debug:
                            create_args["headless"] = headless_state

                        instance = await JurisdictionClass.create(**create_args)
                        instances[jurisdiction] = instance

                    print(f"El cliente {cliente} tiene las siguientes jurisdicciones:")
                    print(f"Jurisdicciones encontradas: {jurisdicciones_encontradas}")
                    print(f"Jurisdicciones no encontradas: {jurisdicciones_no_encontradas}")
                    # Crear una lista de tareas
                    tareas = [
                        instance.procesar_jurisdiccion() for instance in instances.values()
                    ]

                    # Ejecutar todas las tareas de manera concurrente
                    resultados = await asyncio.gather(*tareas)

                    # Convertir resultados de tupla a lista y en DataFrame
                    resultados = [list(res) for res in resultados]
                    df_final_cliente = pd.DataFrame(
                        resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
                    )

                    # Verificar si hay errores
                    errores = df_final_cliente[df_final_cliente["Error"].notna()]
                    for _, error_row in errores.iterrows():
                        jurisdiction = error_row["Nombre"]
                        for _, row in df_input_por_cliente.get_group(cliente).iterrows():
                            if row["Jurisdiccion"] == jurisdiction:
                                JurisdictionClass = globals()[jurisdiction]
                                for intento in range(LIMITES_REINTENTO):  # Limitar a intentos en config.py
                                    # headless = intento % 2 == 0  # Itera entre headless y head full
                                    # Se utiliza el headless definido por defecto en cada Clase de jurisdicciones
                                    instance = await JurisdictionClass.create(
                                        playwright,
                                        row["Cliente"],
                                        int(row["Usuario"]),
                                        row["Password"],
                                        row["fecha_desde"].replace("/", ""),
                                        row["fecha_hasta"].replace("/", ""),
                                        int(row["cuit_cliente"]),
                                        # headless=headless,
                                    )
                                    resultado = await instance.procesar_jurisdiccion()

                                    # Actualizar el DataFrame con el nuevo resultado
                                    df_final_cliente.loc[df_final_cliente["Nombre"] == jurisdiction] = list(resultado)

                                    # Verificar si "Error" es none
                                    if pd.isnull(
                                            df_final_cliente.loc[
                                                df_final_cliente["Nombre"] == jurisdiction, "Error"]).all():
                                        break  # Si "Error" is None, break el loop

                    print(f"{cliente} \n {df_final_cliente}")

                    crear_mapa(df_final_cliente, f"{output_folder}/mapa_jurisdicciones_{cliente}.png")
                    crear_mapa_argentina(df_final_cliente, f"{output_folder}/mapa_nacional_{cliente}.png")

                    now = datetime.now()
                    fecha_actual = now.strftime("%Y%m%d")
                    hora_actual = now.strftime("%H%M")
                    zip_filename = f"{cliente}_{fecha_actual}_{hora_actual}.zip"
                    zip_filepath = f"{output_folder}/{zip_filename}"
                    png_files = glob.glob(f"{output_folder}/*.png")
                    with zipfile.ZipFile(zip_filepath, "w") as zipf:
                        for file in png_files:
                            zipf.write(file, os.path.basename(file))

                    df_adjunto_correo = df_final_cliente[["Nombre", "Notificacion", "Screenshot"]].copy()
                    df_adjunto_correo = df_adjunto_correo.rename(columns={
                        "Nombre": "Jurisdicción",
                        "Notificacion": "Notificaciones",
                        "Screenshot": "Screenshot"
                    })

                    if df_final_cliente["Error"].notna().any():
                        correo_output = CORREO_TEST
                        estado_value = "Proceso terminado con errores"
                    else:
                        estado_value = "Correcto"
                        # # Actualiza hora de Última verificación
                        # PATH_CLIENTES = "Estructura-robot/System/System-Clientes.xlsx"
                        # df_cliente_system = pd.read_excel(PATH_CLIENTES)
                        # now = datetime.now()
                        # current_time = now.strftime("%d/%m/%Y %H:%M:%S")
                        # df_cliente_system.loc[df_cliente_system['Cliente'] == cliente, 'Última verificación'] = current_time
                        # df_cliente_system.to_excel(PATH_CLIENTES, sheet_name="System-Clientes", index=False)

                except Exception as e:
                    print(f"Error en el cliente {cliente}: {e}")
                    estado_value = "Erróneo"

                finally:
                    # Antes de llamar a enviar_correo(), inicializar la variable
                    correo_enviado_exitosamente = False

                    # Con al menos un Incorrecto se envía siempre al correo test
                    # if debug and enviar_correo_test:
                    if enviar_correo_test:
                        correo_output = CORREO_TEST
                    try:
                        enviar_correo(
                            receptor=correo_output,
                            cliente=cliente,
                            ruta_archivo_adjunto=zip_filepath,
                            nombre_archivo_adjunto=zip_filename,
                            df=df_adjunto_correo,
                            ruta_imagen_png=f"{output_folder}/mapa_nacional_{cliente}.png",
                            ruta_imagen_png_2=f"{output_folder}/mapa_jurisdicciones_{cliente}.png",
                            cuerpo_html_plantilla="html/mail_plantilla.html",
                            # cuerpo_html_salida="html/mail_plantilla_salida_con_tabla_ejemplo2.html",
                        )
                        # Si enviar_correo() se ejecuta sin errores, actualizar la variable
                        # Si hay alguna jurisdiccion con error, igualmente se envia y se actualiza la última verificación
                        correo_enviado_exitosamente = True
                    except Exception as e:
                        print(f"Error al enviar correo: {e}")

                    # Actualizar 'Última verificación' sólo si se envio el correo y estado Correcto, sin debug.
                    if correo_enviado_exitosamente and estado_value == "Correcto" and debug is False:
                        # Actualiza hora de Última verificación
                        PATH_CLIENTES = "Estructura-robot/System/System-Clientes.xlsx"
                        df_cliente_system = pd.read_excel(PATH_CLIENTES)
                        now = datetime.now()
                        current_time = now.strftime("%d/%m/%Y %H:%M:%S")
                        df_cliente_system.loc[
                            df_cliente_system['Cliente'] == cliente, 'Última verificación'] = current_time
                        df_cliente_system.to_excel(PATH_CLIENTES, sheet_name="System-Clientes", index=False)

                    username = str(correo_output)

                    proceso = "Revision de Domicilios Fiscales Electronicos"
                    conectar_db(proceso, cliente, username, inicio_value, estado_value)

        elif df_input.empty:
            inicio_value = datetime.now()
            estado_value = "Correcto"
            correo_enviado_exitosamente = True  # No se envia correo en este caso
            username = 'TaxTech'
            cliente = 'TaxTech'

            proceso = "Revision de Domicilios Fiscales Electronicos"
            conectar_db(proceso, cliente, username, inicio_value, estado_value)

        # proceso = "Revision de Domicilios Fiscales Electronicos"
        # conectar_db(proceso, cliente, username, inicio_value, estado_value)

        # Eliminar los archivos .zip en la carpeta de Backup
        delete_zip_files_in_backup(PATH_ESTRUCTURA_ROBOT)

        return estado_value, correo_enviado_exitosamente


if __name__ == "__main__":
    import asyncio

    estado_value, correo_enviado_exitosamente = asyncio.run(main(debug=False, enviar_correo_test=False))

    print(f"Estado: {estado_value}, Correo enviado exitosamente: {correo_enviado_exitosamente}")
