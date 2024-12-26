def enviar_correo(remitente, contraseña, destinatario, asunto, cuerpo):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = destinatario
    mensaje['Subject'] = asunto
    mensaje.attach(MIMEText(cuerpo, 'plain'))

    servidor_smtp = "appmail.atrame.deloitte.com"
    puerto_smtp = 25

    with smtplib.SMTP(servidor_smtp, puerto_smtp) as servidor:
        servidor.starttls()
        servidor.sendmail(remitente, destinatario, mensaje.as_string())

if __name__ == '__main__':
    enviar_correo("lmarinaro@deloitte.com", "LCAm162303$$", "lmarinaro@deloitte.com", "Asunto", "Cuerpo")