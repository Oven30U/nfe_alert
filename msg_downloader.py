"""
📧 Outlook Email Downloader for DFE

Este módulo proporciona funcionalidad para descargar correos electrónicos
desde una carpeta específica de Outlook y organizarlos en una estructura
de carpetas basada en el cliente y la fecha.

Los correos se guardan como archivos .msg con una estructura:
CLIENT_NAME/Msg/YEAR-MONTH\DATE_SUBJECT.msg"
"""

# Importaciones de bibliotecas estándar
import os
import re
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union

# Importaciones de bibliotecas de terceros
import win32com.client

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class MsgDownloader:
    """
    📥 Clase para descargar y organizar correos de Outlook en formato .msg

    Busca correos en una carpeta específica de Outlook y los guarda
    en una estructura organizada por cliente y fecha. Permite filtrar
    por palabras clave en el asunto o en el nombre del cliente.
    """

    save_path: str = r"C:\Users\lmarinaro\Downloads\msg"
    account_name: str = "lmarinaro@deloitte.com"
    folder_name: str = "DFE"
    filter_subject: Optional[List[str]] = None  # Filtros para el asunto completo
    filter_client: Optional[List[str]] = None  # Filtros para el nombre del cliente

    def download_msg(self) -> Dict[str, Any]:
        """
        📤 Descarga correos de Outlook y los organiza en carpetas por cliente y fecha

        Extrae información del asunto para determinar el cliente y crea una estructura
        de carpetas: save_path/CLIENT_NAME/Msg/YEAR-MONTH/

        Returns:
            Dict[str, Any]: Estadísticas de la operación (total, descargados, omitidos, errores)
        """
        # Estadísticas para retornar
        stats = {
            "total": 0,
            "descargados": 0,
            "omitidos_existentes": 0,
            "omitidos_filtro": 0,
            "errores": 0,
        }

        try:
            # 📁 Crear carpeta base si no existe
            self._ensure_directory_exists(self.save_path)

            # 📧 Conectar con Outlook
            outlook = self._connect_to_outlook()

            # Validar conexión exitosa
            if outlook is None:
                logger.error("No se pudo establecer conexión con Outlook")
                return stats

            folder_items = self._get_folder_items(outlook)

            if folder_items is None:
                logger.error(f"No se pudo acceder a la carpeta '{self.folder_name}'")
                return stats

            logger.info(f"🔍 Buscando correos en la carpeta '{self.folder_name}'...")

            # Procesar los elementos de la carpeta
            for item in folder_items:
                stats["total"] += 1
                try:
                    if item.Class != 43:  # 43 es el código para emails
                        continue

                    subject = item.Subject
                    subject_clean = re.sub(r'[\\/*?:"<>|]', "", subject) or "Sin_Asunto"

                    # 🏢 Extraer el nombre del cliente del asunto
                    client_name, client_name_clean = self._extract_client_name(subject)

                    # 🔍 Aplicar filtros
                    if not self._passes_filters(subject_clean, client_name_clean):
                        stats["omitidos_filtro"] += 1
                        continue

                    # Determinar la ruta del archivo
                    sent_date = item.SentOn
                    file_path = self._generate_file_path(
                        client_name_clean, sent_date, subject_clean
                    )

                    # ✅ Verificar si el archivo ya existe antes de guardar
                    if os.path.exists(file_path):
                        logger.info(f"ℹ️ El archivo ya existe, omitiendo: {file_path}")
                        stats["omitidos_existentes"] += 1
                    else:
                        item.SaveAs(file_path, 3)  # 3 es el código para formato .msg
                        logger.info(f"✅ Guardado: {file_path}")
                        stats["descargados"] += 1

                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje: {str(e)}")
                    stats["errores"] += 1

            return stats

        except Exception as e:
            logger.error(f"❌ Error global en la descarga de mensajes: {str(e)}")
            stats["errores"] += 1
            return stats

    def _ensure_directory_exists(self, directory_path: str) -> None:
        """
        Asegura que el directorio especificado exista.

        Args:
            directory_path: Ruta del directorio a verificar/crear
        """
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            logger.info(f"📁 Carpeta creada: {directory_path}")

    def _connect_to_outlook(self) -> Union[Any, None]:
        """
        Establece conexión con la aplicación de Outlook.

        Returns:
            Union[Any, None]: Objeto de aplicación Outlook o None si falla
        """
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            return outlook
        except Exception as e:
            logger.error(f"❌ Error al conectar con Outlook: {str(e)}")
            return None

    def _get_folder_items(self, outlook: Any) -> Union[Any, None]:
        """
        Obtiene los elementos de la carpeta especificada en Outlook.

        Args:
            outlook: Objeto de aplicación Outlook

        Returns:
            Union[Any, None]: Colección de elementos o None si falla
        """
        try:
            namespace = outlook.GetNamespace("MAPI")
            account = namespace.Folders(self.account_name)
            folder = account.Folders(self.folder_name)
            return folder.Items
        except Exception as e:
            logger.error(
                f"❌ Error al acceder a la carpeta '{self.folder_name}': {str(e)}"
            )
            return None

    def _extract_client_name(self, subject: str) -> tuple[str, str]:
        """
        Extrae el nombre del cliente del asunto del correo.

        Args:
            subject: Asunto del correo

        Returns:
            tuple[str, str]: Nombre del cliente original y nombre limpio
        """
        # Formato: "CLIENT_NAME [- JURISDICCION] - NFE Alert_..."
        client_match = re.match(r"^(.*?)\s*-\s*NFE Alert", subject)
        client_name = client_match.group(1).strip() if client_match else "Sin_Cliente"
        client_name_clean = re.sub(r'[\\/*?:"<>|]', "", client_name)

        return client_name, client_name_clean

    def _passes_filters(self, subject_clean: str, client_name_clean: str) -> bool:
        """
        Verifica si el correo pasa los filtros configurados.

        Args:
            subject_clean: Asunto del correo limpio
            client_name_clean: Nombre del cliente limpio

        Returns:
            bool: True si pasa los filtros o no hay filtros, False en caso contrario
        """
        # Si no hay filtros configurados, se aceptan todos los correos
        if (not self.filter_subject or len(self.filter_subject) == 0) and (
            not self.filter_client or len(self.filter_client) == 0
        ):
            return True

        # Verificar filtro de asunto
        if self.filter_subject and len(self.filter_subject) > 0:
            if not any(
                word.lower() in subject_clean.lower() for word in self.filter_subject
            ):
                return False

        # Verificar filtro de cliente
        if self.filter_client and len(self.filter_client) > 0:
            if not any(
                word.lower() in client_name_clean.lower() for word in self.filter_client
            ):
                return False

        return True

    def _generate_file_path(
        self, client_name_clean: str, sent_date: datetime, subject_clean: str
    ) -> str:
        """
        Genera la ruta del archivo según la estructura de carpetas definida.

        Args:
            client_name_clean: Nombre del cliente limpio
            sent_date: Fecha de envío del correo
            subject_clean: Asunto del correo limpio

        Returns:
            str: Ruta completa del archivo
        """
        month_year = sent_date.strftime("%Y-%m")

        # Estructura de carpetas: save_path/CLIENT_NAME/Msg/YEAR-MONTH/
        folder_client = os.path.join(self.save_path, client_name_clean)
        folder_msg = os.path.join(folder_client, "Msg")
        folder_date = os.path.join(folder_msg, month_year)

        # Crear estructura de carpetas si no existe
        self._ensure_directory_exists(folder_date)

        filename = f"{sent_date.strftime('%d-%m-%Y')}_{subject_clean}.msg"
        return os.path.join(folder_date, filename)


def download_msgs(
    account_name: str = "lmarinaro@deloitte.com",
    folder_name: str = "DFE",
    save_path: str = r"C:\Users\lmarinaro\Downloads\msg",
    filter_client: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Función auxiliar para descargar correos con configuración simplificada.

    Args:
        account_name: Nombre de la cuenta de Outlook
        folder_name: Nombre de la carpeta de Outlook
        save_path: Ruta donde guardar los archivos
        filter_client: Lista de palabras clave para filtrar por cliente

    Returns:
        Dict[str, Any]: Estadísticas de la operación
    """
    logger.info("🔄 Iniciando descarga de correos DFE...")

    downloader = MsgDownloader(
        account_name=account_name,
        folder_name=folder_name,
        save_path=save_path,
        filter_client=filter_client,
    )

    stats = downloader.download_msg()

    logger.info(
        f"🏁 Proceso completado! "
        f"Total: {stats['total']}, "
        f"Descargados: {stats['descargados']}, "
        f"Omitidos (existentes): {stats['omitidos_existentes']}, "
        f"Omitidos (filtro): {stats['omitidos_filtro']}, "
        f"Errores: {stats['errores']}"
    )

    return stats


if __name__ == "__main__":
    # 🚀 Ejemplo de ejecución filtrando por cliente específico
    download_msgs(filter_client=["PFIZER"])

    # Para descargar todos los correos, simplemente no especifiques filter_client:
    # download_msgs()
