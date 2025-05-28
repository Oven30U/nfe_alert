import os
from playwright._impl._errors import TimeoutError
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import (
    Jurisdiccion,
    LoginError,
    ConsultarNotificacionesError,
)


class SantaCruz(Jurisdiccion):
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
            "SantaCruz",
            "920 SANTA CRUZ",
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

    async def consultar_notificaciones(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await self.page.goto(
                    "https://sit.asip.gob.ar/stsc/Extranet/index.php",
                    timeout=120000,
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                else:
                    raise

        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.goto("https://sit.asip.gob.ar/stsc/Extranet/index.php")
        await self.page.click("//button[@id='btn_sit']//div[@class='col-md-4']")
        await self.page.get_by_role("textbox", name="Usuario").fill(self._cuit)
        await self.page.get_by_role("textbox", name="Contraseña").fill(self._clave_fiscal)
        await self.page.get_by_role("button", name="Ingresar").click()

        try:
            await self.page.wait_for_selector(
                "//li[@id='id_li_100282']//a[@class='nav-link nav-toggle']", timeout=30000
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
            if await self.page.wait_for_selector("//div[@class='bootbox-body']"):
                raise LoginError(self.cliente, "Credenciales inválidas") from exc
            # else:
            #     raise LoginError(self.cliente, "Credenciales inválidas") from exc

    async def buscar_notificacion(self):
        """Busca notificaciones, comunicaciones y contacto fiscal electronico sin leer. Falta relevar caso en donde existan notificaciones."""
        # Es necesario navegar entre las pestañas para renderizar los elementos
        self.hay_notificacion = False
        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar tres screenshot's en la jurisdicción de Santa Cruz."""
        
        await self.page.click("//a[normalize-space()='Notificaciones']")
        # await self.new_page.get_by_text("NOTIFICACIONES CON VENCIMIENTO").click()
        seccion = "notificaciones"
        nombre_archivo = f"Estructura-robot/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.page.wait_for_selector("//span[normalize-space()='Notificaciones']")
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_notificaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        # await self.new_page.get_by_text("INTIMACIONES").click()
        await self.page.click("//a[normalize-space()='Comunicaciones']")
        seccion = "comunicaciones"
        nombre_archivo = f"Estructura-robot/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_selector("//span[normalize-space()='Comunicaciones']")
            await self.page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_comunicaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e
        
        await self.page.click("//a[normalize-space()='Contacto Fiscal Electrónico']")
        # await self.new_page.get_by_text("COMUNICACIONES").click()
        seccion = "contacto fiscal electronico"
        nombre_archivo = f"Estructura-robot/{self.client_folder}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_selector("//span[normalize-space()='Contacto Fiscal Electrónico']")
            await self.page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_contacto_fiscal = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        if (
            self.hay_screenshot_notificaciones
            and self.hay_screenshot_comunicaciones
            and self.hay_screenshot_contacto_fiscal
        ):
            self.hay_screenshot = True
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_SANTA_CRUZ_CLIENT")
        cuit_SantaCruz = os.getenv("TEST_SANTA_CRUZ_CUIT")
        clave_fiscal_SantaCruz = os.getenv("TEST_SANTA_CRUZ_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_SANTA_CRUZ_CUIT_CLIENTE_INPUT")

        santa_cruz = await SantaCruz.create(
            playwright,
            client,
            cuit_SantaCruz,
            clave_fiscal_SantaCruz,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await santa_cruz.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
