import re
import os

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Neuquen(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, client_folder, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None,
                 razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, client_folder, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input,
                         razon_social_cliente_input, texto_notificacion, headless)
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
            headless=True
    ):
        self = await super().create(
            playwright,
            "Neuquen",
            "915 NEUQUEN",
            cliente, client_folder,
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
        await self.page.goto("https://rentasneuquenweb.gob.ar/nqn/Extranet/index.php")
        await self.page.locator("#btn_sit").click()
        await self.page.get_by_role("textbox", name="Usuario").click()
        await self.page.get_by_role("textbox", name="Usuario").fill(
            f"{self._cuit_cliente_input}"
        )
        await self.page.get_by_placeholder("Contraseña").click()
        await self.page.get_by_placeholder("Contraseña").fill(f"{self._clave_fiscal}")
        await self.page.get_by_role("button", name="Ingresar").click()
        if (
                await self.page.locator(
                    "text='Acción prohibida, por favor ingrese nuevamente al sistema.'"
                ).count()
        ) > 0:
            raise LoginError(self.cliente)

    async def buscar_notificacion(self):
        await self.page.wait_for_load_state(
            "networkidle"
        )  # necesario para encontrar los elementos
        cantidad_notificaciones = await self.page.locator("#cant_notif").inner_text()
        cantidad_comunicaciones = await self.page.locator("#cant_comunic").inner_text()
        # Extrae solo los números del texto
        cantidad_notificaciones = re.findall(r"\d+", cantidad_notificaciones)
        cantidad_comunicaciones = re.findall(r"\d+", cantidad_comunicaciones)
        if cantidad_notificaciones and cantidad_comunicaciones:
            total_notificaciones = int(cantidad_notificaciones[0]) + int(
                cantidad_comunicaciones[0]
            )
        else:
            total_notificaciones = 0
        self.hay_notificacion = total_notificaciones > 0
        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar dos screenshot's en la jurisdicción de Neuquen."""
        self.fecha_desde = self.fecha_desde.replace("/", "")
        self.fecha_hasta = self.fecha_hasta.replace("/", "")
        secciones = [
            ("notificaciones", 'xpath=//a[@href="div_notificaciones"]'),
            ("comunicaciones", 'xpath=//a[@href="div_comunicaciones"]'),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")
        client = os.getenv("TEST_NEUQUEN_CLIENT")
        cuit_Neuquen = os.getenv("TEST_NEUQUEN_CUIT")
        clave_fiscal_Neuquen = os.getenv("TEST_NEUQUEN_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_NEUQUEN_CUIT_CLIENTE_INPUT")
        
        neuquen = await Neuquen.create(
            playwright,
            client,
            cuit_Neuquen,
            clave_fiscal_Neuquen,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        # await neuquen.AFIP_login()
        await neuquen.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
