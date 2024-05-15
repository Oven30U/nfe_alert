
import asyncio
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion

class Nacional(Jurisdiccion):
    @classmethod
    async def create(cls, playwright: Playwright, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None):
        self = await super().create(playwright, "Nacional", "AFIP", cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta)
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def AFIP_login(self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        await self.AFIP_login()
        await self.page.fill("input#buscadorInput", "Domicilio Fiscal Electrónico")
        # Click en la opción de DFE desplegada
        await self.page.click("a.dropdown-item")
        await asyncio.sleep(1)
        self.new_page = self.page.context.pages[1]
        await self.new_page.click('text="Recordar más tarde"')
        await self.new_page.click('text=" Comunicaciones de mis representados "')
        await self.new_page.click("#d-select-80")
        await self.new_page.click(f'xpath=//button[@id="{self.cuit_cliente_input}"]')
        await self.new_page.fill('xpath=(//input)[5]', f"{self.fecha_desde}")
        await self.new_page.fill('xpath=(//input)[6]', f"{self.fecha_hasta}")
        await self.new_page.keyboard.press("Tab")
        await self.new_page.keyboard.press("Enter")
        await self.new_page.select_option("select[name='filtroEstado']", "No Leída")

    async def buscar_notificacion(self):
        return not await super().buscar_notificacion(self.new_page, "No hay comunicaciones para mostrar")

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.new_page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01/05/2024"
        fecha_hasta = "30/05/2024"
        cuit_Nacional = "20386165476"
        clave_fiscal_Nacional = "Gabriel1994"
        cuit_cliente_input="30714604356"
        nacional = await Nacional.create(playwright, client, cuit_Nacional, clave_fiscal_Nacional, fecha_desde, fecha_hasta, cuit_cliente_input)
        await nacional.procesar_jurisdiccion()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())