"""
Este módulo proporciona una función para enviar correos electrónicos
con archivos adjuntos y/o contenido HTML generado a partir de un DataFrame.
Funciones:
- enviar_correo: Envía un correo electrónico
    con un archivo adjunto y/o un DataFrame en el cuerpo del correo.
Dependencias:
- smtplib
- datetime
- email.encoders
- email.mime.base
- email.mime.multipart
- email.mime.text
- config (mapa_jurisdiccion_clases)
- generar_html (convertir_imagen_en_html,
    grabar_html, insertar_mapas_en_html, insertar_tabla_en_html,
    reemplazar_contenido_en_html)
Ejemplo de uso:
    receptor="socio@deloitte.com",
    cliente="Cliente S.R.L.",
    ruta_archivo_adjunto="mail.zip",
    ruta_imagen_png="mapa.png",
    ruta_imagen_png_2="mapa2.png",
    cc=["cc@example.com"]
"""

import os
import smtplib
import ssl
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTPNotSupportedError, SMTPException
from logger import Logger
from datetime import datetime

from config import mapa_jurisdiccion_clases
from generar_html import (
    convertir_imagen_en_html,
    grabar_html,
    insertar_mapas_en_html,
    insertar_tabla_en_html,
    reemplazar_contenido_en_html,
)

logger = Logger.get_logger()

def enviar_correo(
    receptor,
    cliente,
    cuit,
    inicio,
    ruta_archivo_adjunto=None,
    nombre_archivo_adjunto=None,
    df=None,
    ruta_imagen_png=None,
    ruta_imagen_png_2=None,
    cuerpo_html_plantilla="html/mail_plantilla.html",
    cc=None,
):
    """
    Esta función envía un correo electrónico
    con un archivo adjunto y/o un DataFrame en el cuerpo del correo.

    Parámetros:
    receptor (str): El correo electrónico del receptor.
    cliente (str): El nombre del cliente.
    ruta_archivo_adjunto (str): La ruta al archivo que se adjuntará.
    nombre_archivo_adjunto (str): El nombre del archivo adjunto.
    df (pandas.DataFrame): El DataFrame que se incluirá en el cuerpo del correo.
    cc (list): Lista de correos electrónicos para enviar en copia.

    Retorna:
    None

    Ejemplo:
    enviar_correo("socio@deloitte.com",
        "Cliente S.R.L.",
        "mail.zip",
        df=df_output_final,
        ruta_mapa_html="map.html",
        cc=["cc@example.com"])
    """

    servidor_smtp = os.getenv("SERVIDOR_SMTP")
    puerto_smtp = os.getenv("PUERTO_SMTP")

    # Asegurarse de que 'receptor' es una lista y no un string
    if not isinstance(receptor, list):
        receptor = receptor.split(';')

    # Asegurarse de que 'cc' es una lista y no un string
    if cc is None:
        cc = []
    elif not isinstance(cc, list):
        cc = cc.split(';')

    # Crear el mensaje
    msg = MIMEMultipart()
    msg["From"] = os.getenv("CORREO_REMITENTE")
    msg["To"] = ",".join(receptor)
    msg["Cc"] = ",".join(cc) if cc else ""
    correos_rpa = os.getenv("CORREOS_RPA").split(",")
    # Dividir la cadena en varias cadenas utilizando el method split()
    receptor = receptor[0].split(";")
    receptor.extend(correos_rpa)
    # Eliminar duplicados de la lista de receptores
    receptor = list(set(receptor))
    msg["Subject"] = (
        f"{cliente} - NFE Alert_Revisión de Domicilios Fiscales Electrónicos"
    )

    # Adjuntar el archivo si se proporciona
    if ruta_archivo_adjunto is not None and nombre_archivo_adjunto is not None:
        part = MIMEBase("application", "octet-stream")
        with open(ruta_archivo_adjunto, "rb") as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", "attachment", filename=nombre_archivo_adjunto
        )
        msg.attach(part)

    # Creamos el cuerpo del mensaje
    if df is not None:
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

        dia_actual = datetime.today().strftime("%d/%m/%Y")
        html_con_tabla_mapas_dia = reemplazar_contenido_en_html(
            html_con_tabla_y_mapas,
            "id",
            "span-fecha-dinamica",
            f"Deloitte Argentina | Impuestos | {dia_actual}"
        )
        
        cuit_formateado = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10:]}"
        html_con_tabla_mapas_dia_cuit = reemplazar_contenido_en_html(
            html_con_tabla_mapas_dia,
            "id",
            "span-cliente-cuit",
            f"{cliente} CUIT {cuit_formateado}"
        )
        
        inicio_formateado = inicio.strftime("%H:%M")
        html_con_tabla_mapas_dia_cuit_fecha = reemplazar_contenido_en_html(
            html_con_tabla_mapas_dia_cuit,
            "id",
            "span-fecha-hora-procesamiento",
            f"Con fecha {dia_actual} a las {inicio_formateado} horas se realizó la revisión de los domicilios fiscales de las jurisdicciones por ustedes informadas.",
        )
        
        archivo_html_a_enviar = grabar_html(
            cliente, html_con_tabla_mapas_dia_cuit_fecha
        )

        with open(archivo_html_a_enviar, "r", encoding="utf-8") as f:
            html_content = f.read()
        body = MIMEText(html_content, "html")
        msg.attach(body)

    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP(servidor_smtp, puerto_smtp)
        server.starttls(context=context)
        server.sendmail(msg["From"], receptor + cc, msg.as_string())
    except SMTPNotSupportedError:
        logger.error(
            "El servidor no soporta SMTP AUTH. No se enviará el correo para mantener la seguridad."
        )
    except SMTPException as e:
        logger.error(f"Error al enviar correo: {e}")
    except Exception as e:
        logger.error(f"Error inesperado al enviar correo: {e}")
    finally:
        server.quit()


if __name__ == "__main__":
    enviar_correo(
        receptor=os.getenv("CORREO_RECEPTOR_TEST_MAIL"),
        cliente=os.getenv("CLIENTE_TEST_MAIL"),
    )
