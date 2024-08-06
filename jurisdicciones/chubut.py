from playwright.async_api import Playwright, async_playwright
from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Chubut(Jurisdiccion):
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
            "Chubut",
            "907 CHUBUT",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        return self

    async def consultar_notificaciones(self):
        await self.page.goto(
            "https://servicios.dgrchubut.gov.ar/modulos/login_siat.php?back_url=%2Fmodulos%2Fedom_contrib.php"
        )
        await self.page.wait_for_load_state("networkidle")
        await self.page.fill("xpath=//input[@name='log_user']", self._cuit)
        await self.page.fill("xpath=//input[@name='log_pass']", self._clave_fiscal)
        await self.page.click("xpath=//input[@class='entrar']")
        await self.page.wait_for_load_state("networkidle")
        incorrect_login = self.page.locator(
            'xpath=//div[text()="Usuario/clave incorrectos"]'
        )
        if await incorrect_login.count() > 0:
            raise LoginError("Login CUIT incorrecto", self.cliente)

    async def buscar_notificacion(self):
        heights = []
        for tabla_id in ["actos_grid", "actos_grid_fisca"]:
            height = await self.page.evaluate(
                f"""
                (() => {{
                    const tabla = document.querySelector("#{tabla_id}" + " tbody tr td:first-child");
                    return tabla ? window.getComputedStyle(tabla).height : "0";
                }})()
            """
            )
            heights.append(height)

        if all(height != "0px" for height in heights):
            self.hay_notificacion = True
        else:
            self.hay_notificacion = False

        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar dos screenshot's en la jurisdicción de Chubut."""
        secciones = [
            ("comunicaciones", "a#ui-id-1"),
            ("fiscalización_electrónica", "a#ui-id-2"),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Chubut = "30714604356"
        clave_fiscal_Chubut = "Edge2023"
        cuit_cliente_input = "30714604356"
        chubut = await Chubut.create(
            playwright,
            client,
            cuit_Chubut,
            clave_fiscal_Chubut,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await chubut.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
