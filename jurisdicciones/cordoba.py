import os
from datetime import datetime

from playwright._impl._errors import TimeoutError
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import (ConsultarNotificacionesError,
                                         Jurisdiccion)


class Cordoba(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, client_folder, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None, razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, client_folder, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input, razon_social_cliente_input, texto_notificacion, headless)
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
            "Cordoba",
            "904 CORDOBA",
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
    async def AFIP_login(
            self,
            URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=afip-gobcba",
    ):
        try:
            return await super().AFIP_login(URL_AFIP_LOGIN)
        except TimeoutError:
            print("Cordoba AFIP_login excepcion de error de Timeout.")

    async def intentar_representado(self):
        limite_loop = 0
        while limite_loop <= 15:
            try:
                if not await self.page.is_visible('text=" Actualmente esta consulta no arroja resultados. "'):
                    await self.realizar_representado()
                    return
                else:
                    print(
                        f"Cordoba Cartel de Actualmente esta consulta no arroja resultados: intento de recarga {limite_loop}.")
                    await self.page.reload()
            except Exception as e:
                print(f"Cordoba: Error no cargo representado: Recargando e intentando de nuevo... {e}")
                await self.page.reload()
            finally:
                limite_loop += 1

        print("Cordoba Se agotaron los intentos de seleccionar el representado.")
        raise ConsultarNotificacionesError("Se agotaron los intentos de seleccionar el representado.", self.cliente)

    async def realizar_representado(self):
        a_svg_cuit = f"//div[div[p[contains(text(),'{self.cuit_cliente_input}')]]]//a[1]"

        while True:
            try:
                await self.page.wait_for_load_state("load", timeout=90000)
                await self.page.wait_for_load_state("domcontentloaded", timeout=90000)
                await self.page.wait_for_selector(
                    a_svg_cuit,
                    state="attached",
                    timeout=12000,
                )
                await self.page.wait_for_selector(
                    'text="Estamos cargando la información ..."',
                    state="hidden",
                    timeout=90000,
                )
                await self.page.click(a_svg_cuit)
                await self.page.wait_for_selector(
                    'text="Estamos cargando la información ..."',
                    state="hidden",
                    timeout=90000,
                )
                break
            except TimeoutError:
                pagination_locator = "//ul[@class='pagination']//li[@class='page-item active ng-star-inserted']/following-sibling::li[1]"
                try:
                    await self.page.wait_for_selector(
                        pagination_locator,
                        state="attached",
                        timeout=12000,
                    )
                    await self.page.click(pagination_locator)
                except TimeoutError:
                    print("No se encontró el representado ni la paginación.")
                    break

    async def consultar_notificaciones(self):
        try:
            await self.AFIP_login()
        except Exception as e:
            print(f"Cordoba El metodo de AFIP_login falló: {e}")
        # try:
        #     await self.page.goto(
        #         "https://www.rentascordoba.gob.ar/nuevorentas/mis-representados",
        #         timeout=90000,
        #     )
        #     await self.page.wait_for_load_state("load", timeout=900000)
        # except Exception as e:
        #     print(f"Cordoba Error al cargar la página mis-representados: {e}")

        # Intentar loguearse con el representado
        # await self.intentar_representado()

        # selector_si = await self.page.query_selector('text="Sí"')
        # if selector_si:
        #     await self.page.click('text="Sí"', timeout=900000)
        #     await self.page.wait_for_load_state("load", timeout=60000)
        # else:
        #     print('Cordoba: El selector "Sí" no apareció, continuando la ejecución.')

        # try:
        #     await self.page.wait_for_selector('text="Sí"', state="attached", timeout=5000)
        #     await self.page.click('text="Sí"', timeout=900000)
        #     await self.page.wait_for_load_state("load", timeout=60000)
        # except TimeoutError:
        #     print('Cordoba: El selector "Sí" no apareció, continuando la ejecución.')

        # ! await asyncio.sleep(3)  # si no espero, no toma el "Si"

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
        await self.page.wait_for_load_state("domcontentloaded", timeout=90000)
        await self.page.goto(
            f"https://app.rentascordoba.gob.ar/rentas/servlet/aloginrepresentado?{self.cuit_cliente_input}",
            wait_until="domcontentloaded",
        )
        # //*[contains(text(), 'En representación de')]
        await self.page.wait_for_load_state("load", timeout=90000)
        await self.page.wait_for_load_state("domcontentloaded", timeout=90000)
        await self.page.wait_for_selector(
            # 'regex:/(En representación de|Buscar representado)/',
            # 'text="En representación de", text="Buscar representado"',
            # text="Buscar representado",
            'text="En representación de"',
            state="visible",
            timeout=90000,
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
                        print("Cordoba Error: Fecha no está en el formato correcto")
                        self.hay_notificacion = False
                        return
        except Exception as e:
            print(f"Cordoba Error: {e}")

        self.hay_notificacion = fecha_desde_date <= text_date
        return self.hay_notificacion

    async def tomar_screenshot(self):
        try:
            await self.page.wait_for_load_state(
                "networkidle", timeout=60000
            )
        except TimeoutError:
            print("Cordoba Tiempo de espera superado, se toma screenshot igualmente")
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio


    async def main():
        async with async_playwright() as playwright:
            fecha_desde = os.getenv("FECHA_DESDE")
            fecha_hasta = os.getenv("FECHA_HASTA")

            client = os.getenv("TEST_CORDOBA_CLIENT")
            cuit_Cordoba = os.getenv("TEST_CORDOBA_CUIT")
            clave_fiscal_Cordoba = os.getenv("TEST_CORDOBA_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_CORDOBA_CUIT_CLIENTE_INPUT")

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


    asyncio.run(main())
