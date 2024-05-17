import asyncio
from datetime import datetime
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion, LoginError


class Chubut(Jurisdiccion):
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
            "Chubut",
            "Chubut",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        return self

    async def consultar_notificaciones(self):
        await self.page.goto(
            "https://servicios.dgrchubut.gov.ar/modulos/login_siat.php"
        )
        await self.page.wait_for_load_state("networkidle")
        await self.page.fill("xpath=//input[@name='log_user']", self._cuit)
        await self.page.fill("xpath=//input[@name='log_pass']", self._clave_fiscal)
        await self.page.click("xpath=//input[@class='entrar']")
        await self.page.wait_for_load_state("networkidle")
        incorrect_login = self.page.locator(
            'xpath=//div[text()="Verifique el Usuario-Contraseña ingresados!"]'
        )
        if await incorrect_login.count() > 0:
            raise LoginError("Login CUIT incorrecto", self.cliente)

        # Verifique el Usuario-Contraseña ingresados!

        # await self.page.click("#vBTN_INGRESAR")
        await self.page.wait_for_load_state("networkidle")
        await self.page.goto(
            "https://www.rentaschubutonline.gob.ar/cedulavirtual/HCon_NotDFEwwRes.aspx"
        )
        await self.page.wait_for_load_state("load")
        await self.page.fill(
            "#vFECDESDE", await self.formatear_fechas(self.fecha_desde)
        )
        await self.page.fill(
            "#vFECHASTA", await self.formatear_fechas(self.fecha_hasta)
        )
        await self.page.click("#IMAGE1")  # boton de buscar
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        filas_de_notificaciones = await self.page.query_selector(
            'xpath=//*[@id="Grid1ContainerTbl"]/tbody/tr'
        )
        self.hay_notificaciones = filas_de_notificaciones is not None
        return self.hay_notificacion

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Chubut = "30714604356"
        clave_fiscal_Chubut = "Edge2023"
        cuit_cliente_input = "30714604356"
        chubut = await Chubut.create(
            playwright,
            client,
            cuit_Chubut,
            clave_fiscal_Chubut,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await chubut.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
