import asyncio
from datetime import datetime

from playwright.async_api import Playwright, Page

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class SantiagoDelEstero(Jurisdiccion):
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
            "SantiagoDelEstero",
            "922 SANTIAGO DEL ESTERO",
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
        self.playwright = playwright  # Store the playwright instance
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def consultar_notificaciones(self):
        await self.page.goto(
            "https://dgronline.dgrsantiago.gob.ar/dgronline/hlogin.aspx"
        )
        await self.page.locator("//input[@id='vUSUID']").fill(f"{self._cuit}")
        await self.page.locator("//input[@id='vUSUPWD']").fill(f"{self._clave_fiscal}")
        await self.page.locator("//input[@value='Confirmar']").click()
        await self.page.wait_for_load_state("load", timeout=10000)
        await self.page.wait_for_selector( #! TODO: Consultar si hay error de delegacion si no se ve
            "(//a[contains(text(),'Domicilio Fiscal Electrónico')])[1]", timeout=10000
        )
        await self.page.locator(
            "(//a[contains(text(),'Domicilio Fiscal Electrónico')])[1]"
        ).click()
        await self.page.wait_for_load_state("load", timeout=10000)
        await self.page.wait_for_selector(
            "(//a[contains(text(),'Ingreso Sistema Domicilio Fiscal Electrónico')])",
            timeout=10000,
        )
        await self.page.locator(
            "(//a[contains(text(),'Ingreso Sistema Domicilio Fiscal Electrónico')])"
        ).click()

        # Hacer clic en el botón que abre la nueva pestaña (pop-up)
        await self.page.locator("#vBOTDOMICILIOELECTRONICO").click()
        self.logger.debug("Clic en botón realizado, esperando nuevo pop-up...")

        try:
            new_page: Page = await asyncio.wait_for(
                self.page.wait_for_event("popup"), timeout=5000
            )
            self.logger.debug("Popup detectado!")
            await new_page.wait_for_load_state("networkidle")
        except asyncio.TimeoutError:
            self.logger.debug(
                "No se detectó el pop-up, revisa la configuración del navegador."
            )
        else:
            await new_page.wait_for_load_state("load")
            await new_page.wait_for_load_state("networkidle")
            self.page = new_page
            proceed_btn = self.page.locator("#proceed-button")
            if await proceed_btn.is_visible():
                await proceed_btn.click()
            await self.page.wait_for_selector(
                "//h3[normalize-space(.) = 'Bandeja de Entrada']", timeout=60000
            ) # !!! TODO : Modificar en el servidor

    async def buscar_notificacion(self):
        fechas_disposicion = await self.page.locator(
            "//tbody[@id='form:tablanotificaciones_data']//tr//td[5]"
        ).all()

        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")

        for fecha in fechas_disposicion:
            text = await fecha.inner_text()
            try:
                fecha_dt = datetime.strptime(text, "%d/%m/%Y")
                if fecha_desde_dt <= fecha_dt <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue

        return False

    async def tomar_screenshot(self, nombre_extra: str = None) -> str:
        """
        Toma una captura de pantalla de la página actual.

        Args:
            nombre_extra: Texto adicional para incluir en el nombre del archivo de la captura.

        Returns:
            str: Ruta del archivo de la captura guardada.
        """
        return await super().tomar_screenshot(self.page, nombre_extra)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
