"""
📧 Outlook Email Downloader for DFE

Este módulo proporciona funcionalidad para descargar correos electrónicos
desde una carpeta específica de Outlook y organizarlos en una estructura
de carpetas basada en el cliente y la fecha.

Los correos se guardan como archivos .msg con una estructura:
\\PATH\TO\NETWORK\CLIENT_NAME\Msg\YEAR-MONTH\DATE_SUBJECT.msg
"""

import os
import re
import win32com.client
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class MsgDownloader:
    """
    📥 Clase para descargar y organizar correos de Outlook en formato .msg
    
    Busca correos en una carpeta específica de Outlook y los guarda
    en una estructura organizada por cliente y fecha.
    """
    save_path: str = r"\\Arbas0008\taxteccs\RPA\BPS-Tax\DFE"
    account_name: str = "lmarinaro@deloitte.com"
    folder_name: str = "DFE"
    filter_word: Optional[List[str]] = (
        None  # Lista de palabras para filtrar el asunto; si es None o está vacía, no se filtra
    )

    def download_msg(self) -> None:
        """
        📤 Descarga correos de Outlook y los organiza en carpetas por cliente y fecha
        
        Extrae información del asunto para determinar el cliente y crea una estructura
        de carpetas: save_path/CLIENT_NAME/Msg/YEAR-MONTH/
        """
        # 📁 Crear carpeta base si no existe
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
            print(f"📁 Carpeta base creada: {self.save_path}")

        # 📧 Conectar con Outlook
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")

        # 🔐 Acceder a la cuenta y carpeta especificadas
        account = namespace.Folders(self.account_name)
        folder = account.Folders(self.folder_name)

        print(f"🔍 Buscando correos en la carpeta '{self.folder_name}'...")
        
        for item in folder.Items:
            try:
                if item.Class == 43:  # 43 es el código para emails
                    subject = item.Subject
                    subject_clean = re.sub(r'[\\/*?:"<>|]', "", subject) or "Sin_Asunto"

                    # 🔍 Aplicar filtro solo si filter_word tiene palabras
                    if self.filter_word and len(self.filter_word) > 0:
                        # Si ninguna de las palabras de filter_word está en el asunto, se omite el correo
                        if not any(
                            word.lower() in subject_clean.lower()
                            for word in self.filter_word
                        ):
                            continue

                    # 🏢 Extraer el nombre del cliente del asunto (formato: "CLIENT_NAME - NFE Alert_...")
                    client_match = re.match(r"^(.*?)\s*-\s*NFE Alert", subject)
                    client_name = (
                        client_match.group(1).strip() if client_match else "Sin_Cliente"
                    )
                    client_name_clean = re.sub(r'[\\/*?:"<>|]', "", client_name)

                    sent_date = item.SentOn
                    month_year = sent_date.strftime("%Y-%m")

                    # 📂 Nueva estructura de carpetas: save_path/CLIENT_NAME/Msg/YEAR-MONTH/
                    folder_client = os.path.join(self.save_path, client_name_clean)
                    folder_msg = os.path.join(folder_client, "Msg")
                    folder_date = os.path.join(folder_msg, month_year)

                    if not os.path.exists(folder_date):
                        os.makedirs(folder_date)
                        print(f"📁 Carpeta creada: {folder_date}")

                    filename = f"{sent_date.strftime('%d-%m-%Y')}_{subject_clean}.msg"
                    file_path = os.path.join(folder_date, filename)

                    # ✅ Verificar si el archivo ya existe antes de guardar
                    if os.path.exists(file_path):
                        print(f"ℹ️ El archivo ya existe, omitiendo: {file_path}")
                    else:
                        item.SaveAs(file_path, 3)  # 3 es el código para formato .msg
                        print(f"✅ Guardado: {file_path}")
            except Exception as e:
                print(f"❌ Error guardando el mensaje: {e}")


if __name__ == "__main__":
    # 🚀 Ejemplo de ejecución
    print("🔄 Iniciando descarga de correos DFE...")
    msg_downloader = MsgDownloader(
        account_name="lmarinaro@deloitte.com", folder_name="DFE"
    )
    msg_downloader.download_msg()
    print("🏁 Proceso de descarga completado!")
