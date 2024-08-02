from playwright.async_api import Playwright, async_playwright
from jurisdiccion import Jurisdiccion, LoginError


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
        iframe = self.page.frames[0]
        # Seleccionar el elemento usando el método locator y luego llenar el campo
        login_user = iframe.locator("input#vUSRLOGIN")
        await login_user.type(f"{self._cuit}")
        await iframe.locator("input#vUSRLOGIN").fill(f"{self._cuit}")
        # await self.page.fill("//input[@id='vUSRLOGIN']", f"{self._cuit}")
        await iframe.fill("//input[@id='vUSRLOGIN']", f"{self._cuit}")
        await iframe.fill("input#vUSRLOGIN", f"{self._cuit}")
        await iframe.fill("input#vPWDLOGIN", f"{self._clave_fiscal}")
        await iframe.click("//input[@name='BUTTON1']")

        await self.page.wait_for_load_state("domcontentloaded")

        if (
                await  self.page.is_visible("text=El CUIT ingresado No Existe o No se encuentra Activo")
        ):
            raise LoginError(
                "Error de login en La Rioja, al autorizar al usuario", self.cliente
            )

        # cuit_clic = self._cuit_cliente_input[:2] + "-" + self._cuit_cliente_input[2:]
        # await iframe.click(
        #     f"//form[@id='FrmSeleccionEmpresa']//td[contains(text(),'{cuit_clic}')]/following-sibling::td[2]/input[@type='radio']")
        # await iframe.click("input#vConfirmar")
        # await iframe.click("//li[contains(text(), 'Consulta de Novedades/Trámites')]")
        # await self.page.wait_for_load_state("domcontentloaded")
        # await self.page.wait_for_load_state("networkidle")

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
        fecha_desde = "01072024"
        fecha_hasta = "30072024"

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
