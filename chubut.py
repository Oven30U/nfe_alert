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
            'xpath=//div[text()="Usuario/clave incorrectos"]'
        )
        if await incorrect_login.count() > 0:
            raise LoginError("Login CUIT incorrecto", self.cliente)

    async def buscar_notificacion(self):
        fecha_desde_datetime = datetime.strptime(self.fecha_desde, "%d%m%Y")
        notificaciones = await self.page.locator(
            "xpath=//td[@aria-describedby='detail_grid_F_VIG_DESDE']"
        ).element_handles()
        self.hay_notificacion = False
        for notificacion in notificaciones:
            fecha_notificacion_text = await notificacion.inner_text()
            fecha_notificacion_datetime = datetime.strptime(
                fecha_notificacion_text, "%d/%m/%Y"
            )
            if fecha_notificacion_datetime >= fecha_desde_datetime:
                self.hay_notificacion = True
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
