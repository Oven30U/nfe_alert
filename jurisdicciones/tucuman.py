import os
import re
from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, DelegacionError


class Tucuman(Jurisdiccion):
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
            "Tucuman",
            "924 TUCUMAN",
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
        URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrtuc_ddjj",
        tucuman_success_url: str = None
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN, success_url=tucuman_success_url)

    async def consultar_notificaciones(self) -> None:
        """
        Consulta las notificaciones en el portal de Tucumán.
        
        Raises:
            DelegacionError: Cuando el CUIT del cliente no está autorizado
            LoginError: Para otros errores de login que sí requieren screenshot
        """
        await self.AFIP_login(tucuman_success_url="rentastucuman")
        await self.page.locator("xpath=//button[@class='close']").click()
        
        radio_buttons = await self.page.query_selector_all(
            'input[name="radio_cuit_sele"]'
        )
        
        for radio in radio_buttons:
            radio_value = await self.page.evaluate("(element) => element.value", radio)
            if radio_value == self._cuit_cliente_input:
                await radio.check()
                break
        else:
            # Si no se encontró el CUIT, lanza excepción de delegación (sin screenshot)
            raise DelegacionError(
                self.cliente
            )
        
        await self.page.locator("text='Confirmar'").click()
        await self.page.click("//a[text()='Domicilio Fiscal Electrónico']")
        await self.page.locator("text='Notificaciones'").click()
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        """
        Busca notificaciones en la tabla de Tucumán.

        Retorna True si:
        1. No aparece el mensaje "En este momento no hay nuevas notificaciones para mostrar."
        2. Hay al menos una notificación con fecha posterior o igual a self.fecha_desde
        """
        try:
            # Verificar si existe el mensaje de no hay notificaciones
            no_hay_notificaciones = await self.page.is_visible(
                "text=En este momento no hay nuevas notificaciones para mostrar."
            )

            if no_hay_notificaciones:
                self.logger.debug(
                    "TUCUMAN: No hay notificaciones pendientes según el mensaje"
                )
                return False

            # Si llegamos aquí, no se muestra el mensaje de "no hay notificaciones"
            # Ahora verificamos las fechas de las notificaciones existentes

            # Convertir fecha_desde a objeto datetime (formato 'ddmmyyyy')
            fecha_desde = datetime.strptime(self.fecha_desde, "%d%m%Y")
            self.logger.debug(f"TUCUMAN: Fecha desde para comparar: {fecha_desde}")

            # Obtener todas las filas de la tabla
            filas = await self.page.query_selector_all(
                "xpath=//table[@id='miTabla']/tbody/tr"
            )

            self.logger.debug(f"TUCUMAN: Se encontraron {len(filas)} filas en la tabla")

            if len(filas) == 0:
                return False

            for fila in filas:
                # Obtener la fecha de la primera columna
                fecha_td = await fila.query_selector("td:first-child")
                if fecha_td:
                    fecha_texto_original = await fecha_td.text_content()
                    fecha_texto_original = fecha_texto_original.strip()

                    # NUEVO: Detectar y corregir duplicación de fecha
                    fecha_texto = fecha_texto_original
                    # Verificar si la fecha parece duplicada (tiene más de 20 caracteres)
                    if len(fecha_texto) > 20:
                        self.logger.debug(
                            f"TUCUMAN: Detectada posible duplicación en fecha: '{fecha_texto}'"
                        )
                        # Buscar el patrón de fecha dd/mm/yyyy
                        matches = re.findall(r"\d{2}/\d{2}/\d{4}", fecha_texto)
                        if len(matches) > 1:
                            # Usar sólo la última coincidencia + el resto del texto
                            last_match_pos = fecha_texto.rfind(matches[-1])
                            fecha_texto = fecha_texto[last_match_pos:]
                            self.logger.debug(
                                f"TUCUMAN: Fecha corregida: '{fecha_texto}'"
                            )

                    self.logger.debug(f"TUCUMAN: Procesando fecha: '{fecha_texto}'")

                    try:
                        # Primero intentar con formato dd/mm/yyyy HH:MM
                        fecha_notificacion = datetime.strptime(
                            fecha_texto, "%d/%m/%Y %H:%M"
                        )

                        self.logger.debug(
                            f"TUCUMAN: Comparando fecha de notificación {fecha_notificacion} con fecha desde {fecha_desde}"
                        )

                        # Comparar fechas - solo la parte de fecha, ignorando la hora
                        if fecha_notificacion.date() >= fecha_desde.date():
                            self.logger.debug(
                                f"TUCUMAN: Notificación encontrada con fecha {fecha_texto} posterior a {self.fecha_desde}"
                            )
                            return True
                    except ValueError as e:
                        self.logger.warning(
                            f"TUCUMAN: Error en primer formato: {str(e)}"
                        )
                        # Intentar con otros formatos posibles
                        try:
                            # Intentar extraer solo la primera parte que parezca una fecha
                            match = re.search(r"\d{2}/\d{2}/\d{4}", fecha_texto)
                            if match:
                                solo_fecha = match.group(0)
                                self.logger.debug(
                                    f"TUCUMAN: Extrayendo solo la fecha: {solo_fecha}"
                                )
                                fecha_notificacion = datetime.strptime(
                                    solo_fecha, "%d/%m/%Y"
                                )

                                if fecha_notificacion.date() >= fecha_desde.date():
                                    self.logger.debug(
                                        f"TUCUMAN: Notificación encontrada con fecha {solo_fecha}"
                                    )
                                    return True
                            else:
                                self.logger.warning(
                                    f"TUCUMAN: No se pudo extraer una fecha válida de '{fecha_texto}'"
                                )
                        except Exception as e2:
                            self.logger.warning(
                                f"TUCUMAN: Error procesando fecha alternativa: {str(e2)}"
                            )

            self.logger.debug(
                "TUCUMAN: No se encontraron notificaciones con fechas posteriores"
            )
            return False

        except Exception as e:
            self.logger.error(f"TUCUMAN: Error en buscar_notificacion: {str(e)}")
            # En caso de error, mejor reportar que sí hay notificaciones para revisión manual
            return True

    async def tomar_screenshot(self):
        await self.page.wait_for_load_state("networkidle")
        return await super().tomar_screenshot()

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_TUCUMAN_CLIENT")
        cuit_Tucuman = os.getenv("TEST_TUCUMAN_CUIT")
        clave_fiscal_Tucuman = os.getenv("TEST_TUCUMAN_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_TUCUMAN_CUIT_CLIENTE_INPUT")

        tucuman = await Tucuman.create(
            playwright,
            client,
            cuit_Tucuman,
            clave_fiscal_Tucuman,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await tucuman.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
