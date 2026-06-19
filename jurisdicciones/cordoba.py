import os
from datetime import datetime

from playwright._impl._errors import TimeoutError
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import ConsultarNotificacionesError, Jurisdiccion


class Cordoba(Jurisdiccion):
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
        browser=None,
        context=None,
    ):
        self = await super().create(
            playwright,
            "Cordoba",
            "904 CORDOBA",
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
            browser=browser,
            context=context,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=afip-gobcba",
        success_url="https://www.rentascordoba.gob.ar/",
    ):
        try:
            return await super().AFIP_login(URL_AFIP_LOGIN, success_url=success_url)
        except TimeoutError:
            self.logger.warning("Cordoba AFIP_login excepcion de error de Timeout.")

    async def adherir_servicio(self):
        """
        Intenta adherir el servicio haciendo clic en el botón 'Adherir' si aparece.
        """
        try:
            await self.page.wait_for_selector(
                'button:has-text("Adherir")',
                state="visible",
                timeout=10000,
            )
            await self.page.click('button:has-text("Adherir")')
            self.logger.info("Cordoba: Botón 'Adherir' clicado.")
            await self.page.goto(
                "https://www.rentascordoba.gob.ar/nuevorentas/mis-representados",
                timeout=90000,
            )
            await self.page.wait_for_load_state("load", timeout=900000)
        except TimeoutError:
            self.logger.info("Cordoba: Botón 'Adherir' no apareció, continuando.")
        except Exception as e:
            self.logger.error(f"Cordoba: Error al adherir servicio: {e}")

    async def intentar_representado(self):
        limite_loop = 0
        while limite_loop <= 15:
            try:
                if not await self.page.is_visible(
                    'text=" Actualmente esta consulta no arroja resultados. "'
                ):
                    await self.realizar_representado()
                    return
                else:
                    self.logger.info(
                        f"Cordoba Cartel de Actualmente esta consulta no arroja resultados: intento de recarga {limite_loop}."
                    )
                    await self.page.reload()
            except Exception as e:
                self.logger.warning(
                    f"Cordoba: Error no cargo representado: Recargando e intentando de nuevo... {e}"
                )
                await self.page.reload()
            finally:
                limite_loop += 1

        self.logger.error(
            "Cordoba Se agotaron los intentos de seleccionar el representado."
        )
        raise ConsultarNotificacionesError(
            "Se agotaron los intentos de seleccionar el representado.", self.cliente
        )

    async def realizar_representado(self):
        # Selector para el botón "Cambiar representado" basado en el CUIT
        button_selector = f"//p[text()='{self.cuit_cliente_input}']/ancestor::div[contains(@class, 'representados-list__body')]//button[span[text()='Cambiar representado']]"
        # return
        while True:
            try:
                await self.page.wait_for_load_state("load", timeout=90000)
                await self.page.wait_for_load_state("domcontentloaded", timeout=90000)

                # Esperar a que el botón esté disponible
                await self.page.wait_for_selector(
                    button_selector,
                    state="attached",
                    timeout=12000,
                )

                # Esperar a que el indicador de carga esté oculto (si aplica)
                await self.page.wait_for_selector(
                    'text="Estamos cargando la información ..."',
                    state="hidden",
                    timeout=90000,
                )

                # Hacer clic en el botón (seleccionar el primero si hay múltiples)
                await self.page.locator(button_selector).first.click()

                # Esperar nuevamente a que la carga termine
                await self.page.wait_for_selector(
                    'text="Estamos cargando la información ..."',
                    state="hidden",
                    timeout=90000,
                )
                break
            except TimeoutError:
                # Manejo de paginación si el elemento no se encuentra
                pagination_locator = "//ul[@class='pagination']//li[@class='page-item active ng-star-inserted']/following-sibling::li[1]"
                try:
                    await self.page.wait_for_selector(
                        pagination_locator,
                        state="attached",
                        timeout=12000,
                    )
                    await self.page.click(pagination_locator)
                except TimeoutError:
                    try:
                        await self.page.goto("https://www.rentascordoba.gob.ar/mi-perfil/representado")
                        
                        await self.page.wait_for_load_state("load", timeout=90000)
                        await self.page.wait_for_load_state("domcontentloaded", timeout=90000)

                        await self.page.wait_for_selector(
                            'text="Perfil"',
                            state="visible",
                            timeout=90000,
                        )
                    except TimeoutError:
                        self.logger.warning(
                            "No se encontró el representado ni la paginación."
                        )
                        break

    async def consultar_notificaciones(self):
        # raise ConsultarNotificacionesError("La página se encuentra caída", self.cliente)
        try:
            await self.AFIP_login()
        except Exception as e:
            self.logger.error(f"Cordoba El metodo de AFIP_login falló: {e}")
        try:
            await self.page.goto(
                "https://www.rentascordoba.gob.ar/nuevorentas/mis-representados",
                timeout=90000,
            )
            await self.page.wait_for_load_state("load", timeout=900000)
        except Exception as e:
            self.logger.error(
                f"Cordoba Error al cargar la página mis-representados: {e}"
            )

        # Intentar adherir servicio si es necesario
        await self.adherir_servicio()

        # Intentar loguearse con el representado
        await self.intentar_representado()

        await self.page.wait_for_load_state("networkidle", timeout=90000)
        await self.page.wait_for_selector(
            "//*[contains(text(), 'En representación de')]",
            state="visible",
            timeout=90000,
        )
        await self.page.goto(
            "https://www.rentascordoba.gob.ar/nuevorentas/domicilio-fiscal",
            wait_until="load",
        )
        cont_fallos = 0
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
            if await tbody_locator.is_visible() or cont_fallos >= 10:
                break
            cont_fallos += 1

    async def buscar_notificacion(self):
        # raise ConsultarNotificacionesError("La página se encuentra caída", self.cliente)
        try:
            await self.page.wait_for_load_state("load", timeout=60000)
            if self.page.locator('xpath="(//tbody)[1]"') is not None:
                fecha_disposicion = self.page.locator("xpath=//tbody[1]/tr[1]/td[5]")
                # if fecha_disposicion is not None:
                if await fecha_disposicion.count() > 0:
                    texto = await fecha_disposicion.inner_text()
                    try:
                        text_date = datetime.strptime(texto, "%d/%m/%Y")
                        fecha_desde_date = datetime.strptime(self.fecha_desde, "%d%m%Y")
                    except ValueError:
                        self.logger.error(
                            "Cordoba Error: Fecha no está en el formato correcto"
                        )
                        self.hay_notificacion = False
                        return
        except Exception as e:
            self.logger.error(f"Cordoba Error: {e}")

        self.hay_notificacion = fecha_desde_date <= text_date
        return self.hay_notificacion

    async def tomar_screenshot(self):
        # raise TimeoutError("La página se encuentra caída")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=60000)
        except TimeoutError:
            self.logger.warning(
                "Cordoba Tiempo de espera superado, se toma screenshot igualmente"
            )
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
