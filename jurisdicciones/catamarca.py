from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class Catamarca(Jurisdiccion):
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
            "Catamarca",
            "903 CATAMARCA",
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
        await self.page.goto("https://dgrentas.arca.gob.ar/rentascuA/principal.aspx")
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@value='Acceder']").click()
        await self.page.locator("//input[@id='F1:username']").fill(f"{self._cuit}")
        await self.page.locator("//input[@id='F1:btnSiguiente']").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@id='F1:password']").fill(f"{self._clave_fiscal}")
        await self.page.locator("//input[@id='F1:btnIngresar']").click()
        await self.page.wait_for_load_state("networkidle")
        if (
                await self.page.is_visible("text=Clave o usuario incorrecto")
        ):
            raise LoginError(
                "Error de login en Catamarca, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//select[@id='vPERSONAID']")
        options = await self.page.locator("//select[@id='vPERSONAID']//option").all()
        for option in options:
            label = await option.inner_text()
            if self._cuit_cliente_input in label:
                value = await option.get_attribute("value")
                await self.page.select_option("select#vPERSONAID", value=value)
                break
        await self.page.locator("//input[@value='Ingresar']").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//a/span[contains(text(), 'Dom Fiscal')]")
        await self.page.locator("//a/span[contains(text(), 'Dom Fiscal')]").click()
        await self.page.locator("//a[contains(text(), 'Domicilio')]").click()
        # https://dgrentas.arca.gob.ar/rentascuA/DomicilioElectronico.aspx
        # Esperar a que se abra una nueva pestaña
        self.page = await self.context.wait_for_event("page")
        # Cambiar el contexto a la nueva pestaña
        await self.page.bring_to_front()
        await self.page.wait_for_load_state("networkidle")
        # 'No se encontraron novedades'
        # 'Ud. no tiene Notificaciones'

    async def buscar_notificacion(self):
        return False if await self.page.is_visible(
            'text=No se encontraron novedades') and await self.page.is_visible(
            'text=Ud. no tiene Notificaciones') else False

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

            cuit_Catamarca = "20408964823"
            clave_fiscal_Catamarca = "Elcolo_1998&"
            cuit_cliente_input = "30714604356"
            client = "EDGE ARGENTINA S.R.L"

            catamarca = await Catamarca.create(
                playwright,
                client,
                cuit_Catamarca,
                clave_fiscal_Catamarca,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await catamarca.procesar_jurisdiccion()


    asyncio.run(main())
