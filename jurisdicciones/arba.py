from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Arba(Jurisdiccion):
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
            "Arba",
            "902 BUENOS AIRES",
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
        self.page.set_default_timeout(90000)
        await self.page.goto("https://www.arba.gov.ar/Gestionar/PanelAutogestion.asp")
        await self.page.wait_for_load_state("load")
        await self.page.fill("#CUIT", f"{self._cuit}")
        await self.page.fill("#clave_Cuit", f"{self._clave_fiscal}")
        await self.page.locator("//button[@value='Ingresar']").click()
        # await self.page.press("#clave_Cuit", "Enter")
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
        await self.page.wait_for_load_state("load")
        await self.page.click("xpath=//span[contains(text(), 'DFE')]")
        await self.page.wait_for_load_state("load")
        if await self.page.is_visible("text=Seleccione un rol", timeout=60000):
            await self.page.select_option(
                "select[name='rol']", "ContribuyentesGral/Contribuyente"
            )
            # await self.page.click("xpath=//button[@type='submit']")
            await self.page.click("//button[contains(text(),'Continuar')]")
            await self.page.wait_for_load_state("load")
        await self.page.click("xpath=//td[@id='tdFiltroLeidaNO']/a")
        await self.page.click('a[href="#tabs-Todas"]')

    async def buscar_notificacion(self):
        # Verificar si el texto "No se encontraron resultados" es visible
        return not await self.buscar_notificacion_xpath_visible(
            "//table[@id='listaNotificacionesTCTodas']//tbody/tr//*[contains(text(), 'No se encontraron resultados')]",
            self.page)

    async def tomar_screenshot(self):
        await self.page.wait_for_load_state("load")
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = "01072024"
        fecha_hasta = "30072024"

        # cuit_Arba = "30712132554"
        # clave_fiscal_Arba = "Facebook1819"
        # cuit_cliente_input = "30712132554"
        # client = "FACEBOOK ARGENTINA S.R.L"

        client = "EDGE ARGENTINA S.R.L"
        cuit_Arba = "30714604356"
        clave_fiscal_Arba = "Edge2018"
        cuit_cliente_input = "30714604356"

        # client = "ABBOTT LABORATORIES ARG. S.A"
        # cuit_Arba = "30500846301"
        # clave_fiscal_Arba = "Abbott2018"
        # cuit_cliente_input = "30500846301"

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
