"""
Este módulo proporciona una función para enviar correos electrónicos utilizando Microsoft Outlook.
Es necesario que la cuenta logueada en Outlook tenga acceso a la casilla de
sender_email que utiliza la variable de entorno SENDER_EMAIL_BEHAL.
Puede utilizarse cómo BackUp en caso de no poder utilizar SMTP.

Funciones:
- enviar_correo_outlook: Envía un correo electrónico utilizando Outlook 
con la posibilidad de adjuntar archivos, incluir tablas y mapas en el cuerpo del correo,
y personalizar el contenido HTML.

Dependencias:
- win32com.client
- os
- datetime
- config (mapa_jurisdiccion_clases)
- generar_html (convertir_imagen_en_html, grabar_html, insertar_mapas_en_html, insertar_tabla_en_html, reemplazar_contenido_en_html)
- pandas
- dotenv (load_dotenv)

Variables de entorno requeridas:
- SENDER_EMAIL_BEHAL: Correo electrónico del remitente en nombre del cual se enviará el correo.
- CORREO_RECEPTOR_TEST_MAIL: Correo electrónico del receptor para pruebas.

Ejemplo de uso:
    receptor=["receptor@example.com"],
    ruta_archivo_adjunto="ruta/al/archivo.pdf",
    nombre_archivo_adjunto="archivo.pdf",
    df=dataframe,
    ruta_imagen_png="ruta/a/imagen1.png",
    ruta_imagen_png_2="ruta/a/imagen2.png",
    cc=["cc@example.com"],

"""

import win32com.client as win32
import os
from datetime import datetime
from config import mapa_jurisdiccion_clases
from generar_html import (
    convertir_imagen_en_html,
    grabar_html,
    insertar_mapas_en_html,
    insertar_tabla_en_html,
    reemplazar_contenido_en_html,
)
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # Cargar las variables de entorno desde el archivo .env


def enviar_correo_outlook(
    receptor,
    cliente,
    ruta_archivo_adjunto=None,
    nombre_archivo_adjunto=None,
    df=None,
    ruta_imagen_png=None,
    ruta_imagen_png_2=None,
    cuerpo_html_plantilla="html/mail_plantilla.html",
    cc=None,
):
    """
    Envía un correo electrónico utilizando Outlook.
    """
    try:
        # Inicializar la aplicación Outlook
        outlook = win32.Dispatch("outlook.application")
        mail = outlook.CreateItem(0)  # 0: olMailItem

        # Configurar destinatarios
        mail.To = "; ".join(receptor)
        mail.CC = "; ".join(cc) if cc else ""
        sender_email = os.getenv("SENDER_EMAIL_BEHAL")
        if sender_email:
            mail.SentOnBehalfOfName = sender_email
        else:
            print(
                "Advertencia: SENDER_EMAIL no está definido en las variables de entorno."
            )

        # Asunto del correo
        mail.Subject = f"NFE Alert: Revisión de Domicilios Fiscales Electrónicos del cliente {cliente}"

        # Adjuntar archivo si se proporciona
        if ruta_archivo_adjunto and nombre_archivo_adjunto:
            attachment_path = os.path.abspath(ruta_archivo_adjunto)
            mail.Attachments.Add(attachment_path, 1, None, nombre_archivo_adjunto)

        # Crear el cuerpo del correo
        if df is not None:
            try:
                mapa_provincias_html = convertir_imagen_en_html(ruta_imagen_png)
                mapa_argentina_html = convertir_imagen_en_html(ruta_imagen_png_2)

                df["Jurisdicción"] = df["Jurisdicción"].replace(
                    mapa_jurisdiccion_clases
                )
                html_con_tabla = insertar_tabla_en_html(
                    df,
                    cuerpo_html_plantilla,
                    "id",
                    "tabla_jurisdicciones",
                )
                html_con_tabla_y_mapas = insertar_mapas_en_html(
                    mapa_provincias_html, mapa_argentina_html, html_con_tabla
                )

                # Obtener el día actual
                dia_actual = datetime.today().strftime("%d/%m/%Y")
                html_con_tabla_mapas_y_dia = reemplazar_contenido_en_html(
                    html_con_tabla_y_mapas,
                    "id",
                    "span-fecha-dinamica",
                    f"Deloitte Argentina | Impuestos | {dia_actual}",
                )
                archivo_html_a_enviar = grabar_html(cliente, html_con_tabla_mapas_y_dia)

                with open(archivo_html_a_enviar, "r", encoding="utf-8") as f:
                    html_content = f.read()
                mail.HTMLBody = html_content
            except Exception as e:
                print(f"Error al generar el contenido HTML del correo: {e}")
                mail.Body = "Este es el cuerpo del correo en texto plano."
        else:
            mail.Body = "Este es el cuerpo del correo en texto plano."

        # Enviar el correo
        mail.Send()
        print("Correo enviado exitosamente a través de Outlook.")
    except Exception as e:
        print(f"Error al enviar el correo electrónico: {e}")


if __name__ == "__main__":
    enviar_correo_outlook(
        receptor=[os.getenv("CORREO_RECEPTOR_TEST_MAIL")],
        cliente="Cliente S.R.L",
        ruta_archivo_adjunto=None,
        nombre_archivo_adjunto=None,
        df=None,
        ruta_imagen_png=None,
        ruta_imagen_png_2=None,
        cuerpo_html_plantilla=None,
        cc=[os.getenv("CORREO_RECEPTOR_TEST_MAIL")],
    )
