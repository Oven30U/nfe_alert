import os
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class LaPampa(Jurisdiccion):
    def __init__(
        self,
        nombre,
        codigo,
        cliente,
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
            cliente,
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
        cliente,
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
            "LaPampa",
            "911 LA PAMPA",
            cliente,
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

    # Existing methods...

    async def consultar_notificaciones(self):
        await self.page.goto(
            "https://dgr.lapampa.gob.ar/ServiciosEnLinea/?programa=MenuCuenta"
        )
        iframe = self.page.frame(name="iframe1")
        await iframe.fill("input#cuit", f"{self._cuit}")
        await iframe.fill("input#pPassword", f"{self._clave_fiscal}")
        await iframe.click("//input[@name='AceptarLogin']")
        await self.page.wait_for_load_state("domcontentloaded")

        if await iframe.is_visible("text=PASSWORD INCORRECTO"):
            raise LoginError(
                "Error de login en La Pampa, al autorizar al usuario", self.cliente
            )

        cuit_clic = self._cuit_cliente_input[:2] + "-" + self._cuit_cliente_input[2:]
        await iframe.click(
            f"//form[@id='FrmSeleccionEmpresa']//td[contains(text(),'{cuit_clic}')]/following-sibling::td[2]/input[@type='radio']"
        )
        await iframe.click("input#vConfirmar")
        await iframe.click("//li[contains(text(), 'Consulta de Novedades/Trámites')]")
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        iframe = self.page.frame(name="iframe1")
        # Obtener todas las celdas que coinciden con el XPath
        cells = await iframe.query_selector_all("//table//tr//td[position() mod 6 = 0]")

        # Iterar a través de las celdas y verificar si alguna contiene el texto "LEIDO"
        for cell in cells:
            text = await cell.inner_text()
            if "LEIDO" not in text:
                return True

        return False

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_LA_PAMPA_CLIENT")
        cuit_LaPampa = os.getenv("TEST_LA_PAMPA_CUIT")
        clave_fiscal_LaPampa = os.getenv("TEST_LA_PAMPA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_LA_PAMPA_CUIT_CLIENTE_INPUT")

        la_pampa = await LaPampa.create(
            playwright,
            client,
            cuit_LaPampa,
            clave_fiscal_LaPampa,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await la_pampa.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
