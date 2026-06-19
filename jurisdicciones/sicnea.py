import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Frame, Page

from jurisdicciones.jurisdiccion import DelegacionError, Jurisdiccion, LoginError

# from logger import Logger

# logger: Logger = Logger.get_logger()


class Sicnea(Jurisdiccion):
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
        # Convertir las fechas al formato dd/mm/yyyy
        fecha_desde = datetime.strptime(fecha_desde, "%d%m%Y").strftime("%d/%m/%Y")
        fecha_hasta = datetime.strptime(fecha_hasta, "%d%m%Y").strftime("%d/%m/%Y")
        self = await super().create(
            playwright,
            "Sicnea",
            "Sicnea",
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

    async def AFIP_login(
        self,
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml",
        success_selector=None,
    ):
        return await super().AFIP_login(
            URL_AFIP_LOGIN, success_selector=success_selector
        )

    async def consultar_notificaciones(self):
        await self.AFIP_login(success_selector="input#buscadorInput")
        await self.page.fill(
            "input#buscadorInput",
            "SICNEA - Gestion de comunicacion y notificacion electronica aduanera",
        )
        # Click en la opción de DFE desplegada
        await self.page.click("a.dropdown-item")
        popup_info = await self.page.wait_for_event("popup")
        self.new_page = popup_info
        await self.new_page.wait_for_load_state("networkidle")

        # Obtener todas las páginas abiertas en el contexto del navegador
        self.new_page_2: Page = self.context.pages[2]
        # Espera a que el script y el DOM se carguen completamente
        await self.new_page_2.wait_for_load_state("domcontentloaded")
        conexion_selector = await self.new_page_2.query_selector(
            "xpath=//td[contains(text(), 'CONEXION')]"
        )
        if conexion_selector:
            await self._select_cuit_from_dropdown()

        await self.new_page_2.wait_for_load_state("domcontentloaded")
        await self._handle_ingresar_button()

        await self.new_page_2.wait_for_load_state("domcontentloaded")
        await self.new_page_2.wait_for_selector(
            "xpath=//td[contains(@class, 'linksExternos') and .//span[contains(text(), 'MENU')]]",
            timeout=60000,
        )
        await self.new_page_2.hover(
            "xpath=//td[contains(@class, 'linksExternos') and .//span[contains(text(), 'MENU')]]"
        )
        # await self.debug_all_frames(self.new_page_2)
        frame: Frame | None = self.new_page_2.frame(name="iframeAreaMenuLateral")
        if frame is not None:
            # Reviso si el cuit coincide con el que aparece en el dropdown
            await self._check_cuit_in_dropdown(self.new_page_2)

            await frame.click("a:has-text(' Consulta')")
            await self.new_page_2.wait_for_load_state("networkidle")
            await self.new_page_2.wait_for_load_state("domcontentloaded")
            self.frame = self.new_page_2.frame(name="iframeAreaCargaDatos")
            await self.frame.wait_for_selector("select#ddlEstado")
            await self.frame.select_option("select#ddlEstado", value="ENVI")
            await self.frame.fill(
                "input[name='txtFechaNotificacionDesde']", self.fecha_desde
            )
            await self.frame.fill(
                "input[name='txtFechaNotificacionHasta']", self.fecha_hasta
            )
            await self.frame.click("input[name='btnBuscar']")
            await self.new_page_2.wait_for_load_state("networkidle")
            await self.frame.wait_for_load_state("networkidle")

    async def _check_cuit_in_dropdown(self, page: Page):
        datos_conexion_frame = await self._get_datos_conexion_frame(page)
        if datos_conexion_frame is None:
            self.logger.warning("No se encontró el frame mgenDatosConexion.aspx")
            return False

        try:
            await datos_conexion_frame.wait_for_selector(
                "#lblRazonSocialEmpresa",
                state="attached",
                timeout=10000
            )
        except Exception:
            self.logger.warning("No se encontró #lblRazonSocialEmpresa en mgenDatosConexion.aspx")
            return False

        text_cuit = await datos_conexion_frame.evaluate("""
        () => document.querySelector("#lblRazonSocialEmpresa")?.textContent?.trim() || ""
        """)
        self.logger.info(f"Texto CUIT encontrado: {text_cuit}")

        if not text_cuit:
            self.logger.warning("El texto de #lblRazonSocialEmpresa está vacío")
            return False

        if self.cuit_cliente_input not in text_cuit:
            self.logger.error(
                f"Client CUIT {self.cuit_cliente_input} not found in dropdown options. "
                "Service may not be delegated properly."
            )
            raise DelegacionError(self.cliente, LoginError.PENDIENTE_DELEGACION)
        return True

    async def _get_datos_conexion_frame(self, page: Page) -> Frame | None:
        for f in page.frames:
            if "mgenDatosConexion.aspx" in f.url:
                return f
        return None

    async def _select_cuit_from_dropdown(self) -> None:
        """
        Select client CUIT from dropdown if available.

        Validates the client's CUIT exists in the dropdown options before selecting it.
        Raises a LoginError if the CUIT is not found, indicating the service is not
        properly delegated to the user.

        Raises:
            LoginError: When the client's CUIT is not available in the dropdown options.
        """
        try:
            # Check if dropdown exists and is accessible
            dropdown_selector = "xpath=//select[@id='cmbEmpresa']"
            dropdown = await self.new_page_2.query_selector(dropdown_selector)

            if not dropdown:
                self.logger.warning("CUIT dropdown not found in SICNEA interface")
                return

            # Get available options in the dropdown
            options = await dropdown.evaluate("""(dropdown) => {
                return Array.from(dropdown.options).map(option => option.value);
            }""")

            # Verify client's CUIT exists in options
            if self.cuit_cliente_input not in options:
                self.logger.error(
                    f"Client CUIT {self.cuit_cliente_input} not found in dropdown options. "
                    "Service may not be delegated properly."
                )
                raise LoginError(self.cliente, LoginError.PENDIENTE_DELEGACION)

            # Select client's CUIT from dropdown
            await self.new_page_2.select_option(
                dropdown_selector, value=self.cuit_cliente_input
            )
            self.logger.info(
                f"Successfully selected client CUIT: {self.cuit_cliente_input}"
            )

        except LoginError:
            # Re-raise login errors without wrapping
            raise
        except Exception as e:
            self.logger.error(f"Error selecting client CUIT: {str(e)}")
            raise LoginError(self.cliente, f"Failed to select client CUIT: {str(e)}")

    async def _handle_ingresar_button(self) -> None:
        """
        Handle the optional "Ingresar" button that may appear in the SICNEA interface.

        The button may or may not be present depending on the system state.
        This method checks for its presence and clicks it if found, otherwise continues.

        Handles navigation events by ensuring the page is stable before querying elements.
        """
        try:
            await self.new_page_2.wait_for_load_state("networkidle")
            await self.new_page_2.wait_for_load_state("domcontentloaded")

            try:
                ingresar_button = await self.new_page_2.wait_for_selector(
                    "xpath=//input[@value='Ingresar']", timeout=5000, state="visible"
                )

                if ingresar_button:
                    self.logger.info(
                        "Botón 'Ingresar' en SICNEA encontrado, haciendo clic"
                    )
                    await ingresar_button.click()
                    await self.new_page_2.wait_for_load_state("networkidle")
                    await self.new_page_2.wait_for_load_state("domcontentloaded")
            except Exception as e:
                self.logger.info(
                    f"Botón 'Ingresar' en SICNEA no encontrado, continuando el flujo: {str(e)}"
                )

            # Esperar a que el elemento MENU esté visible
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.new_page_2.wait_for_selector(
                        "xpath=//td[contains(@class, 'linksExternos') and .//span[contains(text(), 'MENU')]]",
                        timeout=20000,
                        state="visible",
                    )
                    self.logger.info("Elemento MENU encontrado correctamente")
                    break  # Salir del bucle si se encuentra el elemento
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.logger.error(
                            f"No se pudo encontrar el elemento MENU después de {max_retries} intentos: {str(e)}"
                        )
                        raise  # Re-raise la excepción si se alcanzó el máximo de reintentos
                    self.logger.warning(
                        f"Reintentando búsqueda del elemento MENU (intento {attempt + 1}/{max_retries})"
                    )
                    # esperar un tiempo antes de reintentar
                    await self.new_page_2.wait_for_timeout(1000)

        except Exception as e:
            self.logger.error(f"Error en _handle_ingresar_button: {str(e)}")
            # Check specifically for navigation/context errors
            if (
                "Execution context was destroyed" in str(e)
                or "navigation" in str(e).lower()
            ):
                self.logger.warning(
                    "Detectada navegación durante la operación, esperando a que la página se estabilice"
                )
                # Add recovery actions for navigation interruptions
                await self.new_page_2.wait_for_load_state("networkidle", timeout=30000)
                await self.new_page_2.wait_for_load_state(
                    "domcontentloaded", timeout=30000
                )
            else:
                # For other errors, re-raise to be handled by the caller
                raise

    async def buscar_notificacion(self):
        # Inicializar una variable para controlar el bucle
        encontrado = False
        # Bucle que se ejecuta hasta que se encuentre alguno de los textos
        intento_encontrado = 0
        while not encontrado:
            texto_notificaciones = await self.frame.is_visible(
                "text='No hay datos relacionados a la busqueda'"
            )
            texto_motivo = await self.frame.is_visible("text='Motivo'")
            if texto_notificaciones or texto_motivo:
                encontrado = True
                # Si se encuentra alguno de los textos, se imprime cuál fue encontrado
                if texto_notificaciones:
                    print(
                        "Notificacion SICNEA: No hay datos relacionados a la busqueda"
                    )
                    self.hay_notificacion = False
                else:
                    print("Notificacion SICNEA: Hay datos relacionados a la busqueda")
                    self.hay_notificacion = True
            else:
                # await asyncio.sleep(0.5) # Esperar 0.5 segundos antes de volver a intentar
                await self.frame.wait_for_selector("div#pnlBotonera")

                print(f"SICNEA: intento de carga: {intento_encontrado}")
                intento_encontrado += 1

        return self.hay_notificacion

    async def tomar_screenshot(self):
        try:
            self.fecha_desde = self.fecha_desde.replace("/", "")
            self.fecha_hasta = self.fecha_hasta.replace("/", "")
            await self.frame.wait_for_selector("input#btnBuscar")
            await super().tomar_screenshot(self.new_page_2, nombre_extra="_enviadas")

            # Inicialización correcta con valor booleano
            hay_notificaciones_en_alguna_pagina = False
            if hasattr(self, "hay_notificacion") and isinstance(
                self.hay_notificacion, bool
            ):
                hay_notificaciones_en_alguna_pagina = self.hay_notificacion
            else:
                # Si no es un booleano pero contiene la palabra "Hay" asumimos que hay notificaciones
                hay_notificaciones_en_alguna_pagina = (
                    isinstance(self.hay_notificacion, str)
                    and "Hay" in self.hay_notificacion
                )

            # Si aparece el botón siguiente, entonces navega y toma screenshots
            cantidad_paginas_enviadas = 1
            while await self.frame.query_selector("a#lnkSiguiente"):
                await self.frame.click("a#lnkSiguiente")
                await self.frame.wait_for_selector("input#btnBuscar")

                # Verificar si hay notificaciones en esta página también
                hay_notificacion_en_pagina = not await self.frame.is_visible(
                    "text='No hay datos relacionados a la busqueda'"
                )
                hay_notificaciones_en_alguna_pagina = (
                    hay_notificaciones_en_alguna_pagina or hay_notificacion_en_pagina
                )

                await super().tomar_screenshot(
                    self.new_page_2,
                    nombre_extra=f"_enviadas_{cantidad_paginas_enviadas}",
                )
                cantidad_paginas_enviadas += 1

            # Configurar el segundo tipo de notificaciones (NOTI)
            await self.frame.wait_for_selector("select#ddlEstado")
            is_disabled = await self.frame.evaluate(
                "document.querySelector('select#ddlEstado').disabled"
            )
            if is_disabled:
                fecha_desde_filtro = f"{self.fecha_desde[:2]}/{self.fecha_desde[2:4]}/{self.fecha_desde[4:]}"
                fecha_hasta_filtro = f"{self.fecha_hasta[:2]}/{self.fecha_hasta[2:4]}/{self.fecha_hasta[4:]}"
                await self.frame.click("input#btnLimpiar")
                await self.frame.wait_for_load_state("networkidle")
                await self.frame.wait_for_selector("select#ddlEstado")
                await self.frame.select_option("select#ddlEstado", value="NOTI")
                await self.frame.fill(
                    "input[name='txtFechaNotificacionDesde']", fecha_desde_filtro
                )
                await self.frame.fill(
                    "input[name='txtFechaNotificacionHasta']", fecha_hasta_filtro
                )
                await self.frame.click("input[name='btnBuscar']")
                await self.new_page_2.wait_for_load_state("networkidle")
                await self.frame.wait_for_load_state("networkidle")
            else:
                await self.frame.select_option("select#ddlEstado", value="NOTI")
                await self.frame.click("input[name='btnBuscar']")

            try:
                await self.frame.wait_for_selector(
                    "select#ddlEstado", timeout=60000, state="visible"
                )
                await self.frame.wait_for_selector(
                    "input#btnBuscar", timeout=60000, state="visible"
                )
                self.logger.info("Selector 'select#ddlEstado' encontrado correctamente")
            except Exception as e:
                self.logger.warning(f"Timeout esperando 'select#ddlEstado': {str(e)}")
            # Verificar notificaciones en sección NOTI (primera página)
            hay_notificacion_noti = not await self.frame.is_visible(
                "text='No hay datos relacionados a la busqueda'"
            )
            hay_notificaciones_en_alguna_pagina = (
                hay_notificaciones_en_alguna_pagina or hay_notificacion_noti
            )

            notificado_cargado = False

            intento_encontrado = 0
            while not notificado_cargado:
                texto_notificaciones = await self.frame.is_visible(
                    "text='No hay datos relacionados a la busqueda'"
                )
                texto_motivo = await self.frame.is_visible("text='Motivo'")
                if texto_notificaciones or texto_motivo:
                    notificado_cargado = True

                    # Añadir esta verificación adicional después de cargar la página
                    if texto_motivo:  # Si hay motivo, hay notificaciones
                        hay_notificacion_en_pagina_noti = True
                        hay_notificaciones_en_alguna_pagina = (
                            hay_notificaciones_en_alguna_pagina
                            or hay_notificacion_en_pagina_noti
                        )

            await self.frame.wait_for_selector("input#btnBuscar")

            await super().tomar_screenshot(self.new_page_2, nombre_extra="_notificadas")
            cantidad_paginas_notificadas = 1
            while await self.frame.query_selector("a#lnkSiguiente") is not None:
                await self.frame.click("a#lnkSiguiente")
                await self.frame.wait_for_selector("input#btnBuscar")
                await super().tomar_screenshot(
                    self.new_page_2,
                    nombre_extra=f"_notificadas_{cantidad_paginas_notificadas}",
                )
                cantidad_paginas_notificadas += 1

            # Actualizar el estado final de notificaciones con el formato de string esperado
            if hay_notificaciones_en_alguna_pagina:
                self.hay_notificacion = "Hay notificaciones"
                self.logger.info("Estado final: Hay notificaciones")
            else:
                self.hay_notificacion = "No hay notificaciones"
                self.logger.info("Estado final: No hay notificaciones")
            self.hay_screenshot = True

        except Exception as e:
            print(f"Error taking screenshot: {e}")
            self.hay_screenshot = False
            raise Exception(f"Error taking screenshot: {e}") from e

        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    async def main():
        async with async_playwright() as playwright:
            fecha_desde = os.getenv("FECHA_DESDE")
            fecha_hasta = os.getenv("FECHA_HASTA")
            client = os.getenv("TEST_SICNEA_CLIENT")
            client_folder = os.getenv("TEST_SICNEA_CLIENT_FOLDER")
            cuit_sicnea = os.getenv("TEST_SICNEA_CUIT")
            clave_fiscal_sicnea = os.getenv("TEST_SICNEA_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_SICNEA_CUIT_CLIENTE_INPUT")

            sicnea = await Sicnea.create(
                playwright,
                client,
                client_folder,
                cuit_sicnea,
                clave_fiscal_sicnea,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await sicnea.procesar_jurisdiccion()

    asyncio.run(main())
