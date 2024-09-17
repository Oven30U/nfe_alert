import win32com.client as win32
import os
import re
from typing import Optional

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def send_email_outlook(
    sender_email: str = "lmarinaro@deloitte.com",
    receiver_emails: list[str] = ["lmarinaro@deloitte.com"],
    subject: str = None,
    html_file_path: Optional[str] = None,
    image_paths: Optional[list[str]] = None,
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

    if image_paths:
        # Attach images and replace their paths in the HTML content with CID references
        for image_path in image_paths:
            image_name = os.path.basename(image_path)
            cid = image_name.replace(".", "_")
            attachment = email.Attachments.Add(image_path)
            attachment.PropertyAccessor.SetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x3712001F", cid
            )
            html_content = re.sub(
                r'src="{}"'.format(re.escape(image_path)),
                'src="cid:{}"'.format(cid),
                html_content,
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
    sender_email: str = "lmarinaro@deloitte.com",
    receiver_emails: list[str] = ["lmarinaro@deloitte.com"],
    subject: str = None,
    html_file_path: Optional[str] = None,
    image_paths: Optional[list[str]] = None,
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

    if image_paths:
        # Attach images and replace their paths in the HTML content with CID references
        for image_path in image_paths:
            with open(image_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", f"<{os.path.basename(image_path)}>")
                msg.attach(img)
                html_content = re.sub(
                    r'src="{}"'.format(re.escape(image_path)),
                    'src="cid:{}"'.format(os.path.basename(image_path)),
                    html_content,
                )

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
    receiver_emails = ["lmarinaro@deloitte.com"]
    subject = "Hello from Python!"
    html_file_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\EDGE ARGENTINA S.R.L\Output\EDGE ARGENTINA S.R.L_20240913.html"
    image_paths = [
        r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\EDGE ARGENTINA S.R.L\Output\mapa_jurisdicciones_EDGE ARGENTINA S.R.L.png"
    ]

    send_email_outlook(sender_email, receiver_emails, subject, html_file_path, image_paths)