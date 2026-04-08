import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page

from jurisdicciones.jurisdiccion import (
    Jurisdiccion,
    LoginErrorAfip,
    ConsultarNotificacionesError,
    DelegacionError,
)

import unicodedata


class Nacional(Jurisdiccion):
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
        filtro_fce=True,  # Valor por defecto True
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
        self.filtro_fce = filtro_fce

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
        filtro_fce=True,  # Valor por defecto True
    ):
        self = await super().create(
            playwright,
            "Nacional",
            "Nacional",
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
        self.filtro_fce = filtro_fce  # Guardar el valor de filtro_fce
        return self

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml",
        success_selector="input#buscadorInput",
    ):
        return await super().AFIP_login(
            URL_AFIP_LOGIN=URL_AFIP_LOGIN, success_selector=success_selector
        )

    async def consultar_notificaciones(self):
        try:
            self.page.set_default_timeout(180000)
            self.page.set_default_navigation_timeout(180000)

            await self.AFIP_login()
            await self.page.fill("input#buscadorInput", "Domicilio Fiscal Electrónico")
            await self.page.click("a.dropdown-item")
            popup_info = await self.page.wait_for_event("popup")
            self.new_page: Page = popup_info

            self.new_page.set_default_timeout(180000)
            self.new_page.set_default_navigation_timeout(180000)

            await self.new_page.wait_for_load_state("networkidle")
            await self._click_boton_cerrar()
            await self._click_recordar_mas_tarde()
            await self.new_page.click('text=" Comunicaciones de mis representados "')
            # await self.new_page.click("#d-select-81")
            await self.new_page.click(
                '//*[@id="d-select-111"]/span', timeout=10000
            )
            await self._seleccionar_cuit_cliente()
            await self.page.wait_for_load_state("networkidle")

            # Intentar esperar el encabezado con un timeout más razonable
            try:
                # Usar wait_for_selector en lugar de is_visible para mayor precisión
                await self.new_page.wait_for_selector(
                    'h5:has-text("Notificaciones de oficio")',
                    timeout=10000,
                    state="visible",
                )
                self.logger.info("Encabezado 'Notificaciones de oficio' encontrado")

                # Intentar cerrar el modal si está presente
                try:
                    await self.new_page.click('text="Cerrar"', timeout=3000)
                    self.logger.info("Botón 'Cerrar' encontrado y clickeado")
                except Exception as e:
                    self.logger.info(
                        "No se encontró botón 'Cerrar' o no fue necesario clickearlo"
                    )
            except Exception as e:
                self.logger.info(
                    "No se encontró encabezado 'Notificaciones de oficio', continuando normalmente"
                )

            self.fecha_desde = datetime.strptime(self.fecha_desde, "%d%m%Y").strftime(
                "%d/%m/%Y"
            )
            await self.new_page.fill(
                "xpath=(//label[contains(text(), 'Desde')]/following::input[1])[2]",
                f"{self.fecha_desde}",
            )
            self.fecha_hasta = datetime.strptime(self.fecha_hasta, "%d%m%Y").strftime(
                "%d/%m/%Y"
            )
            await self.new_page.fill(
                "xpath=(//label[contains(text(), 'Hasta')]/following::input[1])[2]",
                f"{self.fecha_hasta}",
            )  # \t\n
            await (
                self.new_page.locator('//button[contains(text(), "Aplicar")]')
                .nth(1)
                .click()
            )

            await self.new_page.click('//*[@id="collapse-filtros-root"]/div/div[3]/button', timeout=5000)
            await self.new_page.select_option("select[name='filtroEstado']", "No Leída", timeout=5000)

            # await completar_fechas(self.new_page, self.fecha_desde, self.fecha_hasta)
        except (LoginErrorAfip, DelegacionError) as e:
            raise
        except Exception as e:
            # Log the actual error details for debugging
            self.logger.error(f"Error en consulta de Nacional: {str(e)}")
            # Raise with standard message only
            raise ConsultarNotificacionesError(self.cliente)

    async def _seleccionar_cuit_cliente(self) -> None:
        """
        Selecciona el CUIT del cliente en el dropdown de contribuyentes representados.

        Raises:
            DelegacionError: Si la CUIT no se encuentra delegada o no está disponible para selección.
        """
        try:
            selector = f'xpath=//button[@id="{self.cuit_cliente_input}"]'
            is_visible = await self.new_page.is_visible(selector, timeout=5000)

            if not is_visible:
                self.logger.error(
                    f"La CUIT {self.cuit_cliente_input} no se encuentra delegada"
                )
                # Cambiar para usar el mensaje por defecto de DelegacionError
                raise DelegacionError(self.cliente)

            await self.new_page.click(selector)
            self.logger.debug(
                f"CUIT {self.cuit_cliente_input} seleccionada correctamente en ARCA"
            )
        except Exception as e:
            if isinstance(e, DelegacionError):
                raise
            self.logger.error(
                f"Error al seleccionar CUIT {self.cuit_cliente_input}: {e}"
            )
            raise ConsultarNotificacionesError(
                self.cliente, f"Error al seleccionar CUIT en ARCA"
            )

    async def _click_recordar_mas_tarde(self) -> None:
        """
        Intenta hacer clic en el botón 'Recordar más tarde' si está visible.

        No lanza excepciones si el botón no se encuentra.
        """
        try:
            # Verificar si existe el botón antes de intentar hacer clic
            is_visible = await self.new_page.is_visible(
                'text="Recordar más tarde"', timeout=10000
            )
            if is_visible:
                await self.new_page.click('text="Recordar más tarde"')
                self.logger.info("Botón 'Recordar más tarde' encontrado y clickeado")
            else:
                self.logger.info(
                    "Botón 'Recordar más tarde' no está visible, continuando..."
                )
        except Exception as e:
            self.logger.info(
                f"No se pudo interactuar con 'Recordar más tarde', continuando: {str(e)}"
            )

    async def buscar_notificacion(self):
        # Use a single selector to get all notification links
        all_links_selector = "xpath=//div[contains(@class, 'list-group')]//div[@id='notificaciones-bandeja-tab']/following-sibling::a"

        contador_filtro_hay_notificacion = 0
        todos_screenshots_exitosos = True

        try:
            # Get all links matching the selector
            self.logger.info("Buscando enlaces de notificaciones")
            enlaces = await self.new_page.locator(all_links_selector).all()
            self.logger.info(f"Se encontraron {len(enlaces)} enlaces de notificaciones")

            # Expand any collapsed filters if necessary
            filtros_colapsados = await self.new_page.locator(
                "xpath=//div[@aria-expanded='false']"
            ).all()
            for filtro in filtros_colapsados:
                await filtro.click()
                await self.new_page.wait_for_load_state("networkidle")
                await self.new_page.wait_for_load_state("load")
                await self.new_page.wait_for_load_state("domcontentloaded")

            # Process each link
            for enlace in enlaces:
                try:
                    texto_enlace = await enlace.inner_text()

                    # Skip FCE notifications if filtro_fce is True
                    if (
                        "Factura de Crédito Electrónica" in texto_enlace
                        and self.filtro_fce
                    ):
                        self.logger.info(
                            f"Saltando FCE según configuración de cliente: {texto_enlace}"
                        )
                        continue

                    # Click on the link and wait for page to load
                    await enlace.click()
                    await self.new_page.wait_for_load_state("networkidle")
                    await self.new_page.wait_for_load_state("load")
                    await self.new_page.wait_for_load_state("domcontentloaded")

                    # Check if there are no notifications
                    no_hay_notificaciones = await super().buscar_notificacion(
                        self.new_page, "No hay comunicaciones para mostrar"
                    )

                    if not no_hay_notificaciones:
                        contador_filtro_hay_notificacion += 1
                        self.logger.info(
                            f"Se encontraron notificaciones en {texto_enlace}"
                        )
                    else:
                        self.logger.info(f"No hay notificaciones en {texto_enlace}")

                    # Create a clean name for the screenshot
                    texto_filtrado = clean_texto_enlace(texto_enlace)
                    nombre_captura = f"{texto_filtrado.lower()}"

                    # Take screenshots
                    self.logger.info(f"Tomando captura para {nombre_captura}")
                    screen_estado = await self.tomar_screenshot_filtrado(nombre_captura)

                    if not screen_estado:
                        self.logger.warning(f"Falló captura para {nombre_captura}")
                        todos_screenshots_exitosos = False
                except Exception as e:
                    self.logger.error(
                        f"Error procesando enlace '{texto_enlace if 'texto_enlace' in locals() else 'desconocido'}': {str(e)}"
                    )
                    todos_screenshots_exitosos = False
                    continue
        except Exception as e:
            self.logger.error(f"Error general en buscar_notificacion: {str(e)}")
            todos_screenshots_exitosos = False

        self.hay_screenshots_filtrados = todos_screenshots_exitosos
        return True if contador_filtro_hay_notificacion > 0 else False

    async def tomar_screenshot_filtrado(self, tipo_notificacion) -> bool:
        try:
            self.logger.info(f"Iniciando captura filtrada para {tipo_notificacion}")

            # Ensure dates are in correct format before screenshot
            if "/" in self.fecha_desde:
                self.fecha_desde = self.fecha_desde.replace("/", "")
            if "/" in self.fecha_hasta:
                self.fecha_hasta = self.fecha_hasta.replace("/", "")

            current_page = 1

            while True:
                try:
                    # Count notifications
                    selector_notificaciones = "//div[@class='tab-pane active card-body']//tbody[@role='rowgroup']/tr"
                    cantidad_notificaciones = await self.new_page.locator(
                        selector_notificaciones
                    ).count()
                    self.logger.info(
                        f"Encontradas {cantidad_notificaciones} notificaciones en página {current_page}"
                    )

                    # If there are many notifications, scroll to the last one to ensure everything is loaded
                    if cantidad_notificaciones >= 7:
                        selector_ultima_notificacion = (
                            "(//div[@class='tab-pane active card-body']//tr)[last()]"
                        )
                        await self.new_page.evaluate(
                            """
                            (selector) => {
                                const element = document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                if (element) element.scrollIntoView();
                            }
                            """,
                            selector_ultima_notificacion,
                        )
                        # Wait for any lazy-loaded content to appear
                        await self.new_page.wait_for_timeout(500)
                except Exception as e:
                    self.logger.warning(
                        f"Error preparando página para captura: {str(e)}"
                    )

                # Take a single full-page screenshot
                screenshot_success = await super().tomar_screenshot(
                    self.new_page, nombre_extra=f"{tipo_notificacion}_p{current_page}"
                )

                if not screenshot_success:
                    self.logger.warning(
                        f"Falló captura de página {current_page} para {tipo_notificacion}"
                    )
                    return False

                # Check if there are more pages
                try:
                    selector_flecha_siguiente = "(//button[@role='menuitem'])[4]"
                    exists = (
                        await self.new_page.locator(selector_flecha_siguiente).count()
                        > 0
                    )

                    if not exists:
                        self.logger.info(
                            f"No se encontró botón de siguiente página para {tipo_notificacion}"
                        )
                        return True

                    clases_flecha_siguiente = await self.new_page.get_attribute(
                        selector_flecha_siguiente, "class"
                    )

                    if "disabled" in clases_flecha_siguiente:
                        self.logger.info(f"No hay más páginas para {tipo_notificacion}")
                        return True

                    # Navigate to next page
                    await self.new_page.click(selector_flecha_siguiente)
                    await self.new_page.wait_for_load_state("networkidle")
                    current_page += 1

                    # Scroll to top of new page to ensure it's properly loaded
                    await self.new_page.evaluate("window.scrollTo(0, 0)")
                except Exception as e:
                    self.logger.warning(f"Error navegando a siguiente página: {str(e)}")
                    return True  # Return true since we got at least the first page screenshot
        except Exception as e:
            self.logger.error(f"Error general en tomar_screenshot_filtrado: {str(e)}")
            return False

    async def tomar_screenshot(self):
        # Ensure dates are in correct format before any screenshot
        if "/" in self.fecha_desde:
            self.fecha_desde = self.fecha_desde.replace("/", "")
        if "/" in self.fecha_hasta:
            self.fecha_hasta = self.fecha_hasta.replace("/", "")

        # Si no se pudieron tomar capturas filtradas o hay_screenshots_filtrados no está definido
        if (
            not hasattr(self, "hay_screenshots_filtrados")
            or not self.hay_screenshots_filtrados
        ):
            # Tomar al menos una captura de pantalla general usando el método de la clase base
            basic_screenshot = await super().tomar_screenshot()
            # Devolver True si al menos una captura fue exitosa
            return basic_screenshot

        # Si ya se tomaron capturas filtradas exitosamente, simplemente devuelve ese valor
        return self.hay_screenshots_filtrados

    async def _click_boton_cerrar(self):
        try:
            # Esperar a que el botón de cerrar esté visible
            await self.new_page.wait_for_selector('text="Cerrar"', timeout=5000)
            await self.new_page.click('text="Cerrar"')
            self.logger.debug("Botón 'Cerrar' encontrado y clickeado")
        except Exception as e:
            self.logger.debug(
                "No se encontró botón 'Cerrar' o no fue necesario clickearlo"
            )

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


def clean_texto_enlace(input_str: str) -> str:
    text = input_str.split("\n")[0].strip().lower()
    nfkd_form = unicodedata.normalize("NFKD", text)
    result = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    result = result.replace("factura de credito electronica", "fce")
    return result


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_NACIONAL_CLIENT")
        cuit_Nacional = os.getenv("TEST_NACIONAL_CUIT")
        clave_fiscal_Nacional = os.getenv("TEST_NACIONAL_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_NACIONAL_CUIT_CLIENTE_INPUT")

        nacional = await Nacional.create(
            playwright,
            client,
            cuit_Nacional,
            clave_fiscal_Nacional,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await nacional.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
