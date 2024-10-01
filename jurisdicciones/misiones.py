from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Misiones(Jurisdiccion):
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
            "Misiones",
            "914 MISIONES",
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
        await self.page.goto("https://extranet.atm.misiones.gob.ar/Extranet/index.php")
        await self.page.locator("xpath=//button[@id='btn_sit']").click()
        # Utiliza press para evitar captchas
        await self.page.fill("input#log_user_aux", self._cuit)
        await self.page.press("input#log_user_aux", "Tab")
        await self.page.fill("input#log_pass_aux", self._clave_fiscal)
        await self.page.press("input#log_pass_aux", "Tab")
        await self.page.press("input#log_pass_aux", "Enter")
        await self.page.wait_for_load_state("networkidle")
        mensaje_login_incorrecto = await self.page.locator(
            "text='El nombre de usuario o la contraseña introducidos no son correctos'"
        ).count()
        if mensaje_login_incorrecto > 0:
            raise LoginError("Login error con mensajde de accion prohibida")

    async def buscar_notificacion(self, retry_count=0):
        cantidad_notificaciones = (
            await self.page.locator(
                "//a[@id='tab_notif']//span[@id='sp_cant_notif']"
            ).inner_text()
        ).strip("()")
        cantidad_comunicaciones = (
            await self.page.locator(
                "//a[@id='tab_comun']//span[@id='sp_cant_notif']"
            ).inner_text()
        ).strip("()")
        if not cantidad_notificaciones and retry_count < 3:  # Limit to 3 retries
            await self.consultar_notificaciones()
            return await self.buscar_notificacion(retry_count=retry_count + 1)
        elif cantidad_notificaciones and cantidad_comunicaciones:
            total_notificaciones = int(cantidad_notificaciones) + int(
                cantidad_comunicaciones
            )
        else:
            total_notificaciones = 0
        self.hay_notificacion = total_notificaciones > 0
        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar dos screenshot's en la jurisdicción de Misiones."""
        secciones = [
            ('notificaciones', 'a#tab_notif'),
            ('avisos', 'a#tab_comun')
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(secciones, self.page, delay=2)
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Misiones = "30714604356"
        clave_fiscal_Misiones = "Edge2021"
        cuit_cliente_input = "30714604356"
        misiones = await Misiones.create(
            playwright,
            client,
            cuit_Misiones,
            clave_fiscal_Misiones,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await misiones.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
