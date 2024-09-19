import os
import re
import smtplib
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from typing import Optional, List

import win32com.client as win32


def send_email_outlook(
    sender_email: str,
    receiver_emails: List[str],
    subject: str = None,
    html_file_path: Optional[str] = None,
    zip_file_paths: Optional[List[str]] = None,
    html_content: Optional[str] = None,
):
    # Create an instance of the Outlook application
    outlook = win32.Dispatch("outlook.application")

    # Create a new email
    email = outlook.CreateItem(0)

    # Set email parameters
    email.Subject = subject

    if html_file_path and not html_content:
        # Read HTML content from file
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()

    if zip_file_paths:
        for zip_file_path in zip_file_paths:
            # Attach the ZIP file
            attachment = email.Attachments.Add(zip_file_path)
            attachment.PropertyAccessor.SetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x3712001F", os.path.basename(zip_file_path).replace(".", "_")
            )

    # Set the body to HTML format if html_content is not empty
    if html_content:
        email.HTMLBody = html_content

    # Join multiple receiver emails with a semicolon
    email.To = "; ".join(receiver_emails)
    email.SentOnBehalfOfName = sender_email

    # Send the email
    email.Send()


def send_email_smtp(
    sender_email: str,
    receiver_emails: List[str],
    subject: str = None,
    html_file_path: Optional[str] = None,
    zip_file_paths: Optional[List[str]] = None,
    html_content: Optional[str] = None,
):
    # SMTP server configuration
    servidor_smtp = "appmail.atrame.deloitte.com"
    puerto_smtp = 25

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

    # Send the email via SMTP
    try:
        with smtplib.SMTP(servidor_smtp, puerto_smtp) as server:
            server.sendmail(sender_email, receiver_emails, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")


if __name__ == "__main__":
    # Example usage
    sender_email = "lmarinaro@deloitte.com"
    receiver_emails = ["lmarinaro@deloitte.com", "marinaro.leonel@tecnica7.edu.ar"]
    subject_outlook = "Hello from Python in Outlook!"
    subject = "Hello from Python!"
    html_file_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\System\archivos_plantilla\SIMPLOT ARGENTINA S.R.L_20240918.html"
    zip_file_paths = [
        r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\System\archivos_plantilla_dfe.zip"
    ]

    send_email_outlook(
        sender_email, receiver_emails, subject_outlook, html_file_path, zip_file_paths
    )
    send_email_smtp(
        sender_email, receiver_emails, subject, html_file_path, zip_file_paths
    )