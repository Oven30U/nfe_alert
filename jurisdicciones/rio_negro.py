import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion


class RioNegro(Jurisdiccion):
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
            "RioNegro",
            "916 RIO NEGRO",
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
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrrn_sitio_seguro",
        rio_negro_success_url: str = None,
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN, success_url=rio_negro_success_url)

    async def consultar_notificaciones(self):
        await self.AFIP_login(
            rio_negro_success_url="https://siatwagencia.rionegro.gov.ar/rn/Extranet/index.php"
        )
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_selector('xpath=//select[@id="cuit_opera"]')
        await self.page.select_option(
            'xpath=//select[@id="cuit_opera"]', str(self._cuit_cliente_input)
        )
        await self.page.click("#btn_ingresar")
        await self.page.wait_for_load_state("networkidle")
        popup_aceptar_button = self.page.get_by_text("ACEPTAR")
        if await popup_aceptar_button.is_visible():
            await popup_aceptar_button.click()

    async def buscar_notificacion(self):
        """
        Verifica si hay notificaciones recientes en Rio Negro.

        1. Primero verifica la cantidad de mensajes y notificaciones
        2. Si hay alguna, comprueba si sus fechas son posteriores a fecha_desde
        """
        try:
            # Obtener las cantidades de mensajes y notificaciones
            cantidad_mensajes = await self.page.locator("#cantidad_msj").inner_text()
            cantidad_notificaciones_electronicas = await self.page.locator(
                "#cantidad_notif"
            ).inner_text()

            self.logger.debug(
                f"RIO NEGRO: Mensajes: {cantidad_mensajes}, Notificaciones: {cantidad_notificaciones_electronicas}"
            )

            # Convertir a enteros (asumiendo que son números)
            cantidad_mensajes = int(cantidad_mensajes)
            cantidad_notificaciones_electronicas = int(
                cantidad_notificaciones_electronicas
            )

            # Convertir fecha_desde a objeto datetime
            fecha_desde = datetime.strptime(self.fecha_desde, "%d%m%Y")
            self.logger.debug(f"RIO NEGRO: Fecha desde para comparar: {fecha_desde}")

            # Variable para rastrear si hay notificaciones relevantes
            hay_notificaciones_relevantes = False

            # Verificar mensajes si hay alguno
            if cantidad_mensajes > 0:
                # Necesitamos navegar a la pestaña de mensajes
                await self.page.click("button#btn_e-ventanilla")
                await self.page.click("a#tab_msj")
                await self.page.wait_for_load_state("networkidle")

                # Verificar si existe una tabla con mensajes
                if await self.page.is_visible("table#vent_elect_msj_grid"):
                    # Buscar la primera fila (la más reciente)
                    primera_fila = await self.page.query_selector(
                        "//table[@id='vent_elect_msj_grid']//tr[@id='1']/td[1]"
                    )

                    if primera_fila:
                        fecha_texto = await primera_fila.inner_text()
                        self.logger.debug(
                            f"RIO NEGRO: Fecha del mensaje más reciente: {fecha_texto}"
                        )

                        try:
                            # Intentar parsear la fecha (ajustar formato según sea necesario)
                            fecha_mensaje = datetime.strptime(
                                fecha_texto.strip(), "%d/%m/%Y"
                            )

                            # Comparar con fecha_desde
                            if fecha_mensaje.date() >= fecha_desde.date():
                                self.logger.debug(
                                    f"RIO NEGRO: Mensaje encontrado con fecha {fecha_texto} posterior a {self.fecha_desde}"
                                )
                                hay_notificaciones_relevantes = True
                        except ValueError as e:
                            self.logger.warning(
                                f"RIO NEGRO: Error al procesar fecha de mensaje '{fecha_texto}': {str(e)}"
                            )

            # Verificar notificaciones electrónicas si hay alguna
            if cantidad_notificaciones_electronicas > 0:
                # Navegar a la pestaña de notificaciones
                await self.page.click("button#btn_e-ventanilla")
                await self.page.click("a#tab_notif")
                await self.page.wait_for_load_state("networkidle")

                # Verificar si existe una tabla con notificaciones
                if await self.page.is_visible("table#ventanilla_elect_notif_grid"):
                    # Buscar la primera fila (la más reciente)
                    primera_fila = await self.page.query_selector(
                        "//table[@id='ventanilla_elect_notif_grid']//tr[@id='1']/td[1]"
                    )

                    if primera_fila:
                        fecha_texto = await primera_fila.inner_text()
                        self.logger.debug(
                            f"RIO NEGRO: Fecha de la notificación más reciente: {fecha_texto}"
                        )

                        try:
                            # Intentar parsear la fecha (ajustar formato según sea necesario)
                            fecha_notificacion = datetime.strptime(
                                fecha_texto.strip(), "%d/%m/%Y"
                            )

                            # Comparar con fecha_desde
                            if fecha_notificacion.date() >= fecha_desde.date():
                                self.logger.debug(
                                    f"RIO NEGRO: Notificación encontrada con fecha {fecha_texto} posterior a {self.fecha_desde}"
                                )
                                hay_notificaciones_relevantes = True
                        except ValueError as e:
                            self.logger.warning(
                                f"RIO NEGRO: Error al procesar fecha de notificación '{fecha_texto}': {str(e)}"
                            )

            self.hay_notificacion = hay_notificaciones_relevantes
            return self.hay_notificacion

        except Exception as e:
            self.logger.error(f"RIO NEGRO: Error en buscar_notificacion: {str(e)}")
            # En caso de error, mejor reportar que sí hay notificaciones para revisión manual
            self.hay_notificacion = True
            return self.hay_notificacion

    async def tomar_screenshot(self):
        await self.page.wait_for_load_state("networkidle")

        # Verificar si el botón está visible antes de hacer clic
        try:
            # Esperar brevemente para ver si el botón está visible
            if await self.page.is_visible("button#btn_e-ventanilla", timeout=2000):
                await self.page.click("button#btn_e-ventanilla")
                self.logger.info("RIO NEGRO: Se hizo clic en el botón e-ventanilla")
            else:
                self.logger.info(
                    "RIO NEGRO: El botón e-ventanilla no está visible, continuando con las pestañas"
                )
        except Exception as e:
            # Continuar aunque falle la verificación o el clic
            self.logger.warning(
                f"RIO NEGRO: No se pudo verificar/hacer clic en el botón: {str(e)}"
            )

        secciones = [
            ("notificaciones", "a#tab_notif"),
            ("mensajes", "a#tab_msj"),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")
        client = os.getenv("TEST_RIO_NEGRO_CLIENT")
        cuit_RioNegro = os.getenv("TEST_RIO_NEGRO_CUIT")
        clave_fiscal_RioNegro = os.getenv("TEST_RIO_NEGRO_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_RIO_NEGRO_CUIT_CLIENTE_INPUT")

        rio_negro = await RioNegro.create(
            playwright,
            client,
            cuit_RioNegro,
            clave_fiscal_RioNegro,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await rio_negro.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
