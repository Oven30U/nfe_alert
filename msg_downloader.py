import os
import re
import win32com.client
from datetime import datetime

class MsgDownloader():
    def __init__():
    
    def download_msg():
        # Carpeta base donde se guardarán los mensajes (ajústala según tus necesidades)
        save_path = r"C:\Users\lmarinaro\Downloads\mails_nfe"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # Conectar con Outlook y obtener namespace
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")

        # Seleccionar la carpeta: ajustar los nombres según tu configuración
        account = namespace.Folders("lmarinaro@deloitte.com")
        folder = account.Folders("DFE")

        # Recorrer todos los elementos de la carpeta
        for item in folder.Items:
            try:
                # Asegurarse de trabajar sólo con mensajes de correo (clase 43 = MailItem)
                if item.Class == 43:
                    # Limpiar el asunto para usarlo en la ruta (eliminar caracteres no válidos)
                    subject_clean = re.sub(r'[\\/*?:"<>|]', "", item.Subject) or "Sin_Asunto"

                    # Obtener la fecha de envío y formatearla a "YYYY-MM"
                    sent_date = item.SentOn
                    month_year = sent_date.strftime("%Y-%m")

                    # Crear las rutas para guardar el mensaje
                    folder_subject = os.path.join(save_path, subject_clean)
                    folder_date = os.path.join(folder_subject, month_year)

                    if not os.path.exists(folder_date):
                        os.makedirs(folder_date)

                    # Construir el nombre del archivo usando el asunto y la fecha con marca temporal para evitar duplicados
                    filename = f"{subject_clean}_{sent_date.strftime('%Y%m%d%H%M%S')}.msg"
                    file_path = os.path.join(folder_date, filename)

                    # Guardar el mensaje en formato .msg (parametro 3)
                    item.SaveAs(file_path, 3)
                    print("Guardado:", file_path)
            except Exception as e:
                print("Error guardando el mensaje:", e)

if __name__ == '__main__':
    msg_downloader = MsgDownloader()
    msg_downloader.download_msg()