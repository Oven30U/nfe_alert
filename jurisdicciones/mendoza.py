import os
import time
from playwright._impl._errors import TimeoutError
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import (
    Jurisdiccion,
    LoginError,
    ConsultarNotificacionesError,
)


class Mendoza(Jurisdiccion):
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
            "Mendoza",
            "913 MENDOZA",
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
            slow_mo=600,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self
    
    async def is_logged_in(self) -> bool:
        """
        Verifica si el usuario ya ha iniciado sesión.

        Returns:
            bool: True si el usuario ha iniciado sesión, False en caso contrario
        """
        try:
            # Asegurar que la página haya terminado de cargar
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_load_state("networkidle")
            
            # Buscar el elemento de logout con timeout reducido
            logout_element = await self.page.wait_for_selector(
                "//a[contains(text(), 'Cerrar Sesión')]", 
                timeout=60000
            )
            
            # Variable explícita para el resultado
            is_logged_in_result: bool = logout_element is not None
            
            if is_logged_in_result:
                self.logger.info("Usuario ya ha iniciado sesión")
            else:
                self.logger.info("Usuario no ha iniciado sesión")
                
            return is_logged_in_result
            
        except TimeoutError:
            self.logger.info("Elemento 'Cerrar Sesión' no encontrado - usuario no logueado")
            return False
        except Exception as e:
            self.logger.error(f"Error verificando estado de login: {str(e)}")
            return False
        
    async def perform_login(self) -> None:
        """
        Realiza el proceso de inicio de sesión en el portal ATM Mendoza con un enfoque flexible.

        Prueba diferentes métodos de inicio de sesión según sea necesario, primero con la evaluación de funciones JS,
        luego con un clic en el botón si es necesario.

        Args:
            page: El objeto page de Playwright
        """
        try:
            # Esperar al selector del formulario de login
            await self.page.wait_for_selector("#cuit")

            # Completar el formulario de login
            # await self.page.fill("#cuit", "30712399623")
            # await self.page.fill("#password", "AbbVie2025.")
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.fill("#cuit", f"{self._cuit}")
            await self.page.fill("#password", f"{self._clave_fiscal}")
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_selector("#ingresar")

            # Esperar a que la función de login esté definida
            await self.page.wait_for_function("typeof window.entrar === 'function'")
            time.sleep(1.5)

            # Primer intento: Usar evaluate para invocar JavaScript function
            self.logger.info("Intentando iniciar sesión usando evaluación de función JS")
            await self.page.evaluate("entrar()")

            # Verificar si esto fue suficiente para iniciar sesión
            await self.page.wait_for_timeout(
                2000
            )  # Dar tiempo para que se complete el inicio de sesión
            if await self.is_logged_in():
                self.logger.info("Inicio de sesión exitoso con función JS")
                return

            # Segundo intento: Hacer clic en el botón de login
            self.logger.info(
                "La función JS no fue suficiente, haciendo clic en el botón de inicio de sesión"
            )
            await self.page.click("#ingresar")

            # Verificar si el login fue exitoso
            await self.page.wait_for_timeout(2000)
            if await self.is_logged_in():
                self.logger.info("Inicio de sesión exitoso después de hacer clic en el botón")
            else:
                self.logger.warning(
                    "El inicio de sesión podría haber fallado - 'Cerrar Sesión' no encontrado"
                )

        except Exception as e:
            self.logger.error(f"El proceso de inicio de sesión falló: {str(e)}")
            raise

    async def consultar_notificaciones(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await self.page.goto(
                    "https://atm.mendoza.gov.ar/portalatm/misTramites/misTramitesLogin.jsp",
                    timeout=120000,
                )
                break
            except Exception:
                if attempt < max_retries - 1:
                    continue
                else:
                    raise
        
        # if await self.is_logged_in():
        #     self.logger.info("Sesión ya iniciada. Saltando proceso de inicio de sesión.")
        # else:
        #     self.logger.info(
        #         "No se ha iniciado sesión. Iniciando proceso de inicio de sesión."
        #     )
        await self.perform_login()

        # await self.page.wait_for_load_state("domcontentloaded")
        # await self.page.fill("#cuit", f"{self._cuit}")
        # await self.page.fill("#password", f"{self._clave_fiscal}")
        # await self.page.locator("#ingresar").click()
        # await self.page.wait_for_load_state("domcontentloaded")

        try:
            await self.page.wait_for_selector(
                '//a[contains(text(), "Cerrar Sesión")]', timeout=30000
            )
        except TimeoutError as exc:
            # Capturar screenshot del error de login antes de lanzar la excepción
            error_screenshot_path = f"Estructura-robot/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_error_login.png"
            try:
                await self.page.screenshot(path=error_screenshot_path)
                self.hay_screenshot = True  # Marcar que se tomó un screenshot
            except Exception as screenshot_error:
                self.logger.error(
                    f"Error al tomar screenshot de error de login: {screenshot_error}"
                )
                self.hay_screenshot = False

            # Verificar el tipo de error específico
            if await self.page.is_visible("text=Su contraseña ha expirado"):
                raise LoginError(self.cliente, "Contraseña expirada") from exc
            else:
                raise LoginError(self.cliente, "Credenciales inválidas") from exc

        async with self.page.expect_popup() as popup_info:
            await self.page.click("#divDFE")
        self.new_page = await popup_info.value
        while True:
            await self.new_page.wait_for_load_state("networkidle")
            title = await self.new_page.title()
            if title == "Domicilio Fiscal Electrónico":
                break
        await self.new_page.locator(
            "xpath=(//*[@class='z-datebox'])[1]//input[1]"
        ).fill(self.fecha_desde)
        await self.new_page.locator(
            "xpath=(//*[@class='z-datebox'])[2]//input[1]"
        ).fill(self.fecha_hasta)
        await self.new_page.check("xpath=(//input[@type='radio'])[2]")  # Sólo sin Leer
        await self.new_page.locator("xpath=//button[text()='Buscar']").click()

    async def buscar_notificacion(self):
        """Busca notificaciones con vencimiento, intimaciones y comunicaciones sin leer. tbody [2, 5, 8]."""
        # Es necesario navegar entre las pestañas para renderizar los elementos
        self.hay_notificacion = False
        await self.new_page.get_by_text("NOTIFICACIONES CON VENCIMIENTO").click()
        notificaciones_con_vencimiento = await self.new_page.locator(
            "css=[class*='z-listitem']"
        ).count()
        await self.new_page.get_by_text("INTIMACIONES").click()
        intimaciones = await self.new_page.locator("css=[class*='z-listitem']").count()
        await self.new_page.get_by_text("COMUNICACIONES").click()
        comunicaciones = await self.new_page.locator(
            "css=[class*='z-listitem']"
        ).count()
        notificaciones_totales = (
            notificaciones_con_vencimiento + intimaciones + comunicaciones
        )
        if notificaciones_totales > 0:
            self.hay_notificacion = True

        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar tres screenshot's en la jurisdicción de Mendoza."""
        await self.new_page.get_by_text("NOTIFICACIONES CON VENCIMIENTO").click()
        seccion = "notificaciones_con_vencimiento"
        nombre_archivo = f"Estructura-robot/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.new_page.wait_for_load_state("domcontentloaded")
            await self.new_page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_notificaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        await self.new_page.get_by_text("INTIMACIONES").click()
        seccion = "intimaciones"
        nombre_archivo = f"Estructura-robot/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.new_page.wait_for_load_state("domcontentloaded")
            await self.new_page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_intimaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        await self.new_page.get_by_text("COMUNICACIONES").click()
        seccion = "comunicaciones"
        nombre_archivo = f"Estructura-robot/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.new_page.wait_for_load_state("domcontentloaded")
            await self.new_page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_comunicaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        if (
            self.hay_screenshot_notificaciones
            and self.hay_screenshot_intimaciones
            and self.hay_screenshot_comunicaciones
        ):
            self.hay_screenshot = True
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_MENDOZA_CLIENT")
        cuit_Mendoza = os.getenv("TEST_MENDOZA_CUIT")
        clave_fiscal_Mendoza = os.getenv("TEST_MENDOZA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_MENDOZA_CUIT_CLIENTE_INPUT")

        mendoza = await Mendoza.create(
            playwright,
            client,
            cuit_Mendoza,
            clave_fiscal_Mendoza,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await mendoza.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
