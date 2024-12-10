import asyncio
import glob
import os
import shutil
import sqlite3
from datetime import date, datetime

import pandas as pd
import pyzipper
from playwright.async_api import async_playwright

from conectar_db import conectar_db, get_pass_zip
from config import (
    CORREO_NOTIFICACION_ERROR,
    CORREO_TEST,
    ENVIAR_CORREO_TEST,
    LIMITES_REINTENTO,
    PATH_ESTRUCTURA_ROBOT,
    jurisdiccion_clases,
)
from functions.delete_backs import delete_zip_files_in_backup
from inputs import obtener_clientes
import jurisdicciones
from mail import enviar_correo
from mapa_plot import crear_mapa, crear_mapa_argentina

pd.set_option("display.max_columns", None)


async def main():
    async with async_playwright() as playwright:

        df_input = obtener_datos_clientes()
        if df_input.empty:
            registrar_sin_clientes()
            return

        df_por_cliente = df_input.groupby("Cliente")

        for cliente, group in df_por_cliente:
            inicio = datetime.now()
            output_folder, backup_folder = preparar_directorios(cliente)
            respaldar_archivos(output_folder, backup_folder)

            correo_output = obtener_correo(group)
            socio_responsable = obtener_socio(group)

            zip_path = None
            zip_name = None

            try:
                instances, encontradas, no_encontradas = await procesar_jurisdicciones(
                    playwright, group
                )

                print(f"Cliente: {cliente}")
                print(f"Jurisdicciones encontradas: {encontradas}")
                print(f"Jurisdicciones no encontradas: {no_encontradas}")

                df_final = await ejecutar_jurisdicciones(instances)
                df_final = await reintentar_errores(playwright, df_final, group)

                print(f"{cliente}\n{df_final}")

                generar_mapas(df_final, output_folder, cliente)
                zip_path, zip_name = crear_zip(df_final, output_folder, cliente)

                estado = (
                    "Correcto"
                    if df_final["Error"].isna().all()
                    else "Proceso terminado con errores"
                )
            except Exception as e:
                print(f"Error en el cliente {cliente}: {e}")
                estado = "Erróneo"
            finally:
                correo_exitoso = enviar_email(
                    df_final, zip_path, zip_name, output_folder, cliente, group
                )
                if not correo_exitoso:
                    estado = "Correo no enviado"
                username = obtener_username(correo_output, socio_responsable)
                registrar_ejecucion(
                    proceso="NFE Alert",
                    cliente=cliente,
                    username=username,
                    inicio=inicio,
                    estado=estado,
                )

        delete_zip_files_in_backup(PATH_ESTRUCTURA_ROBOT)


def obtener_datos_clientes():
    df_clientes = obtener_clientes(
        jurisdiccion_clases=jurisdiccion_clases,
    )

    # Obtener lista de clientes procesados hoy con estado 'Correcto'
    clientes_procesados_hoy = get_clientes_procesados_hoy()

    # Filtrar los clientes ya procesados
    if not df_clientes.empty and clientes_procesados_hoy:
        df_clientes = df_clientes[~df_clientes["Cliente"].isin(clientes_procesados_hoy)]

    return df_clientes


def get_clientes_procesados_hoy():
    conn = sqlite3.connect("pruebas/database.db")
    cursor = conn.cursor()

    today = date.today().strftime("%Y-%m-%d")

    query = """
        SELECT Cliente FROM monitoreo_bots
        WHERE estado = 'Correcto' AND DATE(iniciado) = ?
        UNION
        SELECT Cliente FROM monitoreo_bots_backup
        WHERE estado = 'Correcto' AND DATE(iniciado) = ?
    """

    cursor.execute(query, (today, today))
    rows = cursor.fetchall()

    clientes_procesados = [row[0] for row in rows]

    conn.close()

    return clientes_procesados


def preparar_directorios(cliente):
    base_folder = f"Estructura-robot/{cliente}"
    output_folder = os.path.join(base_folder, "Output")
    backup_folder = os.path.join(base_folder, "Backup")
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(backup_folder, exist_ok=True)
    return output_folder, backup_folder


def respaldar_archivos(output_folder, backup_folder):
    files = os.listdir(output_folder)
    for file in files:
        file_path = os.path.join(output_folder, file)
        if file.endswith(".zip"):
            shutil.move(file_path, backup_folder)
        else:
            os.remove(file_path)


async def procesar_jurisdicciones(playwright, group):
    instances = {}
    encontradas = []
    no_encontradas = []

    for _, row in group.iterrows():
        jurisdiction = row["Jurisdiccion"]
        # Check if the jurisdiction class exists in the jurisdicciones module
        if not hasattr(jurisdicciones, jurisdiction):
            no_encontradas.append(jurisdiction)
            continue
        encontradas.append(jurisdiction)
        instance = await crear_instancia_jurisdiccion(playwright, row, jurisdiction)
        instances[jurisdiction] = instance
    return instances, encontradas, no_encontradas


async def crear_instancia_jurisdiccion(playwright, row, jurisdiction):
    # Get the class from the jurisdicciones module
    JurisdictionClass = getattr(jurisdicciones, jurisdiction)
    create_args = {
        "playwright": playwright,
        "cliente": row["Cliente"],
        "cuit": int(row["Usuario"]),
        "clave_fiscal": row["Password"],
        "fecha_desde": row["fecha_desde"],
        "fecha_hasta": row["fecha_hasta"],
        "cuit_cliente_input": int(row["cuit_cliente"]),
    }
    return await JurisdictionClass.create(**create_args)


async def ejecutar_jurisdicciones(instances):
    tareas = [instance.procesar_jurisdiccion() for instance in instances.values()]
    resultados = await asyncio.gather(*tareas)
    resultados = [list(res) for res in resultados]
    return pd.DataFrame(
        resultados, columns=["Nombre", "Notificacion", "Screenshot", "Error"]
    )


async def reintentar_errores(playwright, df_final, group):
    errores = df_final[df_final["Error"].notna()]
    for _, error_row in errores.iterrows():
        jurisdiction = error_row["Nombre"]
        row = group[group["Jurisdiccion"] == jurisdiction].iloc[0]
        for _ in range(LIMITES_REINTENTO):
            instance = await crear_instancia_jurisdiccion(playwright, row, jurisdiction)
            resultado = await instance.procesar_jurisdiccion()
            df_final.loc[df_final["Nombre"] == jurisdiction] = list(resultado)
            if pd.isna(df_final.loc[df_final["Nombre"] == jurisdiction, "Error"]).all():
                break
    return df_final


def generar_mapas(df_final, output_folder, cliente):
    crear_mapa(df_final, f"{output_folder}/mapa_jurisdicciones_{cliente}.png")
    crear_mapa_argentina(df_final, f"{output_folder}/mapa_nacional_{cliente}.png")


def crear_zip(df_final, output_folder, cliente):
    now = datetime.now()
    fecha_actual = now.strftime("%Y%m%d")
    hora_actual = now.strftime("%H%M")
    zip_name = f"{cliente}_{fecha_actual}_{hora_actual}.zip"
    zip_path = os.path.join(output_folder, zip_name)
    png_files = glob.glob(os.path.join(output_folder, "*.png"))

    pass_zip = get_pass_zip(
        cliente, f"{obtener_correo(df_final)};{obtener_socio(df_final)}"
    )
    with pyzipper.AESZipFile(
        zip_path,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zipf:
        zipf.setpassword(pass_zip.encode("utf-8"))
        for file in png_files:
            zipf.write(file, os.path.basename(file))

    return zip_path, zip_name


def obtener_correo(group):
    if ENVIAR_CORREO_TEST:
        return CORREO_TEST
    if "Correo Output" in group.columns:
        correo_output = group["Correo Output"].iloc[0]
        return correo_output if pd.notna(correo_output) else None
    else:
        return None


def obtener_socio(group):
    if "Socio responsable" in group.columns:
        socio_responsable = group["Socio responsable"].iloc[0]
        return socio_responsable if pd.notna(socio_responsable) else None
    else:
        return None


def enviar_email(df_final, zip_path, zip_name, output_folder, cliente, group):
    try:
        df_correo = df_final[["Nombre", "Notificacion", "Screenshot"]].rename(
            columns={
                "Nombre": "Jurisdicción",
                "Notificacion": "Notificaciones",
                "Screenshot": "Screenshot",
            }
        )

        correo_output = obtener_correo(group)
        socio_responsable = obtener_socio(group)

        if not correo_output and not socio_responsable:
            receptor = CORREO_NOTIFICACION_ERROR
            cc = None
        elif correo_output:
            receptor = correo_output
            cc = socio_responsable if socio_responsable else None
        elif socio_responsable:
            receptor = socio_responsable
            cc = None
        else:
            raise ValueError("No valid email address found for sending the email.")

        if receptor is None:
            raise ValueError("Receptor email address is None. Cannot send email.")

        enviar_correo(
            receptor=receptor,
            cliente=cliente,
            ruta_archivo_adjunto=zip_path,
            nombre_archivo_adjunto=zip_name,
            df=df_correo,
            ruta_imagen_png=f"{output_folder}/mapa_nacional_{cliente}.png",
            ruta_imagen_png_2=f"{output_folder}/mapa_jurisdicciones_{cliente}.png",
            cuerpo_html_plantilla="html/mail_plantilla.html",
            cc=cc,
        )
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False


def obtener_username(correo_output, socio_responsable):
    if correo_output:
        return correo_output
    elif socio_responsable:
        return socio_responsable
    else:
        return "No definido"


def registrar_ejecucion(proceso, cliente, username, inicio, estado):
    conectar_db(
        proceso=proceso,
        cliente=cliente,
        username=username,
        inicio_value=inicio,
        estado_value=estado,
    )


def registrar_sin_clientes():
    proceso = "Revision de Domicilios Fiscales Electronicos"
    cliente = "TaxTech"
    username = "TaxTech"
    estado_value = "Correcto"
    inicio_value = datetime.now()

    conectar_db(
        proceso=proceso,
        cliente=cliente,
        username=username,
        inicio_value=inicio_value,
        estado_value=estado_value,
    )


if __name__ == "__main__":
    asyncio.run(main())
