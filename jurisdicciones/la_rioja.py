import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class LaRioja(Jurisdiccion):
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
            "LaRioja",
            "912 LA RIOJA",
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
            "https://www.dgiplarioja.gob.ar/frontend51/page?1,principal,LR-Aplicacion,O,es,0,"
        )
        frame = self.page.frame_locator('iframe[name="gxpea000098000025"]')
        await frame.locator("#vUSRLOGIN").fill(f"{self._cuit}")
        await frame.locator("#vPWDLOGIN").fill(f"{self._clave_fiscal}")
        await frame.locator("input[name='BUTTON1']").click()

        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_load_state("networkidle")

        if await self.page.is_visible(
            "text=El CUIT ingresado No Existe o No se encuentra Activo"
        ):
            raise LoginError(
                self.cliente
            )

    async def buscar_notificacion(self):
        # frame = self.page.frames[0]
        frame = self.page.frame_locator('iframe[name="gxpea000098000025"]')
        await frame.locator("//input[@title='Domicilio Fiscal Electrónico']").wait_for(
            state="visible"
        )
        await frame.locator("//input[@title='Domicilio Fiscal Electrónico']").click()

        # Obtener todas las celdas que coinciden con el XPath
        cells = await frame.locator(
            "//table[@id='GrdmensajesContainerTbl']//td[@colindex='7']"
        ).all()

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
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_LA_RIOJA_CLIENT")
        cuit_LaRioja = os.getenv("TEST_LA_RIOJA_CUIT")
        clave_fiscal_LaRioja = os.getenv("TEST_LA_RIOJA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_LA_RIOJA_CUIT_CLIENTE_INPUT")

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
