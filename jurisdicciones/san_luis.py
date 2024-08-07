from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError
from datetime import datetime


class SanLuis(Jurisdiccion):
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
            "SanLuis",
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
        await self.page.goto("https://sistematributario.dpip.sanluis.gov.ar/ords/clavefiscal/r/miclave/login")
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@id='P101_USERNAME']").fill(f"{self._cuit}")
        await self.page.locator("//input[@name='P101_PASSWORD']").fill(f"{self._clave_fiscal}")
        await self.page.locator("button:has(span:text('Conectar'))").first.click()
        await self.page.wait_for_load_state("networkidle")
        if (
                await self.page.is_visible("text=Credenciales de conexión no válidas")
        ):
            raise LoginError(
                "Error de login en SanLuis, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator(
            f"//td[b[contains(text(), '{self._cuit_cliente_input}')]]/following-sibling::td//button").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//a[div[h3[contains(text(), 'Buzón Electrónico')]]]")
        await self.page.locator("//a[div[h3[contains(text(), 'Buzón Electrónico')]]]").click()
        await self.page.wait_for_load_state("load")
        iframe = self.page.frame_locator(
            "iframe[src*='/ords/clavefiscal/r/miclave/notificaciones-domicilio-electr%C3%B3nico1']")
        await self.page.wait_for_load_state("load")
        await  iframe.locator("//input[@id='P11_FECHA_DESDE']").fill(f"{self.fecha_desde}")
        await  iframe.locator("//input[@id='P11_FECHA_HASTA']").fill(f"{self.fecha_hasta}")
        await iframe.locator("select#P11_ESTADO").select_option("ENVIADA")
        await  iframe.locator("//div//button[span[contains(text(), 'Buscar')]]").click()
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        iframe = self.page.frame_locator(
            "iframe[src*='/ords/clavefiscal/r/miclave/notificaciones-domicilio-electr%C3%B3nico1']")
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

            cuit_SanLuis = "20104314075"
            clave_fiscal_SanLuis = "Edge2021"
            cuit_cliente_input = "30714604356"
            client = "EDGE ARGENTINA S.R.L"

            san_luis = await SanLuis.create(
                playwright,
                client,
                cuit_SanLuis,
                clave_fiscal_SanLuis,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
            )
            await san_luis.procesar_jurisdiccion()


    asyncio.run(main())
