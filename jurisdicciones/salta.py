import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Salta(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None,
                 razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input,
                         razon_social_cliente_input, texto_notificacion, headless)
        self.cuit_cliente_input = str(cuit_cliente_input)

    @classmethod
    async def create(
            cls,
            playwright: Playwright,
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            razon_social_cliente_input=None,
            texto_notificacion=None,
            headless=True
    ):
        self = await super().create(
            playwright,
            "Salta",
            "917 SALTA",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            razon_social_cliente_input,
            texto_notificacion,
            headless=headless
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def consultar_notificaciones(self):
        await self.page.goto("https://www.dgrsalta.gov.ar/rentassalta/login.jsp")
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@name='usuario']").fill(f"{self._cuit}")
        await self.page.locator("//input[@name='password']").fill(f"{self._clave_fiscal}")
        await self.page.locator("//span[contains(text(),'Ingresar')]").click()
        await self.page.wait_for_load_state("networkidle")
        if (
                await self.page.is_visible("text=Usuario o Password Incorrecto")
        ):
            raise LoginError(
                "Error de login en Salta, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//a[contains(text(), 'Domicilio Fiscal Electrónico')]")
        await self.page.locator("//a[contains(text(), 'Domicilio Fiscal Electrónico')]").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//a[contains(text(), 'Ventanilla Única de Novedades')]")
        await self.page.locator("//a[contains(text(), 'Ventanilla Única de Novedades')]").click()
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        elements = await self.page.locator("//td[contains(text(),'Por el momento no tiene novedades...')]").all()
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
            )
            await salta.procesar_jurisdiccion()


    asyncio.run(main())
