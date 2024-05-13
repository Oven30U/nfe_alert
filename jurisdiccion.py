"""
Este modulo contiene la clase Jurisdiccion.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from abc import ABC, abstractmethod
from datetime import datetime
from playwright.async_api import Playwright
import logging
import os


class LoggedException(Exception):
    """Excepción base que registra errores."""

    def __init__(self, message, cliente):
        self.cliente = cliente
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.ERROR)

        log_file_path = "Estructura-robot/System/logfile.log"
        log_file_dir = os.path.dirname(log_file_path)
        os.makedirs(log_file_dir, exist_ok=True)
        handler = logging.FileHandler(log_file_path)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.error(f"Cliente: {self.cliente}, Error: {message}")
        self.logger.exception(message)

        super().__init__(message)


class LoginError(LoggedException):
    """Excepción lanzada por errores en el inicio de sesión."""

    pass


class ConsultarNotificacionesError(LoggedException):
    """Excepción lanzada por errores al consultar notificaciones."""
    pass


class BuscarNotificacionError(LoggedException):
    """Excepción lanzada por errores al buscar notificaciones."""
    pass


class TomarScreenshotError(LoggedException):
    """Excepción lanzada por errores al tomar screenshots."""
    pass


class Jurisdiccion(ABC):
    @classmethod
    async def create(cls, playwright: Playwright, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None, razon_social_cliente_input=None, texto_notificacion=None):
        self = cls()
        self.nombre = nombre
        self.codigo = codigo
        self.cliente = cliente
        self._cuit = str(cuit)
        self._clave_fiscal = str(clave_fiscal)
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta
        self._cuit_cliente_input = str(cuit_cliente_input)
        self._razon_social_cliente_input = razon_social_cliente_input
        self.texto_notificacion = texto_notificacion
        # Modificar el headless a False para ver la navegación y a True para que sea invisible en entorno de producción
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.hay_notificacion = False
        self.hay_screenshot = False
        self.hora_actual = datetime.now().strftime("%H%M%S")
        self.error = None
        return self

    async def AFIP_login(self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"):
        await self.page.goto(URL_AFIP_LOGIN)
        await self.page.get_by_role("spinbutton").click()
        await self.page.get_by_role("spinbutton").fill(self._cuit)
        await self.page.get_by_role("button", name="Siguiente").click()
        incorrect_login = await self.page.query_selector(":has-text('Número de CUIL/CUIT incorrecto')")
        if incorrect_login:
            raise LoginError("Login CUIT incorrecto")
        await self.page.get_by_label("TU CLAVE").click()
        await self.page.get_by_label("TU CLAVE").fill(self._clave_fiscal)
        await self.page.get_by_role("button", name="Ingresar").click()
        await self.page.wait_for_load_state("networkidle")  # add this line
        incorrect_login = await self.page.query_selector(":has-text('Clave o usuario incorrecto')")
        if incorrect_login:
            raise LoginError("Login pass incorrecto")

    @abstractmethod
    def consultar_notificaciones(self):
        """Metodo utilizado para navegar hasta la sección de notificaciones de la jurisdicción."""
        pass

    async def buscar_notificacion(self, page=None ,texto=None):
        """
        Si aparece el texto retorna hay_notificacion = true
        """
        if page is None:
            page = self.page
        if texto is None:
            texto = self.texto_notificacion
        notificacion = await page.query_selector(f":has-text('{texto}')")
        self.hay_notificacion = notificacion is not None
        return self.hay_notificacion

    async def tomar_screenshot(self, page=None):
        """Metodo utilizado para tomar un screenshot de la sección de notificaciones de la jurisdicción."""
        if page is None:
            page = self.page
        nombre_archivo = f"Estructura-robot/{self.cliente}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}.png"
        try:
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot = True
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot: {e}") from e
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        self.error = None

        try:
            await self.consultar_notificaciones()
        except LoginError as e:
            self.error = e
            self.enviar_correo_errores(self.error)
        except Exception as e:
            self.error = ConsultarNotificacionesError(
                "Error al consultar notificaciones", self.cliente
            )
            print(e)
            self.enviar_correo_errores(self.error)

        if not self.error:
            try:
                self.hay_notificacion = await self.buscar_notificacion()
            except Exception as e:
                self.error = BuscarNotificacionError(
                    "Error al buscar notificación", self.cliente
                )
                print(e)
                self.enviar_correo_errores(self.error)

        if not self.error:
            try:
                await self.tomar_screenshot()
            except Exception as e:
                self.error = TomarScreenshotError("Error al tomar screenshot", self.cliente)
                print(e)
                self.enviar_correo_errores(self.error)
            else:
                self.hay_screenshot = True

            self.hay_notificacion = (
                "Hay notificaciones"
                if self.hay_notificacion
                else "No hay notificaciones"
            )
            self.hay_screenshot = (
                "Se realizó Screenshot"
                if self.hay_screenshot
                else "No se realizó Screenshot"
            )

        return self.nombre, self.hay_notificacion, self.hay_screenshot, self.error

    def enviar_correo_errores(self, error):
        servidor_smtp = "appmail.atrame.deloitte.com"
        puerto_smtp = 25
        remitente = "robot-Tax-AR@deloitte.com"
        # remitente = "cgonzaleztorres@deloitte.com"
        receptor = [
            "lmarinaro@deloitte.com"
        ]  # Todo Reemplazar con laz direcciones del equipo
        # "cgonzaleztorres@deloitte.com; lmarinaro@deloitte.com; apiselli@deloitte.com; lecaracciolo@deloitte.com; rtolaba@deloitte.com; amiriarte@deloitte.com"

        # Crear el mensaje
        msg = MIMEMultipart()
        msg["From"] = remitente
        msg["To"] = ";".join(receptor)
        msg["Subject"] = (
            f"Revisión de Domicilios Fiscales Electronicos del cliente {self.cliente}"
        )
        msg.attach(
            MIMEText(
                f"En la ejecución de Revisión de Domicilios fiscales del Cliente:\n <h3>{self.cliente}</h3>\n Se ha detectado el siguiente <b>Error: {str(self.error)}<b>\n Jurisdicción: {self.nombre}\n Cuit: {self._cuit}\n Fecha Desde: {self.fecha_desde}\n Fecha Hasta: {self.fecha_hasta}\n \n Por favor, revisar el log para más detalles.",
                "html",
            )
        )

        # Enviar el correo electrónico
        with smtplib.SMTP(servidor_smtp, puerto_smtp) as server:
            server.send_message(msg)

