from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion, LoginError


class Tucuman(Jurisdiccion):
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
            "Neuquén",
            "NEU",
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
        await self.page.locator("text='Domicilio Fiscal Electrónico'").click()
        await self.page.locator("text='Notificaciones'").click()

    async def buscar_notificacion(self):
        return not await super().buscar_notificacion(
            self.page,
            texto="En este momento no hay nuevas notificaciones para mostrar.",
        )

    async def tomar_screenshot(self):
        return await super().tomar_screenshot()

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Tucuman = "20386165476"
        clave_fiscal_Tucuman = "Gabriel1994"
        cuit_cliente_input = "30714604356"
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
