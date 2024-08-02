import asyncio
from datetime import datetime
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion


class RioNegro(Jurisdiccion):
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
            "RioNegro",
            "916 RIO NEGRO",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        return self

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrrn_sitio_seguro",
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        await self.AFIP_login()
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_selector('xpath=//select[@id="cuit_opera"]')
        await self.page.select_option(
            'xpath=//select[@id="cuit_opera"]', str(self._cuit_cliente_input)
        )
        await self.page.click("#btn_ingresar")

    async def buscar_notificacion(self):
        cantidad_mensajes = await self.page.locator("#cantidad_msj").inner_text()
        cantidad_notificaciones_electronicas = await self.page.locator(
            "#cantidad_notif"
        ).inner_text()
        total_notificaciones = int(cantidad_mensajes) + int(
            cantidad_notificaciones_electronicas
        )
        self.hay_notificacion = total_notificaciones > 0
        return self.hay_notificacion

    async def tomar_screenshot(self):
        await self.page.wait_for_load_state("networkidle")
        await self.page.click("button#btn_e-ventanilla")
        secciones = [
            ("notificaciones", 'a#tab_notif'),
            ("mensajes", 'a#tab_msj'),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_RioNegro = "20386165476"
        clave_fiscal_RioNegro = "Gabriel1994"
        cuit_cliente_input = "30714604356"
        rio_negro = await RioNegro.create(
            playwright,
            client,
            cuit_RioNegro,
            clave_fiscal_RioNegro,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await rio_negro.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
