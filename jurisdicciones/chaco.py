from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError

# from datetime import datetime

async def wait_for_selector_with_retry(page, selector, retries=3, timeout=30000):
    for attempt in range(retries):
        if await page.wait_for_selector(selector, timeout=timeout):
            return
        else:
            if attempt < retries - 1:
                continue
            else:
                raise


class Chaco(Jurisdiccion):
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
            headless=False,
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
            headless
        )

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
            headless=False,
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
            razon_social_cliente_input,
            texto_notificacion,
            headless=headless,
        )
        return self

    async def consultar_notificaciones(self):
        await self.page.goto("https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/iniciocontribuyente",
                             wait_until="networkidle")
        # # Minimizar la ventana del navegador usando la API de DevTools
        # client = await self.page.context.new_cdp_session(self.page)
        # window_info = await client.send('Browser.getWindowForTarget')
        # window_id = window_info['windowId']
        # await client.send('Browser.setWindowBounds', {
        #     'windowId': window_id,
        #     'bounds': {'windowState': 'minimized'}
        # })

        # await self.page.evaluate("window.moveTo(0, 0); window.resizeTo(0, 0);")
        # await self.page.add_style_tag(
        # content="*, *::before, *::after { transition: none !important; animation: none !important; }")
        # await self.context.newPage({'viewport': {'width': 1280, 'height': 800}})
        await self.page.goto("https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/iniciocontribuyente",
                             wait_until="networkidle")
        # await self.page.wait_for_selector("#vCONCUIT")
        # await wait_for_selector_with_retry(self.page, "#vCONCUIT")
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
        await self.page.wait_for_load_state("load")
        await self.page.locator("//input[@name='BTNACEPTAR']").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_load_state("load")
        # max_retry = 3
        # retry = 0
        # while not await self.page.is_visible("//a[contains(text(), 'Mi Ventanilla')]") and retry < max_retry:
        #     await self.page.locator("//input[@name='BTNACEPTAR']").click()
        #     retry += 1
        # await self.page.locator("//a[contains(text(), 'Mi Ventanilla')]").click()
        # await self.page.wait_for_selector("//a[contains(text(), 'Avisos')]")
        # await self.page.locator("//a[contains(text(), 'Avisos')]").click()
        # https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/notifica_miventanillaelectronicaadj?4DIYuQQKBgi01OQ3HlzQLKcqdGG8GOUC+DXfz/HUZVGImNMPi1vQi9WjdGcyGpPE
        # https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/notifica_miventanillaelectronicaadj?4DIYuQQKBgi01OQ3HlzQLKcqdGG8GOUC+DXfz/HUZVGImNMPi1vQi9WjdGcyGpPE
        # https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/notifica_miventanillaelectronicaadj?IHG7CHvg0lUSUr4E6VSOdtFhvggPU869hfJNFv5nLM8AuDif3N+XuysFAgIsNd80
        await self.page.goto("https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/notifica_miventanillaelectronicaadj?",
                             wait_until="networkidle")
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

            # cuit_Chaco = "30714604356"
            # clave_fiscal_Chaco = "Edge2021"
            # cuit_cliente_input = "30714604356"
            # client = "EDGE ARGENTINA S.R.L"

            cuit_Chaco = "30500846301"
            clave_fiscal_Chaco = "Chaco22."
            cuit_cliente_input = "30500846301"
            client = "ABBOTT LABORATORIES ARG. S.A"

            chaco = await Chaco.create(
                playwright,
                client,
                cuit_Chaco,
                clave_fiscal_Chaco,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                # headless=False
            )
            await chaco.procesar_jurisdiccion()


    asyncio.run(main())
