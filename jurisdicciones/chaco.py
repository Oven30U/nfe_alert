from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
# from datetime import datetime


class Chaco(Jurisdiccion):
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
            "Chaco",
            "906 CHACO",
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
        await self.page.goto("https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/iniciocontribuyente")
        await self.page.locator("#vCONCUIT").fill(f"{self._cuit}")
        await self.page.locator("#vCONTRASENA").fill(f"{self._clave_fiscal}")
        await self.page.locator("//input[@name='BUTTON1']").click()
        if (
                await  self.page.is_visible("text=Contribuyente no habilitado")
        ):
            raise LoginError(
                "Error de login en Chaco, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@name='BTNACEPTAR']").click()
        await  self.page.locator("//a[contains(text(), 'Mi Ventanilla')]").click()
        await  self.page.locator("//a[contains(text(), 'Avisos')]").click()
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        await self.page.is_visible("text=Avisos - Mi Ventanilla Electrónica")
        filas = await self.page.locator("//table[@id='Grid1ContainerTbl']//tbody//tr").all()
        return True if filas else False
        # fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        # fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")
        # for cell in cells:
        #     text = await cell.inner_text()
        #     try:
        #         cell_date = datetime.strptime(text, "%d/%m/%Y %H:%M")
        #         if fecha_desde_dt <= cell_date <= fecha_hasta_dt:
        #             return True
        #     except ValueError:
        #         continue
        # return False

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

            cuit_Chaco = "30714604356"
            clave_fiscal_Chaco = "Edge2021"
            cuit_cliente_input = "30714604356"
            client = "EDGE ARGENTINA S.R.L"

            chaco = await Chaco.create(
                playwright,
                client,
                cuit_Chaco,
                clave_fiscal_Chaco,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
            )
            await chaco.procesar_jurisdiccion()


    asyncio.run(main())
