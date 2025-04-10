import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError

from logger import Logger

logger = Logger.get_logger()


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
        self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        await self.AFIP_login()
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
        self.new_page_2 = self.context.pages[2]
        # Espera a que el script y el DOM se carguen completamente
        await self.new_page_2.wait_for_load_state("domcontentloaded")
        conexion_selector = await self.new_page_2.query_selector(
            "xpath=//td[contains(text(), 'CONEXION')]"
        )
        if conexion_selector:
            # Verificar si el CUIT existe en las opciones antes de seleccionarlo
            dropdown = await self.new_page_2.query_selector("xpath=//select[@id='cmbEmpresa']")
            if dropdown:
                # Obtener todas las opciones disponibles
                options = await dropdown.evaluate('''(dropdown) => {
                    return Array.from(dropdown.options).map(option => option.value);
                }''')
                
                # Verificar si el CUIT del cliente está en las opciones
                if self.cuit_cliente_input not in options:
                    raise LoginError(self.cliente, LoginError.PENDIENTE_DELEGACION)
                    
            await self.new_page_2.select_option(
                "xpath=//select[@id='cmbEmpresa']", value=self.cuit_cliente_input
            )

        await self.new_page_2.wait_for_load_state("domcontentloaded")
        try:
            ingresar_button = await self.new_page_2.query_selector(
                "xpath=//input[@value='Ingresar']"
            )
            if ingresar_button:
                await ingresar_button.click()
        except Exception as e:
            print(
                "El botón 'Ingresar' en Sicnea no se encontró, esperando la carga de la documentación..."
                f"Warning: {e}"
            )

        await self.new_page_2.wait_for_load_state("domcontentloaded")
        await self.new_page_2.wait_for_selector(
            "xpath=//td[contains(@class, 'linksExternos') and .//span[contains(text(), 'MENU')]]",
            timeout=60000,
        )
        await self.new_page_2.hover(
            "xpath=//td[contains(@class, 'linksExternos') and .//span[contains(text(), 'MENU')]]"
        )
        # Cambiar al frame iframeAreaMenuLateral
        frame = self.new_page_2.frame(name="iframeAreaMenuLateral")
        if frame is not None:
            # Realizar hover sobre el elemento del menú
            # await frame.hover("xpath=//td[contains(@class, 'linksExternos') and .//span[contains(text(), 'MENU')]]")
            # Esperar un momento para asegurarse de que el menú se despliegue
            # await self.new_page_2.hover.wait_for_timeout(1000)
            # Hacer clic en el enlace "Ver Notificacion/Comunicacion"
            # await frame.click("a:has-text('Ver Notificacion/Comunicacion')")
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
            # await frame.wait_for_selector("input#btnBuscar")
            # await frame.wait_for_selector("xpath=//div[@id='pnlProcesando' and @style='width:100%;display:none;']")
            # await frame.wait_for_selector("div#pnlProcesando", state='hidden')
            # await frame.wait_for_selector("div#pnlSinDatos")

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
                logger.info("Selector 'select#ddlEstado' encontrado correctamente")
            except Exception as e:
                logger.warning(f"Timeout esperando 'select#ddlEstado': {str(e)}")
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
                logger.info("Estado final: Hay notificaciones")
            else:
                self.hay_notificacion = "No hay notificaciones"
                logger.info("Estado final: No hay notificaciones")
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
