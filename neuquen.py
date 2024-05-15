from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion, LoginError


class Neuquen(Jurisdiccion):
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
            "Neuquén",
            "NEU",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        return self

    # async def AFIP_login(self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"):
    #     return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        # await self.AFIP_login()
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
            raise LoginError("Login error con mensajde de accion prohibida")

    async def buscar_notificacion(self):
        return await super().buscar_notificacion()

    async def tomar_screenshot(self):
        return await super().tomar_screenshot()

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Neuquen = "30714604356"
        clave_fiscal_Neuquen = "Edge2021"
        cuit_cliente_input = cuit_Neuquen
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
