import asyncio
import glob
import os
import shutil
import zipfile
from datetime import datetime

import pandas as pd
from playwright.async_api import async_playwright

from agip import Agip
from arba import Arba
from chubut import Chubut
from cordoba import Cordoba
from entre_rios import EntreRios
from inputs import obtener_clientes
from jujuy import Jujuy
from mail import enviar_correo
from mapa_plot import crear_mapa, crear_mapa_argentina
from mendoza import Mendoza
from misiones import Misiones
from nacional import Nacional
from neuquen import Neuquen
from rio_negro import RioNegro
from tucuman import Tucuman


async def main():
    async with async_playwright() as playwright:
        df_input = obtener_clientes()
        df_input_por_cliente = df_input.groupby("Cliente")

        # Mapea nombre de las instancias
        jurisdiccion_clases = {
            "Nacional": Nacional,
            "AGIP": Agip,
            "ARBA": Arba,
            "Mendoza": Mendoza,
            "Cordoba": Cordoba,
            "Neuquen": Neuquen,
            "Rio Negro": RioNegro,
            "Tucuman": Tucuman,
            "Misiones": Misiones,
            "Entre Rios": EntreRios,
            "Jujuy": Jujuy,
            "Chubut": Chubut,
        }
        for cliente, group in df_input_por_cliente:
            instances = {}
            for index, row in group.iterrows():
                jurisdiction = row["Jurisdiccion"]
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

                JurisdictionClass = jurisdiccion_clases[jurisdiction]

                # Use the globals() function to get the class by name
                # JurisdictionClass = globals()[jurisdiction]
                instance = await JurisdictionClass.create(
                    playwright,
                    cliente,
                    usuario,
                    password,
                    fecha_desde,
                    fecha_hasta,
                    cuit_cliente,
                )
                instances[jurisdiction] = instance

            # Crear una lista de tareas
            tareas = [
                instance.procesar_jurisdiccion() for instance in instances.values()
            ]

            # Ejecutar todas las tareas de manera concurrente
            resultados = await asyncio.gather(*tareas)

            # # Cerrar todas las instancias de navegador
            # for instance in instances.values():
            #     await instance.browser.close()

            # Convertir resultados de tupla a lista y en DataFrame
            resultados = [list(res) for res in resultados]
            df_final_cliente = pd.DataFrame(
                resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
            )

            # Verificar errores y volver a ejecutar si es necesario, hasta 5 veces
            for _ in range(5):
                for index, row in df_final_cliente.iterrows():
                    if row["Error"] is not None:
                        instance = instances[row["Nombre"]]
                        result = await instance.procesar_jurisdiccion()
                        df_final_cliente.loc[index] = list(result)
                if not df_final_cliente["Error"].any():
                    break

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

            # #! Comentado hasta testear
            # Actualiza hora de Última verificación
            PATH_CLIENTES = "Estructura-robot/System/System-Clientes.xlsx"
            df_cliente_system = pd.read_excel(PATH_CLIENTES)
            now = datetime.now()
            current_time = now.strftime("%d-%m-%Y %H:%M")
            df_cliente_system.loc[df_cliente_system['Cliente'] == cliente, 'Última verificación'] = current_time
            df_cliente_system.to_excel(PATH_CLIENTES, sheet_name="System-Clientes", index=False)

if __name__ == "__main__":
    asyncio.run(main())
