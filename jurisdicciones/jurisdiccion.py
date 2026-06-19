"""
Este modulo contiene la clase Jurisdiccion y las clases correspondientes a excepciones.
"""

import asyncio
import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple, Union
from logger import Logger

from playwright.async_api import Page, Playwright

from dotenv import load_dotenv

load_dotenv()


class LoggedException(Exception):
    """Excepción base que registra errores."""

    def __init__(self, cliente, message):
        self.cliente = cliente
        self.message = message
        self.logger = Logger.get_logger()
        self.logger.error(f"Cliente: {self.cliente}, Error: {message}")
        self.logger.exception(message)
        super().__init__(message)  # Inicializar la clase base con el mensaje

    def __str__(self):
        # Devolver solo el mensaje cuando se convierte a string
        return self.message


class LoginError(LoggedException):
    """Excepción lanzada por errores en el inicio de sesión."""

    # Mensajes predefinidos para los errores más comunes
    CREDENCIALES_INVALIDAS = "Credenciales inválidas"
    SERVICIO_NO_DISPONIBLE = "Servicio no disponible"
    PENDIENTE_DELEGACION = "Servicio pendiente de delegación"
    SESION_EXPIRADA = "Sesión expirada"
    CREDENCIALES_ARCA = "Credenciales ARCA inválidas"
    PENDIENTE_ACEPTACION = "Pendiente de aceptación de T&C"
    CREDENCIALES_EXPIRADAS = "Credenciales expiradas"
    CAPTCHA_DETECTADO = "Captcha detectado en login"

    def __init__(self, cliente, mensaje=None):
        """
        Inicializa una excepción de error de login.

        Args:
            cliente: Nombre del cliente afectado
            mensaje: Mensaje personalizado o uno de los predefinidos (usa las constantes de clase)
        """
        # Guardar el mensaje original para referencia
        self.mensaje_original = mensaje

        # El message que se pasa a LoggedException será el mensaje personalizado o predefinido
        super().__init__(cliente, mensaje or self.CREDENCIALES_INVALIDAS)


class LoginErrorAfip(LoginError):
    """Excepción específica para errores de login en AFIP."""

    DEFAULT_MESSAGE = "Credenciales ARCA inválidas"
    PENDIENTE_DELEGACION = "Servicio pendiente de delegación"

    def __init__(self, cliente, mensaje=None):
        super().__init__(cliente, mensaje or self.DEFAULT_MESSAGE)


class ConsultarNotificacionesError(LoggedException):
    """Excepción lanzada por errores al consultar notificaciones."""

    DEFAULT_MESSAGE = "La página se encuentra caída"

    def __init__(self, cliente, message=None):
        super().__init__(cliente, message or self.DEFAULT_MESSAGE)


class BuscarNotificacionError(LoggedException):
    """Excepción lanzada por errores al buscar notificaciones."""

    DEFAULT_MESSAGE = "La página se encuentra caída"

    def __init__(self, cliente, message=None):
        super().__init__(cliente, message or self.DEFAULT_MESSAGE)


class TomarScreenshotError(LoggedException):
    """Excepción lanzada por errores al tomar screenshots."""

    DEFAULT_MESSAGE = "No hay screenshot"

    def __init__(self, cliente, message=None):
        super().__init__(cliente, message or self.DEFAULT_MESSAGE)


class DelegacionError(LoggedException):
    """Excepción lanzada por errores de delegación.
    Esta excepción NO realiza screenshot para evitar visualizar otras CUIT.
    No registra fecha_login_error porque no es necesario actualizar
    credenciales sino sólo delegar el servicio.
    """

    DEFAULT_MESSAGE = "Servicio pendiente de delegación"

    def __init__(self, cliente: str, message: Optional[str] = None) -> None:
        super().__init__(cliente, message or self.DEFAULT_MESSAGE)


class Jurisdiccion(ABC):
    """
    Clase base abstracta para representar una jurisdicción.

    Métodos:
        __init__: Inicializa una instancia de la clase Jurisdiccion.
        create: Method de clase asíncrono para crear e inicializar una instancia de Jurisdiccion.
        AFIP_login: Realiza el inicio de sesión en el portal de AFIP.
        consultar_notificaciones: Method abstracto para navegar hasta la sección de notificaciones de la jurisdicción.
        buscar_notificacion: Busca una notificación específica en la página.
        buscar_notificacion_texto_visible: Verifica si un texto específico es visible en la página.
        buscar_notificacion_xpath_visible: Verifica si un elemento específico es visible en la página utilizando un XPath.
        tomar_screenshot: Toma un screenshot de la sección de notificaciones de la jurisdicción.
        tomar_varias_screenshots: Toma varios screenshots de diferentes secciones de la jurisdicción.
        cerrar_navegador: Cierra el navegador.
        procesar_jurisdiccion: Procesa la jurisdicción, consultando notificaciones, buscando notificaciones y tomando screenshots.
        enviar_correo_errores: Envía un correo electrónico con los errores detectados.

    Métodos a implementar en clases hijas:
        consultar_notificaciones: Method utilizado para navegar hasta la sección de notificaciones de la jurisdicción.

    Ejemplo de implementación en una clase hija:

    class Chaco(Jurisdiccion):
        def __init__(self, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None, razon_social_cliente_input=None, texto_notificacion=None):
            super().__init__(nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input, razon_social_cliente_input, texto_notificacion)

        @classmethod
        async def create(cls, playwright: Playwright, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input, razon_social_cliente_input=None, texto_notificacion=None, headless=True):
            self = await super().create(playwright, "Chaco", "906 CHACO", cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input, razon_social_cliente_input, texto_notificacion, headless=headless)
            return self

        async def consultar_notificaciones(self):
            # Implementación específica para la jurisdicción de Chaco
            pass
    """

    def __init__(
        self,
        nombre,
        codigo,
        cliente,
        client_folder,
        cuit,
        clave_fiscal,
        fecha_desde,
        fecha_hasta,
        cuit_cliente_input=None,
        razon_social_cliente_input=None,
        texto_notificacion=None,
        headless=True,
    ):
        self.nombre = nombre
        self.codigo = codigo
        self.cliente = cliente
        self.client_folder = client_folder
        self._cuit = str(cuit)
        self._clave_fiscal = str(clave_fiscal)
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta
        self._cuit_cliente_input = str(cuit_cliente_input)
        self._razon_social_cliente_input = razon_social_cliente_input
        self.texto_notificacion = texto_notificacion
        self.browser = None
        self.context = None
        self.page: Page = None
        self.hay_notificacion = False
        self.hay_screenshot = False
        self.hora_actual = datetime.now().strftime("%H%M%S")
        self.error = (None,)
        self.headless = headless
        self.logger: logging.Logger

    @classmethod
    async def create(
        cls,
        playwright: Playwright,
        nombre: str,
        codigo: str,
        cliente: str,
        client_folder: str,
        cuit: str,
        clave_fiscal: str,
        fecha_desde: str,
        fecha_hasta: str,
        cuit_cliente_input: Optional[str] = None,
        razon_social_cliente_input: Optional[str] = None,
        texto_notificacion: Optional[str] = None,
        headless: bool = True,
        slow_mo: int = 0,  # Nuevo parámetro para configurar slow motion
        browser: Optional[object] = None,
        context: Optional[object] = None,
        page: Optional[Page] = None,
    ) -> "Jurisdiccion":
        """
        Crea e inicializa una instancia de Jurisdiccion.

        Args:
            playwright: Instancia de Playwright.
            nombre: Nombre de la jurisdicción.
            codigo: Código de la jurisdicción.
            cliente: Nombre del cliente.
            client_folder: Carpeta del cliente.
            cuit: CUIT del cliente.
            clave_fiscal: Clave fiscal del cliente.
            fecha_desde: Fecha de inicio del período.
            fecha_hasta: Fecha de fin del período.
            cuit_cliente_input: CUIT del cliente para input (opcional).
            razon_social_cliente_input: Razón social del cliente para input (opcional).
            texto_notificacion: Texto de notificación a buscar (opcional).
            headless: Si el navegador debe ejecutarse en modo headless.
            slow_mo: Tiempo en milisegundos para ralentizar las acciones de Playwright.

        Returns:
            Instancia de Jurisdiccion.
        """
        self = cls(
            nombre,
            codigo,
            cliente,
            client_folder,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            razon_social_cliente_input,
            texto_notificacion,
            headless,
        )
        self.client_folder = client_folder
        # Si el caller pasa un browser/context/page, reutilizarlos para permitir trazas
        if browser is not None:
            self.browser = browser
            # Usar el context pasado o crear uno nuevo a partir del browser
            if context is not None:
                self.context = context
            else:
                self.context = await self.browser.new_context()
            # Usar la page pasada o crear una nueva desde el context
            self.page = page or await self.context.new_page()
            # Indicador para saber si debemos cerrar el browser en cerrar_navegador()
            self._owns_browser = False
        else:
            # Crear browser/context/page propios
            self.browser = await playwright.chromium.launch(
                headless=headless, slow_mo=slow_mo
            )
            self.context = context or await self.browser.new_context()
            self.page = page or await self.context.new_page()
            self._owns_browser = True
        self.logger = Logger.get_logger()

        return self

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN: str = "https://auth.afip.gob.ar/contribuyente_/login.xhtml",
        success_selector: Optional[str] = None,
        success_url: Optional[str] = None,
        success_title: Optional[str] = None,
    ) -> None:
        """
        Realiza el inicio de sesión en el portal de AFIP.

        Args:
            URL_AFIP_LOGIN: URL del portal de login de AFIP.
            success_selector: Selector CSS que indica login exitoso (puede variar según URL).
            success_url: Parte de la URL que indica login exitoso (opcional).
            success_title: Título de la página que indica login exitoso (opcional).

        Raises:
            LoginErrorAfip: Cuando hay un error en el proceso de login.
        """
        try:
            await self.page.goto(URL_AFIP_LOGIN, timeout=180000)
            await self.page.get_by_role("spinbutton").click(timeout=18000)
            await self.page.get_by_role("spinbutton").fill(self._cuit, timeout=18000)
            await self.page.get_by_role("button", name="Siguiente").click(timeout=18000)

            # Verificar si aparece el mensaje de CUIL/CUIT incorrecto
            incorrect_login = await self.page.query_selector(
                ":has-text('Número de CUIL/CUIT incorrecto')"
            )
            if incorrect_login:
                raise LoginErrorAfip(self.cliente, "Número de CUIL/CUIT incorrecto")


            await self.page.get_by_text("Ingresar con Clave Fiscal ").wait_for(state="visible", timeout=18000)
            captcha_locator = self.page.locator("div#captcha")
            if await captcha_locator.is_visible():
                raise LoginError(
                    self.cliente, LoginError.CAPTCHA_DETECTADO
                )

            await self.page.get_by_label("TU CLAVE").click(timeout=18000)
            await self.page.get_by_label("TU CLAVE").fill(
                self._clave_fiscal, timeout=18000
            )

            await self.page.get_by_role("button", name="Ingresar").click(timeout=18000)
            # await self.page.wait_for_load_state("networkidle", timeout=180000)
            await self.page.wait_for_load_state("load", timeout=180000)

            error_locator = self.page.locator(
                'form[name="F1"]:has-text("Clave o usuario incorrecto")'
            )
            if await error_locator.is_visible():
                raise LoginErrorAfip(self.cliente)

            # Verificar si aparece el mensaje de cambio de contraseña obligatorio
            password_change_locator = self.page.get_by_text(
                "Por medidas de seguridad tenés que cambiar tu contraseña"
            )
            if await password_change_locator.is_visible():
                raise LoginErrorAfip(self.cliente, "Es necesario cambiar clave fiscal")

            # Verificar errores comunes solo si la URL actual es la esperada
            if self.page.url == URL_AFIP_LOGIN:
                error_selector = await self.page.query_selector("#F1\\:msg")
                if error_selector:
                    mensaje_error = await error_selector.inner_text()
                    raise LoginErrorAfip(self.cliente, mensaje=mensaje_error)

            # Verificar éxito mediante selector, URL o título
            if success_selector:
                await self.page.wait_for_selector(success_selector, timeout=60000)
                self.logger.info("Login en AFIP exitoso confirmado mediante selector.")
            elif success_url:
                if success_url in self.page.url:
                    self.logger.info("Login en AFIP exitoso confirmado mediante URL.")
            elif success_title:
                await self.page.wait_for_function(
                    f"document.title.includes('{success_title}')", timeout=60000
                )
                self.logger.info("Login en AFIP exitoso mediante título.")
            else:
                raise LoginErrorAfip(
                    self.cliente,
                    "No se proporcionó un criterio válido para confirmar el login exitoso.",
                )
        except LoginErrorAfip as e:
            self.logger.error(f"Error de login en AFIP: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado en AFIP_login: {e}")
            raise ConsultarNotificacionesError(
                self.cliente, f"Error inesperado: {str(e)}"
            ) from e

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

    async def buscar_notificacion_xpath_visible(
        self, xpath: str, page: Optional[Page] = None
    ) -> bool:
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

    async def tomar_screenshot(
        self, page: Optional[Page] = None, nombre_extra: Optional[str] = None
    ) -> bool:
        """Metodo utilizado para tomar un screenshot de la sección de notificaciones de la jurisdicción."""
        if page is None:
            page = self.page

        # Normalize dates by replacing slashes with underscores
        fecha_desde_norm = (
            self.fecha_desde.replace("/", "_")
            if "/" in self.fecha_desde
            else self.fecha_desde
        )
        fecha_hasta_norm = (
            self.fecha_hasta.replace("/", "_")
            if "/" in self.fecha_hasta
            else self.fecha_hasta
        )

        PATH_ESTRUCTURA_ROBOT = os.getenv("PATH_ESTRUCTURA_ROBOT")
        base_nombre_archivo = f"{PATH_ESTRUCTURA_ROBOT}/{self.client_folder}/Output/{self.nombre}_{self.client_folder}_{fecha_desde_norm}_{fecha_hasta_norm}_{self.hora_actual}"

        if nombre_extra:
            base_nombre_archivo += f"_{nombre_extra}"
        extension = ".png"
        nombre_archivo = base_nombre_archivo + extension
        contador = 1
        while os.path.exists(nombre_archivo):
            nombre_archivo = f"{base_nombre_archivo}_{contador}{extension}"
            contador += 1
        try:
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(
                5000
            )  # Wait an additional 5 seconds to ensure everything is loaded
            await page.screenshot(
                path=nombre_archivo, full_page=True, timeout=60000
            )  # Increase timeout to 60 seconds
            self.hay_screenshot = True
        except Exception as e:
            print(
                f"Error taking screenshot: {e}. Reintentando sin minimizar el navegador."
            )
            await self.maximizar_ventana()
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(5000)
                await page.screenshot(
                    path=nombre_archivo, full_page=True, timeout=60000
                )
                self.hay_screenshot = True
            except Exception as e:
                print(f"Reintento de screenshot falló: {e}")
        return self.hay_screenshot

    async def tomar_varias_screenshots(
        self,
        secciones: List[Tuple[str, str]],
        page: Optional[Page] = None,
        delay: int = 0,
    ) -> bool:
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
                PATH_ESTRUCTURA_ROBOT = os.getenv("PATH_ESTRUCTURA_ROBOT")

                fecha_desde_norm = (
                    self.fecha_desde.replace("/", "_")
                    if "/" in self.fecha_desde
                    else self.fecha_desde
                )
                fecha_hasta_norm = (
                    self.fecha_hasta.replace("/", "_")
                    if "/" in self.fecha_hasta
                    else self.fecha_hasta
                )
                nombre_archivo = f"{PATH_ESTRUCTURA_ROBOT}/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{fecha_desde_norm}_{fecha_hasta_norm}_{self.hora_actual}_{seccion}.png"

                await page.screenshot(path=nombre_archivo, full_page=True)
                self.hay_screenshot = True
            except Exception as e:
                print(f"Error taking screenshot: {e}")
                self.hay_screenshot = False
                raise Exception(f"Error taking screenshot: {e}") from e
        return self.hay_screenshot

    async def cerrar_navegador(self):
        """Cerrar el navegador solo si la instancia lo creó.

        Las instancias que reutilizan un browser/context externo no lo cerrarán.
        """
        try:
            if getattr(self, "_owns_browser", True):
                if self.browser:
                    await self.browser.close()
            else:
                # No cerrar browser que pertenece al caller.
                self.logger.info(
                    "No se cierra el browser porque no pertenece a la instancia."
                )
        except Exception as e:
            self.logger.exception(f"Error cerrando navegador: {e}")

    async def maximizar_ventana(self):
        if not self.headless:
            client = await self.page.context.new_cdp_session(self.page)
            window_info = await client.send("Browser.getWindowForTarget")
            window_id = window_info["windowId"]

            # Restaurar a estado normal si está minimizado o en pantalla completa
            await client.send(
                "Browser.setWindowBounds",
                {"windowId": window_id, "bounds": {"windowState": "normal"}},
            )

            # Maximizar la ventana
            await client.send(
                "Browser.setWindowBounds",
                {"windowId": window_id, "bounds": {"windowState": "maximized"}},
            )

    async def minimizar_ventana(self):
        if not self.headless:
            client = await self.page.context.new_cdp_session(self.page)
            window_info = await client.send("Browser.getWindowForTarget")
            window_id = window_info["windowId"]

            # Minimizar la ventana
            await client.send(
                "Browser.setWindowBounds",
                {"windowId": window_id, "bounds": {"windowState": "minimized"}},
            )

    async def cerrar_recursos(self):
        """Cierra todos los recursos de la instancia como navegador, contexto, etc."""
        try:
            if hasattr(self, "page") and self.page is not None:
                await self.page.close()
            if hasattr(self, "context") and self.context is not None:
                await self.context.close()
            if hasattr(self, "browser") and self.browser is not None:
                await self.browser.close()
        except Exception as e:
            self.logger.warning(f"Error al cerrar recursos de {self.nombre}: {e}")

    async def procesar_jurisdiccion(self) -> Tuple[str, str, str, Optional[str]]:
        """Procesa la jurisdicción, ejecutando todos los pasos necesarios.

        Returns:
            Tuple con (nombre_jurisdiccion, estado_notificacion, estado_screenshot, tipo_error)
        """
        self.error = None
        error_type = None

        # PASO 1: Consultar notificaciones
        error_type = await self._ejecutar_consulta_notificaciones()

        # PASO 2: Buscar notificaciones (solo si no hubo error previo)
        if not self.error:
            error_type = await self._ejecutar_busqueda_notificaciones() or error_type

        # PASO 3: Tomar screenshot (siempre intentar)
        screenshot_error_type = await self._ejecutar_tomar_screenshot()
        # Solo usar el error de screenshot si no hay un error más crítico
        if not error_type:
            error_type = screenshot_error_type

        # Cerrar el navegador al final
        await self.cerrar_navegador()

        return self.nombre, self.hay_notificacion, self.hay_screenshot, error_type

    async def _ejecutar_consulta_notificaciones(self) -> Optional[str]:
        """Ejecuta la consulta de notificaciones y maneja los errores."""
        try:
            await self.consultar_notificaciones()
            return None
        except LoginError as e:
            self.error = e
            self.hay_notificacion = e.message
            return "LoginError"
        except LoginErrorAfip as e:
            self.error = e
            self.hay_notificacion = e.message
            return "LoginErrorAfip"
        except DelegacionError as e:
            self.error = e
            self.hay_notificacion = e.message
            return "DelegacionError"
        except ConsultarNotificacionesError as e:
            self.error = e
            self.hay_notificacion = e.message
            return "ConsultarNotificacionesError"
        except Exception as e:
            self.error = ConsultarNotificacionesError(self.cliente)
            self.hay_notificacion = self.error.message
            return "ConsultarNotificacionesError"

    async def _ejecutar_busqueda_notificaciones(self) -> Optional[str]:
        """Ejecuta la búsqueda de notificaciones y maneja los errores."""
        try:
            notificacion = await self.buscar_notificacion()
            self.hay_notificacion = (
                "Hay notificaciones" if notificacion else "No hay notificaciones"
            )
            return None
        except Exception as e:
            self.error = BuscarNotificacionError(self.cliente)
            self.hay_notificacion = self.error.message
            return "BuscarNotificacionError"

    async def _ejecutar_tomar_screenshot(self) -> Optional[str]:
        """Ejecuta la toma de capturas de pantalla y maneja los errores."""
        try:
            # Si hay un error previo, verificar si debemos saltear el screenshot
            if self.error:
                error_type = (
                    self.error.__class__.__name__
                    if hasattr(self.error, "__class__")
                    else None
                )

                # Lista de tipos de error que no requieren screenshot
                errores_sin_screenshot = ["DelegacionError"]

                if error_type in errores_sin_screenshot:
                    self.logger.info(
                        f"Saltando screenshot para error tipo {error_type} en {self.nombre}"
                    )
                    self.hay_screenshot = (
                        "No se tomó screenshot (error de credenciales/delegación)"
                    )
                    return None

                # Para otros errores, continuar con el flujo normal de screenshot
                error_type_name = None
                if hasattr(self.error, "__class__") and hasattr(
                    self.error.__class__, "__name__"
                ):
                    error_type_name = self.error.__class__.__name__

                # Comprobar si la instancia tiene implementado el método tomar_screenshot_error
                if hasattr(self, "tomar_screenshot_error") and callable(
                    getattr(self, "tomar_screenshot_error")
                ):
                    try:
                        self.logger.info(
                            f"Usando método específico tomar_screenshot_error para {self.nombre}"
                        )
                        screenshot = await self.tomar_screenshot_error(
                            error_type=error_type_name
                        )
                        self.hay_screenshot = (
                            "Se realizó Screenshot"
                            if screenshot
                            else "No se realizó Screenshot"
                        )
                        return None
                    except Exception as e:
                        self.logger.warning(
                            f"Error al usar tomar_screenshot_error: {e}. Usando método estándar."
                        )
                        # Si falla el método específico, continuamos con el método estándar

                # Método estándar de captura de pantalla sin manejo de parámetro extra
                try:
                    nombre_extra = "error" if self.error else None
                    if nombre_extra:
                        # Intentar con el parámetro nombre_extra
                        screenshot = await self.tomar_screenshot(
                            nombre_extra=nombre_extra
                        )
                    else:
                        # Sin parámetro extra
                        screenshot = await self.tomar_screenshot()

                except TypeError as e:
                    # Si hay un error de tipo, es probable que el método no acepte nombre_extra
                    if "unexpected keyword argument 'nombre_extra'" in str(e):
                        self.logger.warning(
                            f"El método tomar_screenshot de {self.nombre} no acepta nombre_extra, tomando screenshot básico"
                        )
                        screenshot = await self.tomar_screenshot()
                    else:
                        # Si es otro tipo de error, propagar la excepción
                        raise e

                self.hay_screenshot = (
                    "Se realizó Screenshot"
                    if screenshot
                    else "No se realizó Screenshot"
                )
                return None

            # Si no hay error, intentar el tomar_screenshot normal
            try:
                screenshot = await self.tomar_screenshot()
                self.hay_screenshot = (
                    "Se realizó Screenshot"
                    if screenshot
                    else "No se realizó Screenshot"
                )
                return None
            except Exception as e:
                self.logger.error(f"Error al tomar screenshot: {e}")
                raise

        except Exception as e:
            if not self.error:  # Solo establecer error si no hay uno previo
                self.error = TomarScreenshotError(self.cliente)
            self.hay_screenshot = (
                str(self.error) if self.error else "Error al tomar screenshot"
            )
            return "TomarScreenshotError"

    async def tomar_screenshot_error(self, error_type=None):
        """Toma un screenshot cuando ocurre un error.

        Implementación base simple que agrega un sufijo con información del error al nombre del archivo.
        Las clases derivadas pueden sobreescribir este método para comportamientos específicos.

        Args:
            error_type: Tipo opcional de error para incluir en el nombre del archivo

        Returns:
            bool: True si el screenshot se tomó correctamente, False en caso contrario
        """
        try:
            # Determinar el mejor sufijo para el nombre del archivo
            error_suffix = "error"

            # Prioridad al mensaje original si existe
            if hasattr(self.error, "mensaje_original") and self.error.mensaje_original:
                # Normalizar mensaje para usarlo en nombre de archivo (reemplazar espacios y caracteres especiales)
                mensaje_normalizado = (
                    str(self.error.mensaje_original).replace(" ", "_").replace("/", "_")
                )
                error_suffix = f"error_{mensaje_normalizado}"
            # Si no hay mensaje original pero hay tipo de error, usarlo
            elif error_type:
                error_suffix = f"error_{error_type}"

            # Usar la página principal por defecto
            self.logger.info(
                f"Tomando screenshot de error para {self.nombre}: {error_suffix}"
            )

            # Verificar si el método tomar_screenshot acepta nombre_extra
            try:
                # Intentar con el parámetro nombre_extra
                self.hay_screenshot = await self.tomar_screenshot(
                    nombre_extra=error_suffix
                )
            except TypeError as e:
                # Si hay un error de tipo, es probable que el método no acepte nombre_extra
                if "unexpected keyword argument 'nombre_extra'" in str(e):
                    self.logger.warning(
                        f"El método tomar_screenshot de {self.nombre} no acepta nombre_extra, tomando screenshot básico"
                    )
                    self.hay_screenshot = await self.tomar_screenshot()
                else:
                    # Si es otro tipo de error, propagar la excepción
                    raise e

            return self.hay_screenshot
        except Exception as e:
            self.logger.error(
                f"Error al tomar screenshot de error en {self.nombre}: {str(e)}"
            )
            self.hay_screenshot = False
            return False

    def enviar_correo_errores(self, error):
        servidor_smtp = os.getenv("SERVIDOR_SMTP")
        puerto_smtp = os.getenv("PUERTO_SMTP")
        remitente = os.getenv("SENDER_EMAIL")
        receptor = [os.getenv("CORREO_NOTIFICACION_ERROR")]

        # Crear el mensaje
        msg = MIMEMultipart()
        msg["From"] = remitente
        msg["To"] = ";".join(receptor)
        msg["Subject"] = f"NFE Alert del cliente {self.client_folder}"
        msg.attach(
            MIMEText(
                f"""En la ejecución de NFE Alert del Cliente:
    <h3>{self.cliente}</h3>
    Se ha detectado el siguiente <b>Error: {str(error)}</b>
    Jurisdicción: {self.nombre}
    Cuit: {self._cuit}
    Fecha Desde: {self.fecha_desde}
    Fecha Hasta: {self.fecha_hasta}
    
    Por favor, revisar el log para más detalles.""",
                "html",
            )
        )

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(servidor_smtp, puerto_smtp) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.send_message(msg)
                print(f"Notificación de error enviada a {', '.join(receptor)}")
        except smtplib.SMTPException as e:
            print(f"Error al enviar el correo electrónico: {e}")
