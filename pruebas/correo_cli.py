import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import win32com.client as win32


def send_email_outlook(
    sender_email: str,
    receiver_emails: list[str],
    subject: str = None,
    html_file_path: Optional[str] = None,
    zip_file_paths: Optional[list[str]] = None,
    html_content: Optional[str] = None,
):
    # Crear una instancia de la aplicación Outlook
    outlook = win32.Dispatch("outlook.application")

    # Crear un nuevo correo
    email = outlook.CreateItem(0)

    # Configurar parámetros del correo
    email.Subject = subject

    if html_file_path and not html_content:
        # Leer contenido HTML desde archivo
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()

    if zip_file_paths:
        for zip_file_path in zip_file_paths:
            # Adjuntar el archivo ZIP
            attachment = email.Attachments.Add(zip_file_path)
            attachment.PropertyAccessor.SetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x3712001F",
                os.path.basename(zip_file_path).replace(".", "_"),
            )

    # Establecer el cuerpo en formato HTML si html_content no está vacío
    if html_content:
        email.HTMLBody = html_content

    # Unir múltiples correos receptores con punto y coma
    email.To = "; ".join(receiver_emails)
    email.SentOnBehalfOfName = sender_email

    # Enviar el correo
    email.Send()


def send_email_smtp(
    sender_email: str,
    receiver_emails: list[str],
    subject: str = None,
    html_file_path: Optional[str] = None,
    zip_file_paths: Optional[list[str]] = None,
    html_content: Optional[str] = None,
) -> tuple[list[str], list[str]]:
    # Configurar el servidor SMTP con SSL en puerto 465
    servidor_smtp = os.getenv("SERVIDOR_SMTP")
    puerto_smtp = int(os.getenv("PUERTO_SMTP", 465))

    # Crear el mensaje de correo
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = "; ".join(receiver_emails)
    msg["Subject"] = subject

    if html_file_path and not html_content:
        # Leer contenido HTML desde archivo
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()

    if zip_file_paths:
        for zip_file_path in zip_file_paths:
            # Adjuntar el archivo ZIP
            with open(zip_file_path, "rb") as file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(zip_file_path)}",
                )
                msg.attach(part)

    # Adjuntar el contenido HTML
    if html_content:
        msg.attach(MIMEText(html_content, "html"))

    successful_emails = []
    failed_emails = []

    # Enviar el correo vía SMTP con SSL
    try:
        with smtplib.SMTP_SSL(servidor_smtp, puerto_smtp) as server:
            server.ehlo()
            # Si el servidor soporta autenticación
            try:
                server.login(
                    os.getenv("CORREO_REMITENTE"), os.getenv("CONTRASEÑA_REMITENTE")
                )
            except smtplib.SMTPNotSupportedError:
                print("El servidor no soporta autenticación SMTP.")
            for email in receiver_emails:
                try:
                    server.sendmail(sender_email, email, msg.as_string())
                    successful_emails.append(email)
                    print(f"Email enviado a {email} exitosamente!")
                except Exception as e:
                    failed_emails.append(email)
                    print(f"Error enviando email a {email}: {e}")
    except Exception as e:
        print(f"Error conectando al servidor SMTP: {e}")
        notify_error(sender_email, e, successful_emails, failed_emails)

    return successful_emails, failed_emails


def notify_error(
    sender_email: str,
    particular_exception: Exception,
    successful_emails: list[str],
    failed_emails: list[str],
):
    # Crear el correo de notificación de error
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = os.getenv("CORREO_NOTIFICACION_ERROR")
    msg["Subject"] = "Notificación de Error: Fallo al Enviar Emails"

    # Crear el cuerpo del correo
    body = f"""
    Ocurrió un error al enviar emails:
    Excepción: {particular_exception}

    Emails Exitosos:
    {', '.join(successful_emails)}

    Emails Fallidos:
    {', '.join(failed_emails)}
    """
    msg.attach(MIMEText(body, "plain"))

    # Enviar el correo de notificación de error
    try:
        with smtplib.SMTP_SSL("appmail.atrame.deloitte.com", 465) as server:
            server.sendmail(sender_email, os.getenv("CORREO_NOTIFICACION_ERROR"), msg.as_string())
            print(f"Notificación de error enviada a {os.getenv('CORREO_NOTIFICACION_ERROR')}")
    except Exception as e:
        print(f"Falló al enviar la notificación de error: {e}")


if __name__ == "__main__":
    # Uso de ejemplo
    sender_email = "lmarinaro@deloitte.com"
    receiver_emails = ["lmarinaro@deloitte.com"]
    subject_outlook = "Hola desde Python en Outlook!"
    subject = "Hola desde Python!"
    html_file_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\System\archivos_plantilla\SIMPLOT ARGENTINA S.R.L_20240918.html"
    zip_file_paths = [
        r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\System\archivos_plantilla_dfe.zip"
    ]

    # Probar enviar correo usando Outlook
    try:
        send_email_outlook(
            sender_email,
            receiver_emails,
            subject_outlook,
            html_file_path,
            zip_file_paths,
        )
        print("Correo enviado exitosamente vía Outlook.")
    except Exception as e:
        print(f"Error enviando correo vía Outlook: {e}")

    # Probar enviar correo usando SMTP
    try:
        successful, failed = send_email_smtp(
            sender_email, receiver_emails, subject, html_file_path, zip_file_paths
        )
        print(f"Correos enviados exitosamente a: {successful}")
        if failed:
            print(f"Errores al enviar correos a: {failed}")
    except Exception as e:
        print(f"Error general al enviar correos vía SMTP: {e}")

    # Prueba de notify_error
    try:
        # Intentar enviar correo con un servidor SMTP incorrecto para forzar un fallo
        notify_error(sender_email, particular_exception = "Excepcion particular", successful_emails = "succeful@deloitte.com", failed_emails = "failed@deloitte.com")
    except Exception as e:
        print("Prueba de notify_error realizada.")
