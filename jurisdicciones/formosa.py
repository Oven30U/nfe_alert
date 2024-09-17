from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Formosa(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None,
                 razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input,
                         razon_social_cliente_input, texto_notificacion, headless)
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
            headless=True
    ):
        self = await super().create(
            playwright,
            "Formosa",
            "909 FORMOSA",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            razon_social_cliente_input,
            texto_notificacion,
            headless=headless
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def consultar_notificaciones(self):
        await self.page.goto("https://www.atpformosa.gob.ar/consultas/index.php")
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@name='cuit']").fill(f"{self._cuit}")
        await self.page.locator("//input[@name='pass']").fill(f"{self._clave_fiscal}")
        await self.page.locator("//input[@value='Ingresar']").click()
        await self.page.wait_for_load_state("networkidle")
        if (
                await self.page.is_visible("text=No se encontraron datos.")
        ):
            raise LoginError(
                "Error de login en Formosa, al autorizar al usuario", self.cliente
            )
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("//span[contains(text(),'BUZÓN FISCAL')]")
        # await self.page.goto("https://www.atpformosa.gob.ar/consultas/buzon_fiscal_electronico.php")
        await self.page.goto(
            "https://www.atpformosa.gob.ar/consultas/buzon_fiscal_electronico.php?caseid=notificaciones_lista")
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        if await self.page.locator("//div[contains(text(),'NO SE ENCONTRARON NOTIFICACIONES')]").is_visible():
            return False
        else:
            # Seleccionar la segunda ocurrencia de fechas_disposicion
            fecha_mas_actual = self.page.locator("//table[@id='table7']//tr//td[3]").nth(1)
            fecha_text = (await fecha_mas_actual.inner_text()).strip()
            try:
                fecha_text = datetime.strptime(fecha_text, "%d/%m/%Y")
            except ValueError:
                return False
            fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
            fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")
            if fecha_desde_dt <= fecha_text <= fecha_hasta_dt:
                return True
            else:
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

            # cuit_Formosa = "30714604356"
            # clave_fiscal_Formosa = "Edge2021"
            # cuit_cliente_input = "30714604356"
            # client = "EDGE ARGENTINA S.R.L"

            cuit_Formosa = "30677757295"
            clave_fiscal_Formosa = "natura2014"
            cuit_cliente_input = "30677757295"
            client = "NATURA COSMETICOS S.A"

            formosa = await Formosa.create(
                playwright,
                client,
                cuit_Formosa,
                clave_fiscal_Formosa,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
            )
            await formosa.procesar_jurisdiccion()


    asyncio.run(main())
