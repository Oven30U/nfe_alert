import win32com.client as win32
import os
import re


def send_email_outlook(
    sender_email, receiver_emails, subject, html_file_path, image_paths
):
    # Create an instance of the Outlook application
    outlook = win32.Dispatch("outlook.application")

    # Create a new email
    email = outlook.CreateItem(0)

    # Set email parameters
    email.Subject = subject

    # Read HTML content from file
    with open(html_file_path, "r", encoding="utf-8") as file:
        html_content = file.read()

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

    # Set the body to HTML format
    email.HTMLBody = html_content

    # Join multiple receiver emails with a semicolon
    email.To = "; ".join(receiver_emails)
    email.SentOnBehalfOfName = sender_email

    # Send the email
    email.Send()


# Example usage
sender_email = "lmarinaro@deloitte.com"
receiver_emails = ["lmarinaro@deloitte.com"]
subject = "Hello from Python!"
# html_file_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\pruebas\enviando_img.html"
html_file_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\EDGE ARGENTINA S.R.L\Output\EDGE ARGENTINA S.R.L_20240913.html"
image_paths = [
    r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\EDGE ARGENTINA S.R.L\Output\mapa_jurisdicciones_EDGE ARGENTINA S.R.L.png"
]

send_email_outlook(sender_email, receiver_emails, subject, html_file_path, image_paths)
