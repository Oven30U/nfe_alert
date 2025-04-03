import os
from datetime import datetime
import requests
from playwright.async_api import Playwright, async_playwright

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
                self.logger.error(
                    f"SALTA: No se pudo verificar el login exitoso: {str(e)}"
                )
                raise LoginError(
                    self.cliente, f"No se pudo verificar el login: {str(e)}"
                )

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
        await self.page.goto("https://www.dgrsalta.gov.ar/rentassalta/login.jsp")
        await self.page.wait_for_load_state()
        await self.page.wait_for_selector("input#usuario")
        await self.page.fill("input#usuario", self._cuit)
        await self.page.fill("input#password", self._clave_fiscal)
        await self.page.click("a#enviaLogin")
        await self.page.wait_for_load_state("domcontentloaded")
        error_selector = "//div[@class='error_text' and contains(text(), 'Usuario o Password Incorrecto')]"
        if await self.page.is_visible(error_selector):
            raise LoginError(self.cliente)

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
            cuit_Salta = os.getenv("TEST_SALTA_CUIT")
            clave_fiscal_Salta = os.getenv("TEST_SALTA_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_SALTA_CUIT_CLIENTE_INPUT")

            salta = await Salta.create(
                playwright,
                client,
                cuit_Salta,
                clave_fiscal_Salta,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await salta.procesar_jurisdiccion()

    asyncio.run(main())
