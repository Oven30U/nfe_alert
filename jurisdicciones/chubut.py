from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class Chubut(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None, razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input, razon_social_cliente_input, texto_notificacion, headless)
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
            "Chubut",
            "907 CHUBUT",
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
        await self.page.goto(
            "https://servicios.dgrchubut.gov.ar/modulos/login_siat.php?back_url=%2Fmodulos%2Fedom_contrib.php"
        )
        await self.page.wait_for_load_state("load")
        await self.page.fill("xpath=//input[@name='log_user']", self._cuit)
        await self.page.fill("xpath=//input[@name='log_pass']", self._clave_fiscal)
        await self.page.click("xpath=//input[@class='entrar']")
        await self.page.wait_for_load_state("load")
        incorrect_login = self.page.locator(
            'xpath=//div[text()="Usuario/clave incorrectos"]'
        )
        if await incorrect_login.count() > 0:
            raise LoginError("Login CUIT incorrecto", self.cliente)

    async def buscar_notificacion(self):
        fechas_envio_comunicaciones = await self.page.locator(
            "//table[@id='actos_grid']//tr[@tabindex='-1']//td[3]").all()
        fechas_envio_fiscalizaciones = await self.page.locator(
            "//table[@id='actos_grid_fisca']//tr[@tabindex='-1']//td[3]").all()

        fechas_envio = fechas_envio_comunicaciones + fechas_envio_fiscalizaciones

        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")

        for fecha in fechas_envio:
            text = await fecha.inner_text()
            try:
                fecha_dt = datetime.strptime(text, "%d/%m/%Y")
                if fecha_desde_dt <= fecha_dt <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue

        return False

    async def tomar_screenshot(self):
        """Tomar dos screenshot's en la jurisdicción de Chubut."""
        secciones = [
            ("comunicaciones", "a#ui-id-1"),
            ("fiscalización_electrónica", "a#ui-id-2"),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio


    async def main():
        async with async_playwright() as playwright:
            fecha_desde = "01052024"
            fecha_hasta = "30052024"

            # cuit_Chubut = "30714604356"
            # client = "EDGE ARGENTINA S.R.L"
            # clave_fiscal_Chubut = "Edge2023"
            # cuit_cliente_input = "30714604356"

            cuit_Chubut = "30677757295"
            client = "NATURA COSMETICOS S.A"
            clave_fiscal_Chubut = "natura00"
            cuit_cliente_input = "30677757295"

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


    asyncio.run(main())
