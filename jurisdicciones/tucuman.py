import os
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion


class Tucuman(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, client_folder, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None,
                 razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, client_folder, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input,
                         razon_social_cliente_input, texto_notificacion, headless)
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
            headless=True
    ):
        self = await super().create(
            playwright,
            "Tucuman",
            "924 TUCUMAN",
            cliente, client_folder,
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

    async def AFIP_login(
            self,
            URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrtuc_ddjj",
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        await self.AFIP_login()
        await self.page.locator("xpath=//button[@class='close']").click()
        radio_buttons = await self.page.query_selector_all(
            'input[name="radio_cuit_sele"]'
        )
        for radio in radio_buttons:
            radio_value = await self.page.evaluate("(element) => element.value", radio)
            if radio_value == self._cuit_cliente_input:
                await radio.check()
                break
        await self.page.locator("text='Confirmar'").click()
        await self.page.click("//a[text()='Domicilio Fiscal Electrónico']")
        await self.page.locator("text='Notificaciones'").click()
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        return not await super().buscar_notificacion(
            self.page,
            texto="En este momento no hay nuevas notificaciones para mostrar.",
        )

    async def tomar_screenshot(self):
        await self.page.wait_for_load_state("networkidle")
        return await super().tomar_screenshot()

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_TUCUMAN_CLIENT")
        cuit_Tucuman = os.getenv("TEST_TUCUMAN_CUIT")
        clave_fiscal_Tucuman = os.getenv("TEST_TUCUMAN_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_TUCUMAN_CUIT_CLIENTE_INPUT")
        
        tucuman = await Tucuman.create(
            playwright,
            client,
            cuit_Tucuman,
            clave_fiscal_Tucuman,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await tucuman.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
