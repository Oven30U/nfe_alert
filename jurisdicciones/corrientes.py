import os
from datetime import datetime
import re

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Corrientes(Jurisdiccion):
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
        slow_mo=0,
        browser=None,
        context=None,
        page=None,
    ):
        self = await super().create(
            playwright,
            "Corrientes",
            "905 CORRIENTES",
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
            slow_mo=slow_mo,
            browser=browser,
            context=context,
            page=page,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        self.headless = headless
        return self

    async def consultar_notificaciones(self):
        await self.page.goto("https://miportal.dgrcorrientes.gov.ar/")
        await self.page.get_by_role("textbox", name="CUIT o Usuario").click()
        await self.page.get_by_role("textbox", name="CUIT o Usuario").fill(
            "30598129246"
        )
        await self.page.get_by_role("textbox", name="Clave virtual").click()
        await self.page.get_by_role("textbox", name="Clave virtual").fill("Janssen22")
        await self.page.get_by_role("button", name="Ingresar").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("text=Domicilio Fiscal Electrónico")
        await (
            self.page.locator("div")
            .filter(has_text=re.compile(r"^DFEDomicilio Fiscal Electrónico$"))
            .nth(1)
            .click()
        )
        await self.page.wait_for_selector("text=Notificaciones")

    async def buscar_notificacion(self):
        await self.page.locator(".css-1hwfws3").click()
        await self.page.get_by_text("No Leidos", exact=True).click()
        await self.page.wait_for_load_state("networkidle")

        text = await self.page.locator("#root").inner_text()
        if "no se encontraron resultados" in text:
            return False
        dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", text)
        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")
        for date_str in dates:
            try:
                cell_date = datetime.strptime(date_str, "%d/%m/%Y")
                if fecha_desde_dt <= cell_date <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue
        return False

    async def tomar_screenshot(self):
        if not self.headless:
            await super().maximizar_ventana()
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    async def main():
        async with async_playwright() as playwright:
            fecha_desde = os.getenv("FECHA_DESDE")
            fecha_hasta = os.getenv("FECHA_HASTA")

            client = os.getenv("TEST_CORRIENTES_CLIENT")
            cuit_Corrientes = os.getenv("TEST_CORRIENTES_CUIT")
            clave_fiscal_Corrientes = os.getenv("TEST_CORRIENTES_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_CORRIENTES_CUIT_CLIENTE_INPUT")

            corrientes = await Corrientes.create(
                playwright,
                client,
                cuit_Corrientes,
                clave_fiscal_Corrientes,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await corrientes.procesar_jurisdiccion()

    asyncio.run(main())
