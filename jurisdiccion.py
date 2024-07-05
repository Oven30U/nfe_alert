"""
Este modulo contiene la clase Jurisdiccion y las clases correspondientes a excepciones.
"""

from typing import Tuple, Optional, Union, List
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from abc import ABC, abstractmethod
from datetime import datetime
from playwright.async_api import Playwright, Page
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
    """
    Clase abstracta que representa una jurisdicción. Esta clase define la estructura y los métodos comunes
    que deben implementar las clases que representan a las diferentes jurisdicciones.

    Atributos:
        nombre (str): Nombre de la jurisdicción.
        codigo (str): Código de la jurisdicción.
        cliente (str): Nombre del cliente.
        _cuit (str): CUIT del cliente.
        _clave_fiscal (str): Clave fiscal del cliente.
        fecha_desde (str): Fecha de inicio del periodo a consultar.
        fecha_hasta (str): Fecha de fin del periodo a consultar.
        _cuit_cliente_input (str): CUIT del cliente a ingresar en la consulta.
        _razon_social_cliente_input (str): Razón social del cliente a ingresar en la consulta.
        texto_notificacion (str): Texto de la notificación a buscar.
        browser (Browser): Instancia del navegador a utilizar.
        context (BrowserContext): Contexto del navegador.
        page (Page): Página actual del navegador.
        hay_notificacion (bool): Indica si se encontró una notificación.
        hay_screenshot (bool): Indica si se tomó un screenshot.
        hora_actual (str): Hora actual en formato HHMMSS.
        error (LoggedException): Error ocurrido durante el procesamiento de la jurisdicción.

    Métodos:
        create: Método de clase para crear una instancia de la jurisdicción.
        AFIP_login: Realiza el inicio de sesión en AFIP.
        consultar_notificaciones: Navega hasta la sección de notificaciones de la jurisdicción.
        buscar_notificacion: Busca una notificación en la página.
        buscar_notificacion_texto_visible: Verifica si un texto específico es visible en la página.
        buscar_notificacion_xpath_visible: Verifica si un elemento específico es visible en la página utilizando un XPath.
        tomar_screenshot: Toma un screenshot de la sección de notificaciones de la jurisdicción.
        tomar_varias_screenshots: Toma varios screenshots de diferentes secciones de la jurisdicción.
        cerrar_navegador: Cierra el navegador.
        procesar_jurisdiccion: Procesa la jurisdicción, consultando notificaciones, buscando una notificación y tomando un screenshot.
        enviar_correo_errores: Envía un correo electrónico con los errores ocurridos durante el procesamiento de la jurisdicción.
    """

    @classmethod
    async def create(
            cls,
            playwright: Playwright,
            nombre,
            codigo,
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input=None,
            razon_social_cliente_input=None,
            texto_notificacion=None,
    ):
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
        # True = Producción
        # False = Desarrollo
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.hay_notificacion = False
        self.hay_screenshot = False
        self.hora_actual = datetime.now().strftime("%H%M%S")
        self.error = None
        return self

    async def AFIP_login(
            self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"
    ):
        await self.page.goto(URL_AFIP_LOGIN)
        await self.page.get_by_role("spinbutton").click()
        await self.page.get_by_role("spinbutton").fill(self._cuit)
        await self.page.get_by_role("button", name="Siguiente").click()
        incorrect_login = await self.page.query_selector(
            ":has-text('Número de CUIL/CUIT incorrecto')"
        )
        if incorrect_login:
            raise LoginError("Login CUIT incorrecto")
        await self.page.get_by_label("TU CLAVE").click()
        await self.page.get_by_label("TU CLAVE").fill(self._clave_fiscal)
        await self.page.get_by_role("button", name="Ingresar").click()
        await self.page.wait_for_load_state(
            "networkidle"
        )  # esperar que cargue la página, si el link no es AFIP puro, entonces redirige a juridiscción
        if URL_AFIP_LOGIN == "https://auth.afip.gob.ar/contribuyente_/login.xhtml":
            incorrect_login = await self.page.query_selector(
                ":has-text('Clave o usuario incorrecto')"
            )
            if incorrect_login:
                raise LoginError("Login pass incorrecto")

    @abstractmethod
    def consultar_notificaciones(self):
        """Metodo utilizado para navegar hasta la sección de notificaciones de la jurisdicción."""
        pass

    async def buscar_notificacion(
            self, page: Optional[Page] = None, texto: Optional[str] = None
    ) -> bool:
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

    async def buscar_notificacion_texto_visible(
            self, texto: str, page: Optional[Page] = None
    ) -> bool:
        """
        Verifica si un texto específico es visible en la página.

        Parámetros:
        page (Optional[Page]): La página en la que se buscará el texto. Si no se proporciona, se utilizará self.page.
        texto (Optional[str]): El texto que se buscará en la página. Si no se proporciona, se utilizará self.texto_notificacion.

        Devuelve:
        bool: True si el texto es visible en la página, False en caso contrario.

        Nota:
        Si se busca el texto que indica que no hay notificaciones, utilizar not para que
        self.hay_notificaciones sea False en caso de que el texto aparezca visible:
            return not await self.buscar_notificacion_texto_visible(self.page, "No se encontraron resultados")
        """
        if page is None:
            page = self.page
        if texto is None:
            texto = self.texto_notificacion
        es_visible = await page.is_visible(f"text={texto}")
        return es_visible

    async def buscar_notificacion_xpath_visible(self, xpath: str, page: Optional[Page] = None) -> bool:
        """
        Verifica si un elemento específico es visible en la página utilizando un XPath.

        Parámetros:
        page (Optional[Page]): La página en la que se buscará el elemento. Si no se proporciona, se utilizará self.page.
        xpath (Optional[str]): El XPath que se utilizará para buscar el elemento en la página.

        Devuelve:
        bool: True si el elemento es visible en la página, False en caso contrario.

        Nota:
        Si se busca el xpath que indica que no hay notificaciones, utilizar not para que
        self.hay_notificaciones sea False en caso de que el xpath aparezca visible:
            return not await self.buscar_notificacion_xpath_visible(self.page,"//table[@id='listaNotificacionesTCTodas']//tbody/tr//*[contains(text(), 'No se encontraron resultados')]")
        """
        if page is None:
            page = self.page
        if xpath is None:
            raise ValueError("Se debe proporcionar un XPath válido.")

        es_visible = await page.is_visible(f"xpath={xpath}")
        return es_visible

    async def tomar_screenshot(self, page: Optional[Page] = None) -> bool:
        """Metodo utilizado para tomar un screenshot de la sección de notificaciones de la jurisdicción."""
        if page is None:
            page = self.page
        nombre_archivo = f"Estructura-robot\\{self.cliente}\\Output\\{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}.png"
        try:
            await page.wait_for_load_state("domcontentloaded")
            await page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot = True
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot: {e}") from e
        return self.hay_screenshot

    async def tomar_varias_screenshots(self, secciones: List[Tuple[str, str]], page: Optional[Page] = None,
                                       delay: int = 0) -> bool:
        """Metodo utilizado para tomar varios screenshots de diferentes secciones de la jurisdicción."""
        if page is None:
            page = self.page
        for seccion, selector in secciones:
            try:
                await page.click(selector)
                await asyncio.sleep(delay)  # Agrega una pausa después de cada clic
                await page.wait_for_load_state("networkidle")
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("load")
                nombre_archivo = f"Estructura-robot/{self.cliente}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
                await page.screenshot(path=nombre_archivo, full_page=True)
                self.hay_screenshot = True
            except Exception as e:
                print(f"Error taking screenshot: {e}")
                self.hay_screenshot = False
                raise Exception(f"Error taking screenshot: {e}") from e
        return self.hay_screenshot

    async def cerrar_navegador(self):
        await self.browser.close()

    async def procesar_jurisdiccion(
            self,
    ) -> Tuple[str, str, str, Optional[Union[LoggedException, None]]]:
        self.error = None

        try:
            await self.consultar_notificaciones()
        except LoginError as e:
            self.error = e
            # self.enviar_correo_errores(self.error)
        except ConsultarNotificacionesError as e:
            self.error = e
            # self.enviar_correo_errores(self.error)
        except Exception as e:
            self.error = ConsultarNotificacionesError(
                "Error al consultar notificaciones", self.cliente
            )
            print(e)
            # self.enviar_correo_errores(self.error)

        if not self.error:
            try:
                notificacion = await self.buscar_notificacion()
                self.hay_notificacion = (
                    "Hay notificaciones" if notificacion else "No hay notificaciones"
                )
            except LoginError as e:
                # Handle the exception, for example by logging it and returning it
                logging.error(f"Error during consultar_notificaciones: {e}")
                self.error = e
                self.enviar_correo_errores(self.error)
            except Exception as e:
                self.error = BuscarNotificacionError(
                    "Error al buscar notificación", self.cliente
                )
                print(e)
                # self.enviar_correo_errores(self.error)

        if not self.error:
            try:
                screenshot = await self.tomar_screenshot()
                self.hay_screenshot = (
                    "Se realizó Screenshot"
                    if screenshot
                    else "No se realizó Screenshot"
                )
            except Exception as e:
                self.error = TomarScreenshotError(
                    "Error al tomar screenshot", self.cliente
                )
                print(e)
                # self.enviar_correo_errores(self.error)

        if self.error:
            self.hay_notificacion = "Error al buscar notificación"
            self.hay_screenshot = "Error al tomar screenshot"

        # Cerrar el navegador al final
        await self.cerrar_navegador()

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
