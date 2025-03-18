import os
from datetime import datetime
import requests
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Salta(Jurisdiccion):
    def __init__(
        self,
        nombre,
        codigo,
        cliente,
        client_folder,
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
            client_folder,
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
        client_folder,
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
            "Salta",
            "917 SALTA",
            cliente,
            client_folder,
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

    # async def consultar_notificaciones(self):
    #     if (True):
    #         self.consultar_notificaciones_dgr()
    #     else:
    #         ...

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrsalta_rentas",
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        # Hacer login con requests
        client = requests.Session()

        login_information = {
            "usuario": self._cuit,
            "password": self._clave_fiscal,
            "pagina": "/login.jsp",
            "disconect": "No",
            "tokengRecaptcha": "",
        }

        if int(str(self._cuit)[0]) != 3:
            await self.AFIP_login()
        else:
            response = client.post(
                "https://www.dgrsalta.gov.ar/rentassalta/form.login",
                data=login_information,
            )

            if "Usuario o Password Incorrecto" in response.text:
                raise LoginError(self.cliente)

        # Obtener las cookies de la sesión
        cookies = client.cookies.get_dict()

        # Añadir las cookies a la sesión de Playwright
        for name, value in cookies.items():
            await self.context.add_cookies(
                [
                    {
                        "name": name,
                        "value": value,
                        "domain": "www.dgrsalta.gov.ar",
                        "path": "/",
                    }
                ]
            )

        # Navegar a la página después de iniciar sesión
        await self.page.goto("https://www.dgrsalta.gov.ar/rentassalta/login.jsp")
        await self.page.wait_for_load_state("networkidle")

        # Verificar si el login fue exitoso buscando un elemento específico
        if not await self.page.query_selector("#enviaLogout"):
            raise LoginError(self.cliente)

        # Continuar con las acciones en la página
        await self.page.wait_for_selector(
            "//a[contains(text(), 'Domicilio Fiscal Electrónico')]"
        )
        await self.page.locator(
            "//a[contains(text(), 'Domicilio Fiscal Electrónico')]"
        ).click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector(
            "//a[contains(text(), 'Ventanilla Única de Novedades')]"
        )
        await self.page.locator(
            "//a[contains(text(), 'Ventanilla Única de Novedades')]"
        ).click()
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        elements = await self.page.locator(
            "//td[contains(text(),'Por el momento no tiene novedades...')]"
        ).all()
        return False if len(elements) == 2 else True

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    async def main():
        async with async_playwright() as playwright:
            fecha_desde = os.getenv("FECHA_DESDE")
            fecha_hasta = os.getenv("FECHA_HASTA")
            client = os.getenv("TEST_SALTA_CLIENT")
            cuit_Salta = os.getenv("TEST_SALTA_CUIT")
            clave_fiscal_Salta = os.getenv("TEST_SALTA_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_SALTA_CUIT_CLIENTE_INPUT")

            salta = await Salta.create(
                playwright,
                client,
                cuit_Salta,
                clave_fiscal_Salta,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await salta.procesar_jurisdiccion()

    asyncio.run(main())
