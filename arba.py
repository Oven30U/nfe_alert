import asyncio
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion, LoginError


class Arba(Jurisdiccion):
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
            "ARBA",
            "902 BUENOS AIRES",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def consultar_notificaciones(self):
        await self.page.goto("https://www.arba.gov.ar/Gestionar/PanelAutogestion.asp")
        await self.page.fill("#CUIT", f"{self._cuit}")
        await self.page.fill("#clave_Cuit", f"{self._clave_fiscal}")
        # await asyncio.sleep(2)
        await self.page.press("#clave_Cuit", "Enter")
        if (
            await self.page.is_visible(
                "text=Ocurrio un error inesperado al autorizar al usuario"
            )
            or await self.page.is_visible(
                "text=El usuario ingresado y/o la contraseña no son válidos."
            )
            or await self.page.is_visible("text=Servicio ocupado")
        ):
            raise LoginError(
                "Error de login en ARBA, al autorizar al usuario", self.cliente
            )
        await self.page.click("xpath=//span[contains(text(), 'DFE')]")
        await self.page.wait_for_load_state("domcontentloaded")
        if await self.page.is_visible("text=Seleccione un rol", timeout=5000):
            await self.page.select_option(
                "select[name='rol']", "ContribuyentesGral/Contribuyente"
            )
            await self.page.click("xpath=//button[@type='submit']")
        await self.page.click("xpath=//td[@id='tdFiltroLeidaNO']/a")
        await self.page.click('a[href="#tabs-Todas"]')

    async def buscar_notificacion(self):
        return not await super().buscar_notificacion(
            self.page, "No se encontraron resultados"
        )

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = "01052024"
        fecha_hasta = "30052024"

        cuit_Arba = "30712132554"
        clave_fiscal_Arba = "Facebook1819"
        cuit_cliente_input = "30712132554"
        client = "FACEBOOK ARGENTINA S.R.L"

        # client = "EDGE ARGENTINA S.R.L"
        # cuit_Arba = "30714604356"
        # clave_fiscal_Arba = "Edge2018"
        # cuit_cliente_input = "30714604356"
        arba = await Arba.create(
            playwright,
            client,
            cuit_Arba,
            clave_fiscal_Arba,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await arba.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
