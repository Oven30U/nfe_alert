import asyncio
from datetime import datetime
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion


class Cordoba(Jurisdiccion):
    @classmethod
    async def create(
        cls,
        playwright: Playwright,
        cliente,
        cuit,
        clave_fiscal,
        fecha_desde,
        fecha_hasta,
        cuit_cliente_input=None,
    ):
        self = await super().create(
            playwright,
            "Cordoba",
            "904 CORDOBA",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=afip-gobcba",
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        await self.AFIP_login()
        await self.page.goto(
            "https://www.rentascordoba.gob.ar/nuevorentas/mis-representados"
        )
        await self.page.wait_for_load_state("load")
        while True:
            try:
                await self.page.click(
                    f"""//a[@ng-click="ingresar('{self.cuit_cliente_input}')"]""",
                    timeout=2000,
                )
                break
            except Exception as e:
                print(f"Error: {e}. Recargando e intentando de nuevo en un 1 seg...")
                await asyncio.sleep(1)
                await self.page.reload()

        await asyncio.sleep(3)  # si no espero, no toma el "Si"
        await self.page.click('text="Sí"', timeout=6000)
        await asyncio.sleep(3)  # si no espero, no toma el "Si"
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_selector(
            'text=" Domicilio Fiscal Electrónico "', state="visible"
        )
        try:
            await self.page.click('text=" Domicilio Fiscal Electrónico "')
            await self.page.wait_for_load_state(
                "domcontentloaded", timeout=5000
            )  # espera 5 segundos
        except Exception as e:
            print(f"Exception: {e}. Navegando directamente a la URL de dfe cordoba.")
            await self.page.goto(
                "https://www.rentascordoba.gob.ar/nuevorentas/domicilio-fiscal",
                wait_until="load",
            )
        expected_title = "MI RENTAS | Perfil Tributario"
        current_title = await self.page.title()

        if current_title != expected_title:
            await self.page.goto(
                "https://www.rentascordoba.gob.ar/nuevorentas/domicilio-fiscal",
                wait_until="load",
            )

        while True:
            text_renderizando_grilla = self.page.locator(
                'xpath=//*[contains(text(), "Renderizando grilla")]'
            )
            if not await text_renderizando_grilla.is_visible():
                break
            await self.page.reload()
            await self.page.wait_for_load_state("load")
            # await asyncio.sleep(2)

    async def buscar_notificacion(self):
        try:
            if self.page.locator('xpath="(//tody)[1]"') is not None:
                fecha_disposicion = self.page.locator("xpath=//tbody[1]/tr[1]/td[5]")
                if fecha_disposicion is not None:
                    texto = await fecha_disposicion.inner_text()
                    try:
                        text_date = datetime.strptime(texto, "%d/%m/%Y")
                        fecha_desde_date = datetime.strptime(self.fecha_desde, "%d%m%Y")
                    except ValueError:
                        print("Error: Fecha no está en el formato correcto")
                        self.hay_notificacion = False
                        return
        except Exception as e:
            print(f"Error: {e}")

        self.hay_notificacion = fecha_desde_date <= text_date
        return self.hay_notificacion

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Cordoba = "20386165476"
        clave_fiscal_Cordoba = "Gabriel1994"
        cuit_cliente_input = "30714604356"
        cordoba = await Cordoba.create(
            playwright,
            client,
            cuit_Cordoba,
            clave_fiscal_Cordoba,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await cordoba.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
