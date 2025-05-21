import os
from datetime import datetime

# import requests
from playwright_stealth import stealth_async
from playwright.async_api import Playwright, async_playwright, TimeoutError as PlaywrightTimeoutError, Page, Frame


from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Salta(Jurisdiccion):
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
            "Salta",
            "917 SALTA",
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

    # async def consultar_notificaciones(self):
    #     if (True):
    #         self.consultar_notificaciones_dgr()
    #     else:
    #         ...

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrsalta_rentas",
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        if int(str(self._cuit)[0]) != 3:
            await self.AFIP_login()
        else:
            await self.login()

        # Mejorar la verificación de login exitoso con timeout adecuado
        try:
            # Esperar adecuadamente a que la página cargue
            await self.page.wait_for_load_state("networkidle", timeout=30000)

            # Esperar específicamente al selector de logout con un timeout razonable
            await self.page.wait_for_selector(
                "#enviaLogout", timeout=15000, state="visible"
            )
            self.logger.debug("SALTA: Login exitoso, se encontró el selector de logout")
        except Exception as e:
            # Verificar si hay errores explícitos antes de concluir que falló el login
            if await self.page.is_visible("div.error_text"):
                error_text = await self.page.locator("div.error_text").text_content()
                self.logger.error(f"SALTA: Error de login detectado: {error_text}")
                raise LoginError(self.cliente, error_text)

            # Verificar una última vez si el selector existe pero tardó en aparecer
            if await self.page.query_selector("#enviaLogout"):
                self.logger.warning(
                    "SALTA: El selector de logout apareció después del timeout"
                )
            else:
                self.logger.error("SALTA: No se pudo verificar el login exitoso")
                # Usar mensaje predefinido en lugar de exponer la excepción
                raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)

        # Continuar con las acciones en la página (resto del código sin cambios)
        await self.page.wait_for_selector(
            "//a[contains(text(), 'Domicilio Fiscal Electrónico')]"
        )
        await self.page.locator(
            "//a[contains(text(), 'Domicilio Fiscal Electrónico')]"
        ).click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector(
            "//a[contains(text(), 'Ventanilla Única de Novedades')]"
        )
        await self.page.locator(
            "//a[contains(text(), 'Ventanilla Única de Novedades')]"
        ).click()
        await self.page.wait_for_load_state("networkidle")

    async def login(self):
        # await stealth_async(self.page)
        await self.page.goto("https://www.dgrsalta.gov.ar/rentassalta/login.jsp")
        await self.page.wait_for_load_state()
        await self.page.wait_for_selector("input#usuario")
        await self.page.fill("input#usuario", self._cuit)
        await self.page.fill("input#password", self._clave_fiscal)
        # await stealth_async(self.page)
        frame = next((f for f in self.page.frames if 'recaptcha' in f.url), None)
        if not frame:
            print("No se encontró el iframe de reCAPTCHA.")
        else:
            try:
                await self.humanoid_click(self.page, frame, '.recaptcha-checkbox-border')
                print("Clic en reCAPTCHA realizado con éxito.")
            except RuntimeError as e:
                print(f"Hubo un error al intentar hacer clic en reCAPTCHA: {e}")

        await self.page.click("a#enviaLogin")
        await self.page.wait_for_load_state("domcontentloaded")
        error_selector = "//div[@class='error_text' and contains(text(), 'Usuario o Password Incorrecto')]"
        if await self.page.is_visible(error_selector):
            raise LoginError(self.cliente)
        
    async def humanoid_click(page: Page, frame: Frame, selector: str, retries: int = 2):
        """
        Simula un clic humano en un elemento dentro de un frame.

        Args:
            page (Page): Página principal de Playwright.
            frame (Frame): Frame donde se encuentra el elemento.
            selector (str): Selector CSS del elemento.
            retries (int): Número de reintentos en caso de fallo.

        Raises:
            RuntimeError: Si no se puede hacer clic en el elemento después de los reintentos.
        """
        try:
            # Esperar que el selector esté visible en el frame
            await frame.locator(selector).wait_for(state="visible", timeout=10000)

            # Obtener la posición del elemento en el frame
            element = frame.locator(selector)
            box = await element.bounding_box()
            if not box:
                raise ValueError(f"No se pudo obtener la posición del elemento: {selector}")
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2

            # Ajustar las coordenadas del elemento al contexto de la página principal
            frame_box = await frame.evaluate("document.body.getBoundingClientRect()")
            x += frame_box["x"]
            y += frame_box["y"]

            # Mover mouse desde una posición superior izquierda simulando desplazamiento humano
            await page.mouse.move(x - 120, y - 120)
            await asyncio.sleep(0.2)
            await page.mouse.move(x, y, steps=20)
            await asyncio.sleep(0.4)

            # Hover y clic
            await page.mouse.click(x, y, delay=80)  # Delay para simular tiempo de reacción de clic
            await asyncio.sleep(0.4)

        except (PlaywrightTimeoutError, ValueError) as e:
            if retries > 0:
                print(f"Fallo al hacer clic en {selector}, reintentando... ({retries} restantes)")
                await asyncio.sleep(1)  # Espera antes de reintentar
                await humanoid_click(page, frame, selector, retries - 1)
            else:
                raise RuntimeError(f"Error al intentar hacer clic en {selector}") from e

    async def buscar_notificacion(self):
        elements = await self.page.locator(
            "//td[contains(text(),'Por el momento no tiene novedades...')]"
        ).all()
        return False if len(elements) == 2 else True

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    async def main():
        async with async_playwright() as playwright:
            fecha_desde = os.getenv("FECHA_DESDE")
            fecha_hasta = os.getenv("FECHA_HASTA")
            client = os.getenv("TEST_SALTA_CLIENT")
            client_folder = os.getenv("TEST_SALTA_CLIENT_FOLDER")
            cuit_Salta = os.getenv("TEST_SALTA_CUIT")
            clave_fiscal_Salta = os.getenv("TEST_SALTA_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_SALTA_CUIT_CLIENTE_INPUT")

            salta = await Salta.create(
                playwright,
                client,
                client_folder,
                cuit_Salta,
                clave_fiscal_Salta,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await salta.procesar_jurisdiccion()


    asyncio.run(main())
