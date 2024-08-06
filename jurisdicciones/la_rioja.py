from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class LaRioja(Jurisdiccion):
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
            "LaRioja",
            "912 LA RIOJA",
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
        await self.page.goto("https://www.dgiplarioja.gob.ar/frontend51/page?1,principal,LR-Aplicacion,O,es,0,")
        frame = self.page.frame_locator("iframe[name=\"gxpea000098000025\"]")
        await frame.locator("#vUSRLOGIN").fill(f"{self._cuit}")
        await frame.locator("#vPWDLOGIN").fill(f"{self._clave_fiscal}")
        await frame.locator("input[name='BUTTON1']").click()

        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_load_state("networkidle")

        if (
                await  self.page.is_visible("text=El CUIT ingresado No Existe o No se encuentra Activo")
        ):
            raise LoginError(
                "Error de login en La Rioja, al autorizar al usuario", self.cliente
            )

    async def buscar_notificacion(self):
        # frame = self.page.frames[0]
        frame = self.page.frame_locator("iframe[name=\"gxpea000098000025\"]")
        await frame.locator("//input[@title='Domicilio Fiscal Electrónico']").wait_for(state="visible")
        await frame.locator("//input[@title='Domicilio Fiscal Electrónico']").click()

        # Obtener todas las celdas que coinciden con el XPath
        cells = await frame.locator("//table[@id='GrdmensajesContainerTbl']//td[@colindex='7']").all()

        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")

        for cell in cells:
            text = await cell.inner_text()
            try:
                cell_date = datetime.strptime(text, "%d/%m/%Y %H:%M:%S")
                if fecha_desde_dt <= cell_date <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue

        return False

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = "01082024"
        fecha_hasta = "30082024"

        cuit_LaRioja = "30677757295"
        clave_fiscal_LaRioja = "Natura2024"
        cuit_cliente_input = "30677757295"
        client = "NATURA COSMETICOS S.A"

        la_rioja = await LaRioja.create(
            playwright,
            client,
            cuit_LaRioja,
            clave_fiscal_LaRioja,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await la_rioja.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
