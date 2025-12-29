import os
from playwright.async_api import Playwright, async_playwright
from datetime import datetime

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class LaPampa(Jurisdiccion):
    def __init__(
        self,
        nombre,
        codigo,
        cliente,
        client_folder,
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
            client_folder,
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
        client_folder,
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
            client_folder,
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
            "https://dgr.lapampa.gob.ar/ServiciosEnLinea/?programa=MenuCuenta"
        )

        await self.page.wait_for_load_state("networkidle")

        await self.page.locator('a#gestionar').click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator('a#aContribuyentes').click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator('iframe[name="iframe1"]').content_frame.locator('button#Btn2').click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator('iframe[name="iframe1"]').content_frame.locator('li.list-group-item').filter(has_text="Consulta de Novedades / Trámites").click()
        await self.page.wait_for_load_state("networkidle")

        iframe = self.page.frame(name="iframe1")
        await iframe.fill("input#cuit", f"{self._cuit}")
        await iframe.fill("input#pPassword", f"{self._clave_fiscal}")
        await iframe.click("//input[@name='AceptarLogin']")
        await self.page.wait_for_load_state("domcontentloaded")

        if await iframe.is_visible("text=PASSWORD INCORRECTO"):
            raise LoginError(self.cliente)

        cuit_clic = self._cuit_cliente_input[:2] + "-" + self._cuit_cliente_input[2:]
        await iframe.click(
            f"//form[@id='FrmSeleccionEmpresa']//td[contains(text(),'{cuit_clic}')]/following-sibling::td[2]/input[@type='radio']"
        )
        await iframe.click("input#vConfirmar")
        await self.page.wait_for_load_state("networkidle")
        await iframe.locator('div#lblBandeja').wait_for(state='visible')
        # await iframe.click("//h1[contains(text(), 'Consulta de Novedades/Trámites')]")
            

    async def buscar_notificacion(self):
        iframe = self.page.frame(name="iframe1")

        fecha_desde_formated = (
            datetime.strptime(self.fecha_desde, "%d%m%Y")
            if isinstance(self.fecha_desde, str)
            else self.fecha_desde
        )

        fecha_hasta_formated = (
            datetime.strptime(self.fecha_hasta, "%d%m%Y")
            if isinstance(self.fecha_hasta, str)
            else self.fecha_hasta
        )

        rows = await iframe.query_selector_all("//table//tr")

        for row in rows:
            if await row.query_selector("th"):
                continue

            date_cell = await row.query_selector("xpath=./td[5]")
            status_cell = await row.query_selector("xpath=./td[6]")

            if date_cell and status_cell:
                date_text = await date_cell.inner_text()
                status_text = await status_cell.inner_text()

                try:
                    notification_date = datetime.strptime(date_text.strip(), "%d/%m/%Y")

                    if (
                        fecha_desde_formated
                        <= notification_date
                        <= fecha_hasta_formated
                        and "LEIDO" not in status_text
                    ):
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
