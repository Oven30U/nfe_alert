import asyncio
from datetime import datetime
from playwright.async_api import Playwright, async_playwright, expect
from playwright._impl._errors import TimeoutError
from jurisdiccion import Jurisdiccion, ConsultarNotificacionesError


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
        try:
            return await super().AFIP_login(URL_AFIP_LOGIN)
        except TimeoutError:
            print("AFIP_login excepcion de error de Timeout.")


    async def intentar_representado(self):
        limite_loop = 0
        while limite_loop <= 15:
            try:
                if not await self.page.is_visible('text=" Actualmente esta consulta no arroja resultados. "'):
                    await self.realizar_representado()
                    return
                else:
                    print(f"Cartel de Actualmente esta consulta no arroja resultados: intento de recarga {limite_loop}.")
                    await self.page.reload()
            except Exception as e:
                print(f"Cordoba: Error no cargo representado: Recargando e intentando de nuevo... {e}")
                await self.page.reload()
            finally:
                limite_loop += 1

        print("Se agotaron los intentos de seleccionar el representado.")
        raise ConsultarNotificacionesError("Se agotaron los intentos de seleccionar el representado.", self.cliente)

    async def realizar_representado(self):
        await self.page.wait_for_selector(
            f"""//a[@ng-click="ingresar('{self.cuit_cliente_input}')"]""",
            state="attached",
            timeout=3000,
        )
        await self.page.click(
            f"""//a[@ng-click="ingresar('{self.cuit_cliente_input}')"]"""
        )

    async def consultar_notificaciones(self):
        try:
            await self.AFIP_login()
        except Exception as e:
            print(f"El metodo de AFIP_login falló: {e}")
        try:
            await self.page.goto(
                "https://www.rentascordoba.gob.ar/nuevorentas/mis-representados",
                timeout=90000,
            )
            await self.page.wait_for_load_state("load", timeout=900000)
        except Exception as e:
            print(f"Error al cargar la página mis-representados: {e}")

        # Intentar loguearse con el representado
        await self.intentar_representado()

        await self.page.wait_for_selector('text="Sí"', state="attached")
        await self.page.click('text="Sí"', timeout=900000)
        await self.page.wait_for_load_state("load", timeout=60000)

        #! await asyncio.sleep(3)  # si no espero, no toma el "Si"

        # await self.page.click('text="Sí"', timeout=0)
        # await asyncio.sleep(3)  # si no espero, no toma el "Si"
        # await self.page.wait_for_load_state("load")
        # await self.page.wait_for_load_state("load")
        # await self.page.wait_for_selector(
        #     'text=" Domicilio Fiscal Electrónico "', state="visible"
        # )
        # # Wait for the "Sí" button to be clickable
        # await self.page.wait_for_selector('text="Sí"', state="attached")
        # # Click the "Sí" button
        # await self.page.click('text="Sí"', timeout=0)
        # # Wait for the "Domicilio Fiscal Electrónico" text to be visible

        # try:
        #     # await self.page.wait_for_load_state("load", timeout=0)
        #     # await self.page.wait_for_load_state("networkidle", timeout=90000)
        #     await self.page.wait_for_selector(
        #         'text=" Domicilio Fiscal Electrónico "', state="visible", timeout=60000
        #     )
        #     await self.page.click('text=" Domicilio Fiscal Electrónico "')
        #     # await self.page.wait_for_load_state("networkidle", timeout=900000)
        # except Exception as e:
        #     print(f"Exception: {e}. Navegando directamente a la URL de dfe cordoba.")
        #     await self.page.goto(
        #         "https://www.rentascordoba.gob.ar/nuevorentas/domicilio-fiscal",
        #         wait_until="networkidle",
        #     )
        # expected_title = "MI RENTAS | Perfil Tributario"
        # current_title = await self.page.title()

        # if current_title != expected_title:
        #     await self.page.goto(
        #         "https://www.rentascordoba.gob.ar/nuevorentas/domicilio-fiscal",
        #         wait_until="networkidle",
        #     )

        # await self.page.wait_for_load_state("networkidle", timeout=60000)

        # //*[contains(text(), 'En representación de')]
        await self.page.wait_for_selector(
            'text="En representación de"', state="visible"
        )
        # await self.page.wait_for_load_state("load", timeout=60000)
        await self.page.goto(
            "https://www.rentascordoba.gob.ar/nuevorentas/domicilio-fiscal",
            wait_until="load",
        )
        while True:
            tbody_locator = self.page.locator(
                'xpath=//table[@class="table table-hover"]'
            )
            if tbody_locator and await tbody_locator.count() == 0:
                # If tbody does not exist, reload the page
                await self.page.wait_for_timeout(
                    3000
                )  # wait for 3 seconds before reloading
                await self.page.reload()
            if await tbody_locator.is_visible():
                break
            # if not await text_renderizando_grilla.is_visible():
            #     break
            # try:
            #     await text_renderizando_grilla.wait_for("hidden", timeout=4000)
            # except Exception:
            #     await self.page.reload()
            #     await self.page.wait_for_load_state("load")

    async def buscar_notificacion(self):
        try:
            await self.page.wait_for_load_state("load", timeout=60000)
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
        try:
            await self.page.wait_for_load_state(
                "networkidle", timeout=60000
            )
        except TimeoutError:
            print("Tiempo de espera superado, se toma screenshot igualmente")
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
