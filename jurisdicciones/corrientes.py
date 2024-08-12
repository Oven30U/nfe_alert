from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class Corrientes(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None,
                 razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input,
                         razon_social_cliente_input, texto_notificacion, headless)
        self.cuit_cliente_input = str(cuit_cliente_input)
        # self.headless = headless

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
            "Corrientes",
            "905 CORRIENTES",
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
        self.headless = headless
        return self

    async def consultar_notificaciones(self):
        await self.page.goto("https://miportal.dgrcorrientes.gov.ar/")
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@id='username']").fill(f"{self._cuit}")
        await self.page.locator("//input[@id='loginPassword']").fill(f"{self._clave_fiscal}")
        await self.page.locator("//button[@id='ingresar']").click()
        await self.page.wait_for_load_state("networkidle")
        if (
                await self.page.is_visible("text=Los datos ingresados no son correctos.")
        ):
            raise LoginError(
                "Error de login en Corrientes, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//h3[contains(text(),'Domicilio')]")
        await self.page.goto("https://miportal.dgrcorrientes.gov.ar/bandejadfe#")
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        filas = await self.page.locator("//div[@class='listCuerpo']//p[3]").all()
        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")
        for fila in filas:
            text = await fila.inner_text()
            try:
                cell_date = datetime.strptime(text, "%d/%m/%Y")
                if fecha_desde_dt <= cell_date <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue
        return False

    async def tomar_screenshot(self):
        if not self.headless:
            await super().maximizar_ventana()
        # if not self.headless:
        #     # Maximizar la ventana del navegador usando la API de DevTools
        #     client = await self.page.context.new_cdp_session(self.page)
        #     window_info = await client.send('Browser.getWindowForTarget')
        #     window_id = window_info['windowId']
        #
        #     # Restaurar a estado normal si está minimizado o en pantalla completa
        #     await client.send('Browser.setWindowBounds', {
        #         'windowId': window_id,
        #         'bounds': {'windowState': 'normal'}
        #     })
        #
        #     # Maximizar la ventana
        #     await client.send('Browser.setWindowBounds', {
        #         'windowId': window_id,
        #         'bounds': {'windowState': 'maximized'}
        #     })
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio


    async def main():
        async with async_playwright() as playwright:
            fecha_desde = "01082024"
            fecha_hasta = "30082024"

            cuit_Corrientes = "30677757295"
            clave_fiscal_Corrientes = "natura18"
            cuit_cliente_input = "30677757295"
            client = "NATURA COSMETICOS S.A"

            corrientes = await Corrientes.create(
                playwright,
                client,
                cuit_Corrientes,
                clave_fiscal_Corrientes,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False
            )
            await corrientes.procesar_jurisdiccion()


    asyncio.run(main())
