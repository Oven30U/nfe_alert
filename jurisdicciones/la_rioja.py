from datetime import datetime

from playwright.async_api import Playwright

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
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_load_state("networkidle")

        await frame.locator("#vUSRLOGIN").fill(f"{self._cuit}")
        await frame.locator("#vPWDLOGIN").fill(f"{self._clave_fiscal}")
        await frame.locator("input[name='BUTTON1']").click()

        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_load_state("networkidle")

        frame = self.page.frame_locator('iframe[name="gxpea000098000025"]')
        if await frame.locator('span.PopupHeaderButton#gxp0_cls').is_visible():
            await frame.locator('span.PopupHeaderButton#gxp0_cls').click()

        if await self.page.is_visible(
            "text=El CUIT ingresado No Existe o No se encuentra Activo"
        ):
            raise LoginError(
                self.cliente
            )

    async def buscar_notificacion(self):
        # frame = self.page.frames[0]
        frame = self.page.frame_locator('iframe[name="gxpea000098000025"]')
        await frame.locator("//input[@title='Domicilio Fiscal Electrónico']").wait_for(  #! TODO: Consultar si hay error de delegacion si no se ve
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
