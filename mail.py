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
from email.mime.application import MIMEApplication
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
import zipfile
import os

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
    Esta función envía un correo electrónico con un archivo ZIP adjunto y contenido HTML en el cuerpo del correo.
    El archivo ZIP contiene imágenes PNG y el PDF generado.

    Parámetros:
    receptor (str): El correo electrónico del receptor.
    cliente (str): El nombre del cliente.
    cuit (str): CUIT del cliente.
    inicio (datetime): Fecha y hora de inicio del procesamiento.
    ruta_archivo_adjunto (str): La ruta al archivo ZIP que se adjuntará.
    nombre_archivo_adjunto (str): El nombre del archivo ZIP adjunto.
    df (pandas.DataFrame): El DataFrame que se incluirá en el cuerpo del correo.
    ruta_imagen_png (str): Ruta a la primera imagen para incluir en el cuerpo.
    ruta_imagen_png_2 (str): Ruta a la segunda imagen para incluir en el cuerpo.
    cuerpo_html_plantilla (str): Ruta a la plantilla HTML.
    cc (list, str): Lista o cadena de correos electrónicos para enviar en copia.

    Retorna:
    None
    """

    servidor_smtp = os.getenv("SERVIDOR_SMTP")
    puerto_smtp = int(os.getenv("PUERTO_SMTP", "25"))

    if not servidor_smtp:
        logger.error("SERVIDOR_SMTP no está configurado en las variables de entorno")
        raise ValueError("SERVIDOR_SMTP es requerido")

    # Asegurarse de que 'receptor' es una lista y no un string
    if isinstance(receptor, str):
        display_recipients = [r.strip() for r in receptor.split(";") if r.strip()]
    else:
        display_recipients = [r.strip() for r in receptor if r.strip()]

    # Asegurarse de que 'cc' es una lista y no un string
    if cc is None:
        cc_recipients = []
    elif isinstance(cc, str):
        cc_recipients = [c.strip() for c in cc.split(";") if c.strip()]
    else:
        cc_recipients = [c.strip() for c in cc if c.strip()]

    rpa_emails = [
        email.strip()
        for email in os.getenv("CORREOS_RPA", "").split(",")
        if email.strip()
    ]

    # Crear el mensaje
    msg = MIMEMultipart()
    msg["From"] = os.getenv("CORREO_REMITENTE")
    msg["To"] = ",".join(display_recipients)
    msg["Cc"] = ",".join(cc_recipients)

    all_recipients = list(set(display_recipients + cc_recipients + rpa_emails))

    msg["Subject"] = (
        f"{cliente} - NFE Alert_Revisión de Domicilios Fiscales Electrónicos"
    )

    # Adjuntar el archivo ZIP si se proporciona
    if ruta_archivo_adjunto is not None and nombre_archivo_adjunto is not None:
        try:
            part = MIMEBase("application", "zip")
            with open(ruta_archivo_adjunto, "rb") as file:
                content = file.read()
                if not content:
                    raise ValueError("Archivo ZIP vacío")
                part.set_payload(content)

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition", "attachment", filename=nombre_archivo_adjunto
            )
            part.add_header("Content-Type", "application/zip")
            msg.attach(part)
        except (IOError, ValueError) as e:
            logger.error(f"Error adjuntando archivo ZIP: {e}")
            raise

    # Creamos el cuerpo del mensaje
    if df is not None:
        mapa_provincias_html = convertir_imagen_en_html(ruta_imagen_png)
        mapa_argentina_html = convertir_imagen_en_html(ruta_imagen_png_2)

        df["Jurisdicción"] = df["Jurisdicción"].replace(mapa_jurisdiccion_clases)

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
            f"Deloitte Argentina | Impuestos | {dia_actual}",
        )

        cuit_formateado = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10:]}"
        html_con_tabla_mapas_dia_cuit = reemplazar_contenido_en_html(
            html_con_tabla_mapas_dia,
            "id",
            "span-cuit",
            f"CUIT {cuit_formateado}",
        )

        html_con_tabla_mapas_dia_cuit_cliente = reemplazar_contenido_en_html(
            html_con_tabla_mapas_dia_cuit,
            "id",
            "span-cliente",
            f"{cliente.title()}",
        )

        inicio_formateado = inicio.strftime("%H:%M")
        html_con_tabla_mapas_dia_cuit_fecha = reemplazar_contenido_en_html(
            html_con_tabla_mapas_dia_cuit_cliente,
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

    server = None
    try:
        # Crear contexto SSL más permisivo para evitar errores de certificado
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Obtener credenciales SMTP
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")

        logger.debug(f"Conectando al servidor SMTP: {servidor_smtp}:{puerto_smtp}")
        server = smtplib.SMTP(servidor_smtp, puerto_smtp)

        # Iniciar TLS con contexto permisivo
        logger.debug("Iniciando conexión TLS...")
        server.starttls(context=context)

        # Verificar si se requiere autenticación
        if smtp_username and smtp_password:
            logger.debug("Autenticando con credenciales SMTP...")
            server.login(smtp_username, smtp_password)

        # Enviar el correo
        logger.debug(f"Enviando correo a {len(all_recipients)} destinatarios...")
        server.sendmail(msg["From"], all_recipients, msg.as_string())
        logger.info(f"Correo enviado exitosamente para cliente: {cliente}")

    except SMTPNotSupportedError as e:
        logger.error(
            f"El servidor no soporta SMTP AUTH. No se enviará el correo para mantener la seguridad. Error: {e}"
        )
        raise
    except ssl.SSLError as e:
        logger.error(f"Error SSL al conectar con el servidor SMTP: {e}")
        logger.warning("Intentando envío sin SSL...")
        # Intentar sin SSL como último recurso
        try:
            if server:
                server.quit()
            server = smtplib.SMTP(servidor_smtp, puerto_smtp)
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.sendmail(msg["From"], all_recipients, msg.as_string())
            logger.info(f"Correo enviado exitosamente sin SSL para cliente: {cliente}")
        except Exception as fallback_error:
            logger.error(f"Error en fallback sin SSL: {fallback_error}")
            raise
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Error de autenticación SMTP: {e}")
        logger.error("Verificar credenciales SMTP_USERNAME y SMTP_PASSWORD")
        raise
    except smtplib.SMTPConnectError as e:
        logger.error(
            f"Error de conexión al servidor SMTP {servidor_smtp}:{puerto_smtp}: {e}"
        )
        raise
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"Destinatarios rechazados por el servidor: {e}")
        raise
    except SMTPException as e:
        logger.error(f"Error SMTP al enviar correo: cliente: {cliente}, error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al enviar correo: {e}")
        raise
    finally:
        # Cerrar la conexión del servidor de forma segura
        if server is not None:
            try:
                server.quit()
                logger.debug("Conexión SMTP cerrada correctamente")
            except Exception as e:
                logger.warning(f"Error al cerrar conexión SMTP: {e}")


if __name__ == "__main__":
    enviar_correo(
        receptor=os.getenv("CORREO_RECEPTOR_TEST_MAIL"),
        cliente=os.getenv("CLIENTE_TEST_MAIL"),
        cuit=os.getenv("CUIT_TEST_MAIL"),
        inicio=os.getenv("INICIO_TEST_MAIL"),
    )
