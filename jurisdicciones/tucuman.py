import re
from datetime import datetime

from playwright.async_api import Playwright

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
        URL_AFIP_LOGIN: str = "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrtuc_ddjj",
        tucuman_success_url: str = None
    ) -> None:
        return await super().AFIP_login(URL_AFIP_LOGIN, success_url=tucuman_success_url)

    async def consultar_notificaciones(self) -> None:
        """
        Consulta las notificaciones en el portal de Tucumán.
        
        Raises:
            DelegacionError: Cuando el CUIT del cliente no está autorizado
            LoginError: Para otros errores de login que sí requieren screenshot
        """
        await self.AFIP_login(tucuman_success_url="rentastucuman")
        
        # Esperar a que la página esté completamente cargada
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # Esperar a que el botón de cerrar esté visible y hacer clic
        try:
            close_button = self.page.locator("xpath=//button[@class='close']")
            await close_button.wait_for(state="visible", timeout=10000)
            await close_button.click()
        except Exception:
            # Si no se encuentra el botón, continuar (puede que no esté presente)
            pass
        
        # Esperar a que los radio buttons estén cargados
        await self.page.wait_for_selector('input[name="radio_cuit_sele"]', state="visible", timeout=30000)
        
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
            raise DelegacionError(self.cliente)
        
        # Esperar a que el botón "Confirmar" esté visible y hacer clic
        confirm_button = self.page.locator("text='Confirmar'")
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()
        
        # Esperar a que la página se cargue después del clic en confirmar
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        
        # Esperar a que el enlace "Domicilio Fiscal Electrónico" esté visible
        dfe_link = self.page.locator("//a[text()='Domicilio Fiscal Electrónico']")
        await dfe_link.wait_for(state="visible", timeout=30000)
        await dfe_link.click()
        
        # Esperar a que la página se cargue después del clic en DFE
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        
        # Esperar a que el enlace "Notificaciones" esté visible
        notifications_link = self.page.locator("text='Notificaciones'")
        await notifications_link.wait_for(state="visible", timeout=30000)
        await notifications_link.click()
        
        # Esperar a que la página de notificaciones se cargue completamente
        await self.page.wait_for_load_state("networkidle", timeout=30000)

    async def buscar_notificacion(self) -> bool:
        """
        Busca notificaciones en la tabla de Tucumán.

        Retorna True si:
        1. No aparece el mensaje "En este momento no hay nuevas notificaciones para mostrar."
        2. Hay al menos una notificación con fecha posterior o igual a self.fecha_desde
        """
        try:
            # Garantizar que la página esté completamente cargada
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            
            # Esperar a que el contenido principal esté presente
            await self.page.wait_for_selector("body", state="visible", timeout=30000)
            
            # Esperar un poco más para asegurar que todos los elementos dinámicos se hayan cargado
            await self.page.wait_for_timeout(2000)
            
            self.logger.debug("TUCUMAN: Página completamente cargada, iniciando búsqueda de notificaciones")
            
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

            # Esperar a que la tabla esté presente y visible antes de buscar filas
            try:
                await self.page.wait_for_selector("table#miTabla", state="visible", timeout=10000)
                await self.page.wait_for_selector("table#miTabla tbody tr", timeout=10000)
            except Exception as e:
                self.logger.warning(f"TUCUMAN: No se encontró la tabla o no tiene filas: {str(e)}")
                return False

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
                    if fecha_texto_original:
                        fecha_texto_original = fecha_texto_original.strip()
                    else:
                        continue  # Si no hay contenido de texto, continuar con la siguiente fila

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
        """
        Toma una captura de pantalla de la página actual.
        Garantiza que la página esté completamente cargada antes de tomar la captura.
        """
        # Esperar a que la página esté completamente cargada
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # Esperar a que el body esté visible
        await self.page.wait_for_selector("body", state="visible", timeout=30000)
        
        # Esperar un poco más para asegurar que todos los elementos estén renderizados
        await self.page.wait_for_timeout(2000)
        
        return await super().tomar_screenshot()

    async def procesar_jurisdiccion(self):
        """
        Procesa la jurisdicción de Tucumán con manejo robusto de carga de página.
        """
        # Garantizar que la página esté completamente cargada antes de procesar
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # Esperar un poco más para asegurar estabilidad
        await self.page.wait_for_timeout(1000)
        
        return await super().procesar_jurisdiccion()

    async def _wait_for_element_and_ensure_loaded(
        self, 
        selector: str, 
        timeout: int = 30000, 
        retry_attempts: int = 3
    ) -> bool:
        """
        Espera a que un elemento esté presente y visible, con reintentos.
        
        Args:
            selector: Selector del elemento a esperar
            timeout: Tiempo máximo de espera en milisegundos
            retry_attempts: Número de intentos de reintento
            
        Returns:
            bool: True si el elemento fue encontrado, False en caso contrario
        """
        for attempt in range(retry_attempts):
            try:
                # Esperar a que la página esté estable
                await self.page.wait_for_load_state("networkidle", timeout=timeout)
                await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
                
                # Esperar al elemento específico
                await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
                
                # Verificar que el elemento realmente está visible
                is_visible = await self.page.is_visible(selector)
                if is_visible:
                    return True
                    
            except Exception:
                if attempt < retry_attempts - 1:
                    # Esperar antes del siguiente intento
                    await self.page.wait_for_timeout(2000)
                    continue
                else:
                    return False
        
        return False
