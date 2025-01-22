import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class SantiagoDelEstero(Jurisdiccion):
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
            "SantiagoDelEstero",
            "922 SANTIAGO DEL ESTERO",
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

    async def consultar_notificaciones(self):
        await self.page.goto(
            "https://dfe.dgrsantiago.gob.ar:8090/domicilioelectronico/faces/contribuyentes/bandejadentradacontribuyente.xhtml",
            timeout = 900000
        )
        
        # Desde la página de login princial: 
        # await self.page.goto(
        #     "https://dgronline.dgrsantiago.gob.ar/dgronline/hlogin.aspx"
        # )
        # await self.page.locator("//input[@id='vUSUID']").fill(f"{self._cuit}")
        # await self.page.locator("//input[@id='vUSUPWD']").fill(f"{self._clave_fiscal}")
        # await self.page.locator("//input[@value='Confirmar']").click()
        # await self.page.wait_for_load_state("load", timeout=90000)
        # await self.page.locator(
        #     "(//a[contains(text(),'Domicilio Fiscal Electrónico')])[1]"
        # ).click()
        # await self.page.wait_for_load_state("load", timeout=90000)
        # await self.page.locator(
        #     "(//a[contains(text(),'Domicilio Fiscal Electrónico')])[2]"
        # ).click()
        # await self.page.locator("#vBOTDOMICILIOELECTRONICO").click()
        

        # self.page.set_default_timeout(60000)
        # Create a new browser context with bypass_csp=True
        # context = await self.browser.new_context(bypass_csp=True)
        # self.page = await context.new_page()
        # await self.page.goto("https://dgronline.dgrsantiago.gob.ar/dgronline/hlogin.aspx")
        
        await self.page.locator("//input[@id='loginForm:username']").fill(
            f"{self._cuit}"
        )
        await self.page.locator("//input[@name='loginForm:password']").fill(
            f"{self._clave_fiscal}"
        )
        await self.page.locator("//button[@id='loginForm:loginButton']").click()
        await self.page.wait_for_load_state("load")
        if await self.page.is_visible("text=Usuario y Contraseña Incorrectos!"):
            raise LoginError(
                "Error de login en SantiagoDelEstero, al autorizar al usuario",
                self.cliente,
            )
        await self.page.wait_for_selector("//h3[contains(text(),'Bandeja de Entrada')]")
        await self.page.wait_for_load_state("load")

    async def buscar_notificacion(self):
        fechas_disposicion = await self.page.locator(
            "//tbody[@id='form:tablanotificaciones_data']//tr//td[5]"
        ).all()

        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")

        for fecha in fechas_disposicion:
            text = await fecha.inner_text()
            try:
                fecha_dt = datetime.strptime(text, "%d/%m/%Y")
                if fecha_desde_dt <= fecha_dt <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue

        return False

        # return not await self.page.locator("//span[contains(text(),'No se han encontrado datos para mostrar')]").is_visible()

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    async def main():
        async with async_playwright() as playwright:
            fecha_desde = os.getenv("FECHA_DESDE")
            fecha_hasta = os.getenv("FECHA_HASTA")

            client = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CLIENT")
            cuit_SantiagoDelEstero = os.getenv("TEST_SANTIAGO_DEL_ESTERO_CUIT")
            clave_fiscal_SantiagoDelEstero = os.getenv(
                "TEST_SANTIAGO_DEL_ESTERO_CLAVE_FISCAL"
            )
            cuit_cliente_input = os.getenv(
                "TEST_SANTIAGO_DEL_ESTERO_CUIT_CLIENTE_INPUT"
            )

            santiago_del_estero = await SantiagoDelEstero.create(
                playwright,
                client,
                cuit_SantiagoDelEstero,
                clave_fiscal_SantiagoDelEstero,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await santiago_del_estero.procesar_jurisdiccion()

    asyncio.run(main())
