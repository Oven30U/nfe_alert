import asyncio
from datetime import datetime
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion


class Jujuy(Jurisdiccion):
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
    ):
        self = await super().create(
            playwright,
            "Jujuy",
            "Jujuy",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        return self

    async def consultar_notificaciones(self):
        await self.page.goto("https://www.rentasjujuyonline.gob.ar/")
        await self.page.fill("#vUSUID", self._cuit)
        await self.page.fill("#vCONTRING", self._cuit)
        await self.page.press("#vCONTRING", "Tab")
        await self.page.press("#vCONTRING", "Enter")
        # await self.page.click("#vBTN_INGRESAR")
        await self.page.wait_for_load_state("networkidle")
        await self.page.goto(
            "https://www.rentasjujuyonline.gob.ar/cedulavirtual/HCon_NotDFEwwRes.aspx"
        )
        await self.page.fill(
            "input#buscadorInput", "Servicios Administradora Tributaria de Entre Ríos"
        )
        asyncio.sleep(5)

        await self.page.click("a.dropdown-item")
        popup_info = await self.page.wait_for_event("popup")
        self.new_page = popup_info
        await self.new_page.wait_for_load_state("networkidle")
        cuit_contribuyente = await self.formatear_cuit(self._cuit_cliente_input)
        # await self.page.click(
        #     f'xpath=//*[@id="textoFiltro"][contains(text(), "{cuit_contribuyente}")]'
        # )
        await self.new_page.locator(
            f"xpath=//*[contains(text(), '{cuit_contribuyente}')]"
        ).click()
        await self.new_page.wait_for_load_state("load")
        await self.new_page.goto(
            "https://portal.ater.gob.ar/ventanillaVirtual/adhesionVentanilla.aspx"
        )
        await self.new_page.wait_for_load_state("load")

    async def buscar_notificacion(self):
        cantidad_avisos = (await self.new_page.locator("#avisos").inner_text()).strip(
            "()"
        )
        cantidad_notificaciones = (
            await self.new_page.locator("#notificaciones").inner_text()
        ).strip("()")
        total_notificaciones = int(cantidad_avisos) + int(cantidad_notificaciones)
        self.hay_notificacion = total_notificaciones > 0
        return self.hay_notificacion

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.new_page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Jujuy = "30714604356"
        clave_fiscal_Jujuy = "Edge2021!"
        cuit_cliente_input = "30714604356"
        jujuy = await Jujuy.create(
            playwright,
            client,
            cuit_Jujuy,
            clave_fiscal_Jujuy,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await jujuy.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
