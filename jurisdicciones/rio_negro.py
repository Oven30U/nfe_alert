import os
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion


class RioNegro(Jurisdiccion):
    def __init__(
        self,
        nombre,
        codigo,
        cliente, client_folder,
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
            cliente, client_folder,
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
        cliente, client_folder,
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
            "RioNegro",
            "916 RIO NEGRO",
            cliente, client_folder,
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
        await self.page.wait_for_load_state("networkidle")
        popup_aceptar_button = self.page.get_by_text("ACEPTAR")
        if await popup_aceptar_button.is_visible():
            await popup_aceptar_button.click()
        

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
            ("notificaciones", "a#tab_notif"),
            ("mensajes", "a#tab_msj"),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")
        client = os.getenv("TEST_RIO_NEGRO_CLIENT")
        cuit_RioNegro = os.getenv("TEST_RIO_NEGRO_CUIT")
        clave_fiscal_RioNegro = os.getenv("TEST_RIO_NEGRO_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_RIO_NEGRO_CUIT_CLIENTE_INPUT")

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
