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
    # Ejemplo de uso
    enviar_correo_outlook(
        receptor=["lmarinaro@deloitte.com"],
        cliente="FACEBOOK ARGENTINA S.R.L",
        ruta_archivo_adjunto="mail.zip",
        nombre_archivo_adjunto="mail.zip",
        df=pd.DataFrame(
            {  # Ejemplo de DataFrame
                "Jurisdicción": ["Región 1", "Región 2"],
                "Valor": [100, 200],
            }
        ),
        ruta_imagen_png="mapa.png",
        ruta_imagen_png_2="mapa2.png",
        cuerpo_html_plantilla="html/mail_plantilla.html",
        cc=["cc@example.com"],
    )
