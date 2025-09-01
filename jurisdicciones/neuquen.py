import re
import os
from typing import Optional

from playwright.async_api import (
    Playwright,
    async_playwright,
    Page,
    expect,
    TimeoutError as PlaywrightTimeoutError,
)

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError, DelegacionError


class Neuquen(Jurisdiccion):
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
        super().__init__(
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
        self.cuit_cliente_input = str(cuit_cliente_input)

    @classmethod
    async def create(
        cls,
        playwright: Playwright,
        cliente,
        client_folder,
        cuit,
        clave_fiscal,
        fecha_desde,
        fecha_hasta,
        cuit_cliente_input,
        razon_social_cliente_input=None,
        texto_notificacion=None,
        headless=True,
    ):
        self = await super().create(
            playwright,
            "Neuquen",
            "915 NEUQUEN",
            cliente,
            client_folder,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            razon_social_cliente_input,
            texto_notificacion,
            headless=headless,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def consultar_notificaciones(self):
        """
        Realiza la consulta de notificaciones eligiendo el método de login adecuado
        según el tipo de CUIT.
        """
        # Determinar qué tipo de login usar basado en el CUIT
        if self._cuit.startswith("30"):
            # Usar el login directo a Neuquen para empresas (CUIT tipo 30)
            await self.login_neuquen()
        else:
            # Usar el login a través de AFIP para otros tipos de CUIT
            await self.login_neuquen_afip()

        # El resto del procesamiento es común para ambos métodos de login

    async def login_neuquen(self):
        """Login directo al sitio de Neuquen usando usuario y contraseña."""
        await self.page.goto("https://rentasneuquenweb.gob.ar/nqn/Extranet/index.php")
        await self.page.locator("#btn_sit").click()
        await self.page.get_by_role("textbox", name="Usuario").click()
        await self.page.get_by_role("textbox", name="Usuario").fill(
            f"{self._cuit_cliente_input}"
        )
        await self.page.get_by_placeholder("Contraseña").click()
        await self.page.get_by_placeholder("Contraseña").fill(f"{self._clave_fiscal}")
        await self.page.get_by_role("button", name="Ingresar").click()

        # Verificar errores de login
        if (
            await self.page.locator(
                "text='Acción prohibida, por favor ingrese nuevamente al sistema.'"
            ).count()
        ) > 0:
            raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)
        if (
            await self.page.locator(
                "text='El nombre de usuario o la contraseña introducidos no son correctos'"
            ).count()
        ) > 0:
            raise LoginError(self.cliente, LoginError.CREDENCIALES_INVALIDAS)

    async def login_neuquen_afip(self):
        """Login a través del sistema de AFIP con redirección a Neuquen DFE."""
        # URL específica para Neuquen a través de AFIP
        URL_AFIP_NEUQUEN = "https://auth.afip.gob.ar/contribuyente_/login.xhtml"
        SUCCESS_SELECTOR = "input#buscadorInput"

        # Reutilizar el método AFIP_login de la clase base
        await self.AFIP_login(URL_AFIP_NEUQUEN, success_selector=SUCCESS_SELECTOR)

        try:
            await self.page.get_by_role("combobox", name="Buscador").click()
            await self.page.get_by_role("combobox", name="Buscador").fill(
                "Login SiNATrA"
            )
            await self.page.get_by_role("combobox", name="Buscador").press("Enter")
            async with self.page.expect_popup() as page2_info:
                await self.page.get_by_role(
                    "link", name="Login SiNATrA Acceso al"
                ).click()
            page2 = await page2_info.value
            self.page = page2
            self.new_page = page2
            if await self.page.get_by_label("CUIT a Representar:").is_visible():
                # Intentar seleccionar directamente; si no selecciona nada o timed out,
                # considerar pendiente de aceptación
                try:
                    selected = await self.page.get_by_label(
                        "CUIT a Representar:"
                    ).select_option(self._cuit_cliente_input)
                except PlaywrightTimeoutError as e:
                    # Timeout usually means the option was not found / not visible
                    self.logger.warning(
                        f"Timeout seleccionando CUIT {self._cuit_cliente_input}: {e}"
                    )
                    # Usar DelegacionError para evitar tomar screenshots y tratar como delegación
                    raise DelegacionError(self.cliente) from e
                except Exception as e:
                    # Any other error treat as delegation for safety
                    self.logger.warning(
                        f"Error seleccionando CUIT {self._cuit_cliente_input}: {e}"
                    )
                    raise DelegacionError(self.cliente) from e

                if not selected:
                    self.logger.warning(
                        f"CUIT {self._cuit_cliente_input} no encontrado en las opciones disponibles"
                    )
                    raise DelegacionError(self.cliente)
                self.logger.info(f"Seleccionado CUIT {selected} del dropdown")
                await self.page.get_by_role("button", name="Ingresar").click()
            await expect(
                self.page.get_by_text("Bandeja de Mensajes - Notificaciones")
            ).to_be_visible()

        except Exception as e:
            self.logger.error(f"Error completando login AFIP para Neuquen: {str(e)}")
            # Intentar tomar un screenshot del error antes de lanzar la excepción
            await self.tomar_screenshot_error("afip_login_error")

            # Determinar el tipo de error apropiado
            if isinstance(e, LoginError):
                raise  # Re-lanzar si ya es un LoginError
            else:
                # Convertir otros errores en LoginError genérico
                raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)

    async def buscar_notificacion(self):
        await self.page.wait_for_load_state(
            "networkidle"
        )  # necesario para encontrar los elementos
        cantidad_notificaciones = await self.page.locator("#cant_notif").inner_text()
        cantidad_comunicaciones = await self.page.locator("#cant_comunic").inner_text()
        # Extrae solo los números del texto
        cantidad_notificaciones = re.findall(r"\d+", cantidad_notificaciones)
        cantidad_comunicaciones = re.findall(r"\d+", cantidad_comunicaciones)
        if cantidad_notificaciones and cantidad_comunicaciones:
            total_notificaciones = int(cantidad_notificaciones[0]) + int(
                cantidad_comunicaciones[0]
            )
        else:
            total_notificaciones = 0
        self.hay_notificacion = total_notificaciones > 0
        return self.hay_notificacion

    async def tomar_screenshot(
        self, page: Optional[Page] = None, nombre_extra: Optional[str] = None
    ):
        """Tomar screenshots en la jurisdicción de Neuquen, incluso en caso de error."""
        # Normalizar fechas para el nombre del archivo
        self.fecha_desde = self.fecha_desde.replace("/", "")
        self.fecha_hasta = self.fecha_hasta.replace("/", "")

        # Verificar si hubo un error de login o consulta
        if hasattr(self, "error") and self.error is not None:
            # Si hay un error, intentar un screenshot directo sin usar tomar_screenshot_error
            try:
                # Determinar el sufijo de error
                error_type = getattr(self.error, "error_type", None)
                error_suffix = f"_error_{error_type}" if error_type else "_error"

                # Usar la página correcta y propagar el parámetro nombre_extra correctamente
                screenshot_page = page if page is not None else self.page
                self.hay_screenshot = await super().tomar_screenshot(
                    screenshot_page, nombre_extra=error_suffix
                )
                return self.hay_screenshot
            except Exception as e:
                self.logger.error(
                    f"Error al tomar screenshot de error en Neuquen: {str(e)}"
                )
                return False

        # Continuar con el flujo normal si no hay errores
        try:
            secciones = [
                ("notificaciones", 'xpath=//a[@href="div_notificaciones"]'),
                ("comunicaciones", 'xpath=//a[@href="div_comunicaciones"]'),
            ]
            # Si se ha pasado un page específico, usarlo
            screenshot_page = page if page is not None else self.page
            self.hay_screenshot = await super().tomar_varias_screenshots(
                secciones, screenshot_page
            )
            return self.hay_screenshot
        except Exception as e:
            self.logger.error(
                f"Error al tomar screenshots normales en Neuquen: {str(e)}"
            )
            # En caso de error al tomar los screenshots normales, intentar un screenshot simple
            try:
                screenshot_page = page if page is not None else self.page
                # Asegurarse de pasar el parámetro nombre_extra correctamente
                fallback_name = nombre_extra if nombre_extra else "_fallback"
                self.hay_screenshot = await super().tomar_screenshot(
                    screenshot_page, nombre_extra=fallback_name
                )
                return self.hay_screenshot
            except Exception as fallback_error:
                self.logger.error(
                    f"Error al tomar screenshot de fallback: {str(fallback_error)}"
                )
                return False

    async def tomar_screenshot_error(self, error_type=None):
        """Toma un screenshot cuando ocurre un error, con lógica específica para Neuquen.

        Args:
            error_type: Tipo opcional de error para incluir en el nombre del archivo

        Returns:
            bool: True si el screenshot se tomó correctamente, False en caso contrario
        """
        try:
            # Normalizar fechas para el nombre del archivo si es necesario
            fecha_desde_normalizada = self.fecha_desde.replace("/", "")
            fecha_hasta_normalizada = self.fecha_hasta.replace("/", "")

            # Crear nombre de archivo con información del error
            error_suffix = f"_error_{error_type}" if error_type else "_error"

            # Determinar qué página está disponible para el screenshot
            screenshot_page = self.page
            if hasattr(self, "new_page_2") and self.new_page_2 is not None:
                self.logger.debug(
                    "Usando new_page_2 para screenshot de error en Neuquen"
                )
                screenshot_page = self.new_page_2
            elif hasattr(self, "new_page") and self.new_page is not None:
                self.logger.debug("Usando new_page para screenshot de error en Neuquen")
                screenshot_page = self.new_page

            # Tomar el screenshot
            self.logger.info(f"Tomando screenshot de error para Neuquen: {error_type}")
            self.hay_screenshot = await self.tomar_screenshot(
                screenshot_page, nombre_extra=error_suffix
            )
            return self.hay_screenshot
        except Exception as e:
            self.logger.error(
                f"Error al tomar screenshot de error en Neuquen: {str(e)}"
            )
            self.hay_screenshot = False
            return False

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")
        client = os.getenv("TEST_NEUQUEN_CLIENT")
        cuit_Neuquen = os.getenv("TEST_NEUQUEN_CUIT")
        clave_fiscal_Neuquen = os.getenv("TEST_NEUQUEN_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_NEUQUEN_CUIT_CLIENTE_INPUT")

        neuquen = await Neuquen.create(
            playwright,
            client,
            cuit_Neuquen,
            clave_fiscal_Neuquen,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        # await neuquen.AFIP_login()
        await neuquen.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
