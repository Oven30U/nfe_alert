"""
Este módulo proporciona una función para enviar correos electrónicos utilizando SMTP con STARTTLS.
Es necesario que la cuenta tenga acceso al servidor SMTP configurado.
Podría utilizarse cómo BackUp en caso de no poder utilizar SMTP de mail.py, luego de solicitar 
habilitación de los puertos 465 o 587 y el protocolo SMTP sobre SSL o STARTTLS.

Funciones:
- send_email_smtp: Envía un correo electrónico utilizando SMTP con la posibilidad de adjuntar archivos y personalizar el contenido HTML.

Dependencias:
- smtplib
- email.mime.multipart
- email.mime.text
- email.mime.base
- email.encoders
- os
- dotenv (load_dotenv)

Variables de entorno requeridas:
- SENDER_EMAIL: Correo electrónico del remitente.
- CORREO_RECEPTOR_TEST_MAIL: Correo electrónico del receptor para pruebas.

Ejemplo de uso:
    sender_email = os.getenv("SENDER_EMAIL")
    receiver_emails = [os.getenv("CORREO_RECEPTOR_TEST_MAIL")]
    subject = "Test send_email_smtp"
    html_content = "<h1>Test Email</h1>"

    successful_emails, failed_emails = send_email_smtp(
        sender_email,
        receiver_emails,
        subject,
        html_content=html_content
    )
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
import os


def send_email_smtp(
    sender_email: str,
    receiver_emails: List[str],
    subject: str = None,
    html_file_path: Optional[str] = None,
    zip_file_paths: Optional[List[str]] = None,
    html_content: Optional[str] = None,
) -> tuple[List[str], List[str]]:
    """
    Envía un correo electrónico utilizando SMTP con STARTTLS.

    Parámetros:
    sender_email (str): El correo electrónico del remitente.
    receiver_emails (List[str]): Lista de correos electrónicos de los receptores.
    subject (str, opcional): El asunto del correo electrónico.
    html_file_path (Optional[str], opcional): La ruta al archivo HTML que se incluirá en el cuerpo del correo.
    zip_file_paths (Optional[List[str]], opcional): Lista de rutas a archivos ZIP que se adjuntarán.
    html_content (Optional[str], opcional): El contenido HTML que se incluirá en el cuerpo del correo.

    Retorna:
    tuple[List[str], List[str]]: Una tupla con dos listas: correos electrónicos enviados exitosamente y correos electrónicos que fallaron.
    """
    # SMTP server configuration
    servidor_smtp = "appmail.atrame.deloitte.com"
    puerto_smtp = 587  # Puerto para SMTP con STARTTLS

    # Create the email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = "; ".join(receiver_emails)
    msg["Subject"] = subject

    if html_file_path and not html_content:
        # Read HTML content from file
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()

    if zip_file_paths:
        for zip_file_path in zip_file_paths:
            # Attach the ZIP file
            with open(zip_file_path, "rb") as file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(zip_file_path)}",
                )
                msg.attach(part)

    # Attach the HTML content
    if html_content:
        msg.attach(MIMEText(html_content, "html"))

    successful_emails = []
    failed_emails = []

    # Send the email via SMTP with STARTTLS
    try:
        with smtplib.SMTP(servidor_smtp, puerto_smtp) as server:
            server.starttls()  # Secure the connection
            # server.login('your_username', 'your_password')  # Si se requiere autenticación
            for email in receiver_emails:
                try:
                    server.sendmail(sender_email, email, msg.as_string())
                    successful_emails.append(email)
                    print(f"Email sent successfully to {email}")
                except Exception as e:
                    failed_emails.append(email)
                    print(f"Error sending email to {email}: {e}")
    except Exception as e:
        print(f"Error connecting to SMTP server: {e}")
        # notify_error(sender_email, e, successful_emails, failed_emails)

    return successful_emails, failed_emails


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    sender_email = os.getenv("SENDER_EMAIL")
    receiver_emails = [os.getenv("CORREO_RECEPTOR_TEST_MAIL")]
    subject = "Test send_email_smtp"
    html_content = "<h1>Test Email</h1>"

    successful_emails, failed_emails = send_email_smtp(
        sender_email, receiver_emails, subject, html_content=html_content
    )

    print(f"Successful emails: {successful_emails}")
    print(f"Failed emails: {failed_emails}")
