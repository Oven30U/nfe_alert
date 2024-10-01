from playwright._impl._errors import TimeoutError
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion


class Mendoza(Jurisdiccion):
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
            "Mendoza",
            "913 MENDOZA",
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
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await self.page.goto(
                    "https://atm.mendoza.gov.ar/portalatm/misTramites/misTramitesLogin.jsp",
                    timeout=120000,
                )
                break
            except TimeoutError:
                if attempt < max_retries - 1:
                    continue
                else:
                    raise
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.fill("#cuit", f"{self._cuit}")
        await self.page.fill("#password", f"{self._clave_fiscal}")
        await self.page.locator("#ingresar").click()
        async with self.page.expect_popup() as popup_info:
            await self.page.click("#divDFE")
        self.new_page = await popup_info.value
        while True:
            await self.new_page.wait_for_load_state("networkidle")
            title = await self.new_page.title()
            if title == "Domicilio Fiscal Electrónico":
                break
        await self.new_page.locator(
            "xpath=(//*[@class='z-datebox'])[1]//input[1]"
        ).fill(self.fecha_desde)
        await self.new_page.locator(
            "xpath=(//*[@class='z-datebox'])[2]//input[1]"
        ).fill(self.fecha_hasta)
        await self.new_page.check("xpath=(//input[@type='radio'])[2]")  # Sólo sin Leer
        await self.new_page.locator("xpath=//button[text()='Buscar']").click()

    async def buscar_notificacion(self):
        """Busca notificaciones con vencimiento, intimaciones y comunicaciones sin leer. tbody [2, 5, 8]."""
        # Es necesario navegar entre las pestañas para renderizar los elementos
        self.hay_notificacion = False
        await self.new_page.get_by_text("NOTIFICACIONES CON VENCIMIENTO").click()
        notificaciones_con_vencimiento = await self.new_page.locator(
            "css=[class*='z-listitem']"
        ).count()
        await self.new_page.get_by_text("INTIMACIONES").click()
        intimaciones = await self.new_page.locator("css=[class*='z-listitem']").count()
        await self.new_page.get_by_text("COMUNICACIONES").click()
        comunicaciones = await self.new_page.locator(
            "css=[class*='z-listitem']"
        ).count()
        notificaciones_totales = (
                notificaciones_con_vencimiento + intimaciones + comunicaciones
        )
        if notificaciones_totales > 0:
            self.hay_notificacion = True

        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar tres screenshot's en la jurisdicción de Mendoza."""
        await self.new_page.get_by_text("NOTIFICACIONES CON VENCIMIENTO").click()
        seccion = "notificaciones_con_vencimiento"
        nombre_archivo = f"Estructura-robot/{self.cliente}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.new_page.wait_for_load_state("domcontentloaded")
            await self.new_page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_notificaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        await self.new_page.get_by_text("INTIMACIONES").click()
        seccion = "intimaciones"
        nombre_archivo = f"Estructura-robot/{self.cliente}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.new_page.wait_for_load_state("domcontentloaded")
            await self.new_page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_intimaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        await self.new_page.get_by_text("COMUNICACIONES").click()
        seccion = "comunicaciones"
        nombre_archivo = f"Estructura-robot/{self.cliente}/Output/{self.nombre}_{self.cliente}_{self.fecha_desde}_{self.fecha_hasta}_{self.hora_actual}_{seccion}.png"
        try:
            await self.new_page.wait_for_load_state("domcontentloaded")
            await self.new_page.screenshot(path=nombre_archivo, full_page=True)
            self.hay_screenshot_comunicaciones = True
        except Exception as e:
            print(f"Error taking screenshot en seccion {seccion}: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot en seccion {seccion}: {e}") from e

        if (
                self.hay_screenshot_notificaciones
                and self.hay_screenshot_intimaciones
                and self.hay_screenshot_comunicaciones
        ):
            self.hay_screenshot = True
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = "01052020"
        fecha_hasta = "30052024"
        client = "EDGE ARGENTINA S.R.L"
        cuit_Mendoza = "30714604356"
        clave_fiscal_Mendoza = "Edge2023"
        cuit_cliente_input = "30714604356"
        mendoza = await Mendoza.create(
            playwright,
            client,
            cuit_Mendoza,
            clave_fiscal_Mendoza,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await mendoza.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
