import os
from datetime import datetime
import asyncio
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Arba(Jurisdiccion):
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
            "Arba",
            "902 BUENOS AIRES",
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

    async def consultar_notificaciones(self):
        self.page.set_default_timeout(90000)
        await self.page.goto("https://www.arba.gov.ar/Gestionar/PanelAutogestion.asp")
        await self.page.wait_for_load_state("load")
        await self.page.fill("#CUIT", f"{self._cuit}")
        await self.page.fill("#clave_Cuit", f"{self._clave_fiscal}")
        await self.page.locator("//button[@value='Ingresar']").click()
        # await self.page.press("#clave_Cuit", "Enter")
        if (
            await self.page.is_visible(
                "text=Ocurrio un error inesperado al autorizar al usuario"
            )
            or await self.page.is_visible(
                "text=El usuario ingresado y/o la contraseña no son válidos."
            )
            or await self.page.is_visible("text=Servicio ocupado")
        ):
            raise LoginError(
                "Error de login en ARBA, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("load")
        await self.page.click("xpath=//span[contains(text(), 'DFE')]")
        await self.page.wait_for_load_state("load")
        if await self.page.is_visible("text=Seleccione un rol", timeout=60000):
            await self.page.select_option(
                "select[name='rol']", "ContribuyentesGral/Contribuyente"
            )
            # await self.page.click("xpath=//button[@type='submit']")
            await self.page.click("//button[contains(text(),'Continuar')]")
            await self.page.wait_for_load_state("load")
        await self.page.click("xpath=//td[@id='tdFiltroLeidaNO']/a")
        await self.page.click('a[href="#tabs-Todas"]')

    async def buscar_notificacion(self):
        no_results = await self.buscar_notificacion_xpath_visible(
            "//table[@id='listaNotificacionesTCTodas']//tbody/tr//*[contains(text(), 'No se encontraron resultados')]",
            self.page
        )
        if no_results:
            return False

        date_elements = await self.page.query_selector_all("//table[@id='listaNotificacionesTCTodas']//tbody/tr/td[3]")
        
        if not date_elements:
            return False
            
        fecha_desde = datetime.strptime(self.fecha_desde, '%d%m%Y')
        fecha_hasta = datetime.strptime(self.fecha_hasta, '%d%m%Y')
        
        for date_element in date_elements:
            date_text = await date_element.text_content()
            try:
                notification_date = datetime.strptime(date_text.strip(), '%d-%m-%Y')
                if fecha_desde <= notification_date <= fecha_hasta:
                    return True
            except ValueError:
                continue
                
        return False

    async def tomar_screenshot(self):
        await self.page.wait_for_load_state("load")
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_ARBA_CLIENT")
        cuit_Arba = os.getenv("TEST_ARBA_CUIT")
        clave_fiscal_Arba = os.getenv("TEST_ARBA_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_ARBA_CUIT_CLIENTE_INPUT")

        arba = await Arba.create(
            playwright,
            client,
            cuit_Arba,
            clave_fiscal_Arba,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await arba.procesar_jurisdiccion()


if __name__ == "__main__":
    asyncio.run(main())
