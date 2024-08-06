from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class SanJuan(Jurisdiccion):
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
            "SanJuan",
            "918 SAN JUAN",
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
        await self.page.goto("https://rentas.dgrsj.gob.ar/sesion/LoginCUR")
        await self.page.locator("#CuitCUR").fill(f"{self._cuit}")
        await self.page.locator("#PassCUR").fill(f"{self._clave_fiscal}")
        await self.page.locator("#btnFormValidarCur").click()
        if (
                await  self.page.is_visible("text=El N° de CUIT no es válido")
        ):
            raise LoginError(
                "Error de login en San Juan, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.goto("https://rentas.dgrsj.gob.ar/Notificaciones/getListadoDeNotificaciones")
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        await self.page.locator("//table[@id='dtDetalleDeNotificaciones']").wait_for(state="visible")
        cells = await self.page.locator("//table[@id='dtDetalleDeNotificaciones']//tbody//tr/td[4]").all()
        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")
        for cell in cells:
            text = await cell.inner_text()
            try:
                cell_date = datetime.strptime(text, "%d/%m/%Y %H:%M")
                if fecha_desde_dt <= cell_date <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue
        return False

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

            cuit_SanJuan = "30677757295"
            clave_fiscal_SanJuan = "GJdd0x"
            cuit_cliente_input = "30677757295"
            client = "NATURA COSMETICOS S.A"

            san_juan = await SanJuan.create(
                playwright,
                client,
                cuit_SanJuan,
                clave_fiscal_SanJuan,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
            )
            await san_juan.procesar_jurisdiccion()


    asyncio.run(main())
