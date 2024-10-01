import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTPNotSupportedError

from config import jurisdiccion_clases, mapa_jurisdiccion_clases
from generar_html import (
    convertir_imagen_en_html,
    grabar_html,
    insertar_mapas_en_html,
    insertar_tabla_en_html,
    reemplazar_contenido_en_html,
)


def enviar_correo(
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
    Esta función envía un correo electrónico con un archivo adjunto y/o un DataFrame en el cuerpo del correo.

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
    enviar_correo("lmarinaro@deloitte.com", "Facebook S.R.L.", "mail.zip", df=df_output_final, ruta_mapa_html="map.html", cc=["cc@example.com"])
    """

    # Configurar el servidor SMTP (asegúrate de tener las credenciales correctas)
    servidor_smtp = "appmail.atrame.deloitte.com"
    puerto_smtp = 25

    # Asegurarse de que 'receptor' es una lista y no un string
    if not isinstance(receptor, list):
        receptor = [receptor]

    # Asegurarse de que 'cc' es una lista y no un string
    if cc is None:
        cc = []
    elif not isinstance(cc, list):
        cc = [cc]

    # Crear el mensaje
    msg = MIMEMultipart()
    msg["From"] = "robot-Tax-AR@deloitte.com"
    msg["To"] = ",".join(receptor)
    msg["Cc"] = ",".join(cc)
    correos_rpa = ["lmarinaro@deloitte.com", "rpa-tax-ar@deloitte.com"]
    # Dividir la cadena en varias cadenas utilizando el method split()
    receptor = receptor[0].split(";")
    receptor.extend(correos_rpa)
    msg["Subject"] = (
        f"Revisión de Domicilios Fiscales Electrónicos del cliente {cliente}"
    )

    # Adjuntar el archivo si se proporciona
    if ruta_archivo_adjunto is not None and nombre_archivo_adjunto is not None:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(open(ruta_archivo_adjunto, "rb").read())
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
        )  # mapa_jurisdiccion_clases jurisdiccion_clases
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
        # msg = MIMEMultipart("alternative")
        body = MIMEText(html_content, "html")
        msg.attach(body)

    # Intenta crear conexión al servidor SMTP
    try:
        server = smtplib.SMTP(servidor_smtp, puerto_smtp)
        server.starttls()
    except ConnectionRefusedError:
        # Si la conexión es rechazada, intenta sin especificar el puerto
        server = smtplib.SMTP(servidor_smtp)

    # Intenta enviar el correo electrónico
    try:
        server.sendmail(msg["From"], receptor + cc, msg.as_string())
    except SMTPNotSupportedError:
        # Si no se admite la autenticación, continuar sin autenticación
        server = smtplib.SMTP(servidor_smtp)
        server.sendmail(msg["From"], receptor + cc, msg.as_string())

    # Cerrar la conexión
    server.quit()
