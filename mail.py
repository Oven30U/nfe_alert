from datetime import datetime

# from encodings import utf-8
import smtplib

# from uu import encode
# import pandas as pd
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from smtplib import SMTPNotSupportedError
from email.mime.text import MIMEText

# from email.mime.image import MIMEImage


# from matplotlib import style
from generar_html import (
    convertir_imagen_en_html,
    insertar_tabla_en_html,
    insertar_mapas_en_html,
    reemplazar_contenido_en_html,
    grabar_html,
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
    # cuerpo_html_salida=None,
):
    """
    Esta función envía un correo electrónico con un archivo adjunto y/o un DataFrame en el cuerpo del correo.

    Parámetros:
    receptor (str): El correo electrónico del receptor.
    cliente (str): El nombre del cliente.
    ruta_archivo_adjunto (str): La ruta al archivo que se adjuntará.
    nombre_archivo_adjunto (str): El nombre del archivo adjunto.
    df (pandas.DataFrame): El DataFrame que se incluirá en el cuerpo del correo.

    Retorna:
    None

    Ejemplo:
    enviar_correo("lmarinaro@deloitte.com", "Facebook S.R.L.", "mail.zip", df=df_output_final, ruta_mapa_html="map.html")
    """

    # Configurar el servidor SMTP (asegúrate de tener las credenciales correctas)
    servidor_smtp = "appmail.atrame.deloitte.com"
    puerto_smtp = 25

    # Asegurarse de que 'receptor' es una lista y no un string
    if not isinstance(receptor, list):
        receptor = [receptor]

    # Crear el mensaje
    msg = MIMEMultipart()
    # msg["From"] = "TaxTecARG@deloitte.com"
    msg["From"] = "robot-Tax-AR@deloitte.com"
    # msg["From"] = "Robot DFE <Robot-Tax@deloitte.com>"
    msg["To"] = ",".join(receptor)
    # msg["To"] = receptor
    # msg["To"] = ", ".join(receptor)
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

    # # Adjuntar la imagen PNG nro 1 si se proporciona
    # if ruta_imagen_png is not None:
    #     with open(ruta_imagen_png, "rb") as file:
    #         img = MIMEImage(file.read())
    #     img.add_header("Content-ID", "<{}>".format(ruta_imagen_png.split("/")[-1]))
    #     img.add_header(
    #         "Content-Disposition", "inline", filename=ruta_imagen_png.split("/")[-1]
    #     )
    #     msg.attach(img)

    # # Adjuntar la imagen PNG nro 2 si se proporciona
    # if ruta_imagen_png_2 is not None:
    #     with open(ruta_imagen_png_2, "rb") as file:
    #         img = MIMEImage(file.read())
    #     img.add_header("Content-ID", "<{}>".format(ruta_imagen_png_2.split("/")[-1]))
    #     img.add_header(
    #         "Content-Disposition", "inline", filename=ruta_imagen_png_2.split("/")[-1]
    #     )
    #     msg.attach(img)

    # # Agregar el DataFrame, texto HTML y contenido del archivo HTML al cuerpo del correo electrónico
    # if df is not None:
    #     # df = df.reset_index(drop=True)  # Reset the index to ensure it's unique
    #     # df.columns = pd.Series(df.columns).apply(lambda x: x if df.columns.tolist().count(x)==1 else x + "_dup")

    #     # Replace color_row with color_row_func in the rest of the code
    #     # colors = df.apply(color_row_func, axis=1)

    #     # In enviar_correo function
    #     color = df.apply(color_row_func, axis=1)

    #     table_html = """
    #     <table border="0" cellspacing="0" cellpadding="0" style="border-collapse:collapse">
    #         <tbody>
    #             <tr style="height:17.0pt">
    #     <td width="19" style="width:14.05pt;border-top:solid windowtext 3.0pt;border-left:none;border-bottom:solid windowtext 1.0pt;border-right:none;padding:0cm 0cm 0cm 0cm;height:17.0pt">
    #     <p><b><span lang="ES-MX" style="font-family: ;Calibri Light ;,sans-serif"><u></u>&nbsp;<u></u></span></b></p>
    #     </td>
    #     <td width="150" style="width:112.45pt;border-top:solid windowtext 3.0pt;border-left:none;border-bottom:solid windowtext 1.0pt;border-right:none;padding:0cm 0cm 0cm 0cm;height:17.0pt">
    #     <p><b><span lang="ES-MX">Jurisdicción <u></u><u></u></span></b></p>
    #     </td>
    #     <td width="150" style="width:112.5pt;border-top:solid windowtext 3.0pt;border-left:none;border-bottom:solid windowtext 1.0pt;border-right:none;padding:0cm 0cm 0cm 0cm;height:17.0pt">
    #     <p><b><span lang="ES-MX">Screenshot<u></u><u></u></span></b></p>
    #     </td>
    #     <td width="150" style="width:112.5pt;border-top:solid windowtext 3.0pt;border-left:none;border-bottom:solid windowtext 1.0pt;border-right:none;padding:0cm 0cm 0cm 0cm;height:17.0pt">
    #     <p><b><span lang="ES-MX">Observaciones<u></u><u></u></span></b></p>
    #     </td>
    #     </tr>
    #     """
    #     for (index, row), color_row in zip(df.iterrows(), color.items()):
    #         row_html = f'<tr style="background-color: {color_row}">'
    #         for column in df.columns:
    #             row_html += f"<td>{row[column]}</td>"
    #         row_html += "</tr>"
    #         table_html += row_html

    #     # html_df = styled_df.to_html()
    #     # Leer el archivo HTML si se proporciona
    #     # html_text = ""
    #     ruta_archivo_html_base = "base_mail.html"
    #     if ruta_archivo_html_base is not None:
    #         # with open(ruta_archivo_html_base, "r", encoding="utf-8") as file:
    #         # html_text = file.read()
    #         cuerpo_mail_html = insertar_mapas_en_html(
    #             ruta_imagen_png, ruta_imagen_png_2, table_html
    #         )
    #     # cuerpo_mail_html = html_text  # + html_df

    #     body = MIMEText(cuerpo_mail_html, "html")
    #     msg.attach(body)

    # Creamos el cuerpo del mensaje
    if df is not None:
        mapa_provincias_html = convertir_imagen_en_html(ruta_imagen_png)
        mapa_argentina_html = convertir_imagen_en_html(ruta_imagen_png_2)
        dict_reemplazo = {
            "Agip": "AGIP",
            "Arba": "ARBA",
            "Cordoba": "Córdoba",
            "EntreRios": "Entre Ríos",
            "Neuquen": "Neuquén",
            "RioNegro": "Río Negro",
            "Tucuman": "Tucumán",
        }
        df["Jurisdicción"] = df["Jurisdicción"].replace(dict_reemplazo)
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

        # # Adjuntar la imagen PNG si se proporciona
        # if ruta_imagen_png is not None:
        #     with open(ruta_imagen_png, "rb") as file:
        #         img = MIMEImage(file.read())
        #     img.add_header(
        #         "Content-Disposition",
        #         "attachment",
        #         filename=ruta_imagen_png.split("/")[-1],
        #     )
        #     msg.attach(img)

        # # Adjuntar la imagen PNG si se proporciona
        # if ruta_imagen_png_2 is not None:
        #     with open(ruta_imagen_png_2, "rb") as file:
        #         img = MIMEImage(file.read())
        #     img.add_header(
        #         "Content-Disposition",
        #         "attachment",
        #         filename=ruta_imagen_png_2.split("/")[-1],
        #     )
        #     msg.attach(img)

    # Intenta crear conexión al servidor SMTP
    try:
        server = smtplib.SMTP(servidor_smtp, puerto_smtp)
        server.starttls()
    except ConnectionRefusedError:
        # Si la conexión es rechazada, intenta sin especificar el puerto
        server = smtplib.SMTP(servidor_smtp)

    # Intenta enviar el correo electrónico
    try:
        server.sendmail(msg["From"], receptor, msg.as_string())
    except SMTPNotSupportedError:
        # Si no se admite la autenticación, continuar sin autenticación
        server = smtplib.SMTP(servidor_smtp)
        # server.sendmail(msg["From"], receptor.split(";"), msg.as_string())
        server.sendmail(receptor, receptor, msg.as_string())

    # Cerrar la conexión
    server.quit()
