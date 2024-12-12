import os
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion


class EntreRios(Jurisdiccion):
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
            "EntreRios",
            "908 ENTRE RIOS",
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
    async def AFIP_login(self):
        return await super().AFIP_login()

    async def formatear_cuit(self, cuit):
        """
        Esta función formatea un número de CUIT 20386165476 al formato 20-38616547-6.

        Args:
        cuit: El número de CUIT a formatear.

        Returns:
        El número de CUIT formateado.
        """
        # Convertir el número de CUIT a una cadena.
        cuit_str = str(cuit)
        # Insertar un guión después del segundo dígito.
        cuit_str = cuit_str[:2] + "-" + cuit_str[2:]
        # Insertar un guión después del décimo dígito.
        cuit_str = cuit_str[:11] + "-" + cuit_str[11:]
        # Devolver el número de CUIT formateado.
        return cuit_str

    async def consultar_notificaciones(self):
        await self.AFIP_login()
        await self.page.fill(
            "input#buscadorInput", "Servicios Administradora Tributaria de Entre Ríos"
        )
        await self.page.click("a.dropdown-item")
        popup_info = await self.page.wait_for_event("popup")
        self.new_page = popup_info
        await self.new_page.wait_for_load_state("networkidle")
        cuit_contribuyente = await self.formatear_cuit(self._cuit_cliente_input)
        # await self.page.click(
        #     f'xpath=//*[@id="textoFiltro"][contains(text(), "{cuit_contribuyente}")]'
        # )
        await self.new_page.locator(
            f"xpath=//*[contains(text(), '{cuit_contribuyente}')]"
        ).click()
        await self.new_page.wait_for_load_state("load")
        await self.new_page.goto(
            "https://portal.ater.gob.ar/ventanillaVirtual/adhesionVentanilla.aspx"
        )
        await self.new_page.wait_for_load_state("load")

    async def buscar_notificacion(self):
        await self.new_page.wait_for_load_state("networkidle")
        cantidad_avisos = (await self.new_page.locator("#avisos").inner_text()).strip(
            "()"
        )
        cantidad_notificaciones = (
            await self.new_page.locator("#notificaciones").inner_text()
        ).strip("()")
        total_notificaciones = int(cantidad_avisos) + int(cantidad_notificaciones)
        self.hay_notificacion = total_notificaciones > 0
        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar dos screenshot's en la jurisdicción de Entre Rios."""
        secciones = [
            ("notificaciones", "a.nav-link.notificaciones"),
            ("avisos", "a.nav-link.avisos"),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.new_page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_ENTRE_RIOS_CLIENT")
        cuit_EntreRios = os.getenv("TEST_ENTRE_RIOS_CUIT")
        clave_fiscal_EntreRios = os.getenv("TEST_ENTRE_RIOS_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_ENTRE_RIOS_CUIT_CLIENTE_INPUT")
        entre_rios = await EntreRios.create(
            playwright,
            client,
            cuit_EntreRios,
            clave_fiscal_EntreRios,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await entre_rios.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
