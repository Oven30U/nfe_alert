from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class SantiagoDelEstero(Jurisdiccion):
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
            "SantiagoDelEstero",
            "919 SAN LUIS",
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
        self.page.set_default_timeout(60000)
        # Create a new browser context with bypass_csp=True
        context = await self.browser.new_context(bypass_csp=True)
        self.page = await context.new_page()
        await self.page.goto("https://dgronline.dgrsantiago.gob.ar/dgronline/hlogin.aspx")
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@id='vUSUID']").fill(f"{self._cuit}")
        await self.page.locator("//input[@name='vUSUPWD']").fill(f"{self._clave_fiscal}")
        await self.page.locator("//input[@value='Confirmar']").click()
        await self.page.wait_for_load_state("networkidle")
        if (
                await self.page.is_visible("text=Usuario o contraseña incorrecta.")
        ):
            raise LoginError(
                "Error de login en SantiagoDelEstero, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//span[contains(text(),'Rentas Online')]")
        await self.page.locator(
            "//a[contains(text(), 'Domicilio Fiscal Electrónico')]").click()
        await self.page.wait_for_load_state("load")
        await self.page.locator(
            "//a[contains(text(), 'Ingreso Sistema Domicilio Fiscal Electrónico')]").click()
        await self.page.wait_for_load_state("load")
        await self.page.locator("//img[@id='vBOTDOMICILIOELECTRONICO']").click()
        await self.page.wait_for_load_state("load")
        new_page = await self.page.context.wait_for_event("page")
        await new_page.wait_for_load_state("load")
        if await new_page.locator("//button[@id='proceed-button']").is_visible():
            # await new_page.locator("//button[@id='proceed-button']").click()
            # await new_page.wait_for_load_state("load")
            # await new_page.evaluate("document.querySelector('#proceed-button').click()")
            await new_page.goto('https://dfe.dgrsantiago.gob.ar:8090/domicilioelectronico/faces/contribuyentes/bandejadentradacontribuyente.xhtml')
        await new_page.wait_for_load_state("load")
        await  new_page.wait_for_selector("//h3[contains(text(),'Bandeja de Entrada')]")

    async def buscar_notificacion(self):
        new_page = self.page.context.pages[-1]
        fechas_disposicion = await new_page.locator("//tbody[@id='form:tablanotificaciones_data']//tr//td[5]").all()

        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")

        for fecha in fechas_disposicion:
            text = await fecha.inner_text()
            try:
                fecha_dt = datetime.strptime(text, "%d/%m/%Y %H:%M:%S")
                if fecha_desde_dt <= fecha_dt <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue

        return False

        return not await iframe.locator(
            "//span[contains(text(),'No se han encontrado datos para mostrar')]").is_visible()

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio


    async def main():
        async with async_playwright() as playwright:
            fecha_desde = "01012020"
            fecha_hasta = "30082024"

            cuit_SantiagoDelEstero = "30714604356"
            clave_fiscal_SantiagoDelEstero = "Edge2023"
            cuit_cliente_input = "30714604356"
            client = "EDGE ARGENTINA S.R.L"

            santiago_del_estero = await SantiagoDelEstero.create(
                playwright,
                client,
                cuit_SantiagoDelEstero,
                clave_fiscal_SantiagoDelEstero,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
            )
            await santiago_del_estero.procesar_jurisdiccion()


    asyncio.run(main())
