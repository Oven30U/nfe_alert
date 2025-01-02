import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import win32com.client as win32
from logger import Logger

logger = Logger.get_logger()


def send_email_smtp(
    sender_email: str,
    receiver_emails: list[str],
    subject: str = None,
    html_file_path: Optional[str] = None,
    zip_file_paths: Optional[list[str]] = None,
    html_content: Optional[str] = None,
) -> tuple[list[str], list[str]]:
    # Enviar correos electrónicos utilizando SMTP con STARTTLS.
    servidor_smtp = os.getenv("SERVIDOR_SMTP")
    puerto_smtp = int(os.getenv("PUERTO_SMTP", "25"))

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

    # Enviar el correo vía SMTP con STARTTLS
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(servidor_smtp, puerto_smtp) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            # server.login(...) removed
            for email in receiver_emails:
                try:
                    server.sendmail(sender_email, email, msg.as_string())
                    successful_emails.append(email)
                    logger.info("Email enviado a %s exitosamente!", email)
                except Exception:
                    failed_emails.append(email)
                    logger.error("Error enviando email a %s", email)
    except Exception:
        particular_exception = "Error conectando al servidor SMTP"
        logger.error("%s", particular_exception)
        notify_error(
            sender_email, particular_exception, successful_emails, failed_emails
        )

    return successful_emails, failed_emails


def notify_error(
    sender_email: str,
    particular_exception: str,
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
    servidor_smtp = os.getenv("SERVIDOR_SMTP")
    puerto_smtp = int(os.getenv("PUERTO_SMTP", "25"))
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(servidor_smtp, puerto_smtp) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.sendmail(
                sender_email, os.getenv("CORREO_NOTIFICACION_ERROR"), msg.as_string()
            )
            logger.info(
                "Notificación de error enviada a %s",
                {os.getenv("CORREO_NOTIFICACION_ERROR")},
            )
    except ConnectionRefusedError:
        logger.error("Falló al enviar la notificación de error")

