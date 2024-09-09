from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class SantiagoDelEstero(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None,
                 razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input,
                         razon_social_cliente_input, texto_notificacion, headless)
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
            "SantiagoDelEstero",
            "922 SANTIAGO DEL ESTERO",
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
            'https://dfe.dgrsantiago.gob.ar:8090/domicilioelectronico/faces/contribuyentes/bandejadentradacontribuyente.xhtml')
        await self.page.wait_for_load_state("load")

        # self.page.set_default_timeout(60000)
        # Create a new browser context with bypass_csp=True
        # context = await self.browser.new_context(bypass_csp=True)
        # self.page = await context.new_page()
        # await self.page.goto("https://dgronline.dgrsantiago.gob.ar/dgronline/hlogin.aspx")
        await self.page.locator("//input[@id='loginForm:username']").fill(f"{self._cuit}")
        await self.page.locator("//input[@name='loginForm:password']").fill(f"{self._clave_fiscal}")
        await self.page.locator("//button[@id='loginForm:loginButton']").click()
        await self.page.wait_for_load_state("load")
        if (
                await self.page.is_visible("text=Usuario y Contraseña Incorrectos!")
        ):
            raise LoginError(
                "Error de login en SantiagoDelEstero, al autorizar al usuario", self.cliente
            )
        await  self.page.wait_for_selector("//h3[contains(text(),'Bandeja de Entrada')]")
        await self.page.wait_for_load_state("load")

    async def buscar_notificacion(self):
        fechas_disposicion = await self.page.locator("//tbody[@id='form:tablanotificaciones_data']//tr//td[5]").all()

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
            fecha_desde = "01082024"
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
                headless=False
            )
            await santiago_del_estero.procesar_jurisdiccion()


    asyncio.run(main())
