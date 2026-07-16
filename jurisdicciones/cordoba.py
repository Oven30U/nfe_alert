from datetime import datetime

from playwright.async_api import Playwright, TimeoutError as PlaywrightTimeoutError

from jurisdicciones.jurisdiccion import (
    ConsultarNotificacionesError,
    DelegacionError,
    Jurisdiccion,
    LoginError,
    LoginErrorAfip,
)


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
        return await super().AFIP_login(URL_AFIP_LOGIN, success_url=success_url)

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
        except PlaywrightTimeoutError:
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
            except DelegacionError as e:
                self.logger.error(f"Cordoba: servicio pendiente de delegación: {e}")
                raise e
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
        cambio_representado = False
        retries = 3
        cont = 0
        while not cambio_representado:
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
                cambio_representado = True
            except PlaywrightTimeoutError:
                # Manejo de paginación si el elemento no se encuentra
                pagination_locator = "//ul[@class='pagination']//li[@class='page-item active ng-star-inserted']/following-sibling::li[1]"
                try:
                    await self.page.wait_for_selector(
                        pagination_locator,
                        state="attached",
                        timeout=12000,
                    )
                    await self.page.click(pagination_locator)
                except PlaywrightTimeoutError as e:
                    try:
                        await self.page.goto(
                            "https://www.rentascordoba.gob.ar/mi-perfil/representado"
                        )

                        await self.page.wait_for_load_state("load", timeout=90000)
                        await self.page.wait_for_load_state(
                            "domcontentloaded", timeout=90000
                        )

                        await self.page.wait_for_selector(
                            'text="Perfil"',
                            state="visible",
                            timeout=90000,
                        )
                        cont += 1
                        if cont + 1 == retries:
                            raise DelegacionError(self.cliente) from e
                    except PlaywrightTimeoutError as e:
                        self.logger.warning(
                            "No se encontró el representado ni la paginación."
                        )
                        raise ConsultarNotificacionesError(self.cliente, "No se encontró el representado ni la paginación.") from e

    async def consultar_notificaciones(self):
        try:
            await self.AFIP_login()
        except (LoginError, LoginErrorAfip) as e:
            if LoginError.CREDENCIALES_ARCA in str(e):
                self.logger.error(
                    f"Cordoba AFIP_login excepcion de error de Login: {e}. Credenciales incorrectas."
                )
                raise LoginError(self.cliente, LoginError.CREDENCIALES_ARCA) from e
            self.logger.error(f"Cordoba AFIP_login excepcion de error de Login: {e}")
            raise LoginError(self.cliente) from e
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
        """
        Busca notificaciones no leídas en la tabla de Rentas Córdoba dentro del
        rango de fechas configurado en `self.fecha_desde`.

        - Espera a que la página termine de cargar.
        - Convierte `self.fecha_desde` (formato 'ddmmyyyy') a objeto `datetime`.
        - Recorre todos los elementos `tbody` de la tabla y extrae la fecha
            del primer renglón (columna 5) de cada `tbody`.
        - Si la fecha del registro está dentro del rango (>= `fecha_desde`)
            y el `tbody` contiene la clase `noleida`, marca
            `self.hay_notificacion` como `True` y finaliza la búsqueda.

        Returns
        bool: `True` si se encontró al menos una notificación no leída dentro del
            rango de fechas; `False` en caso contrario.

        Raises
        ConsultarNotificacionesError: Si ocurre cualquier excepción durante la búsqueda
            (se registra el error y se relanza la excepción con `self.cliente`).
        """
        try:
            await self.page.wait_for_load_state("load", timeout=60000)

            self.hay_notificacion = False
            fecha_desde_date = datetime.strptime(self.fecha_desde, "%d%m%Y")
            tbodies = self.page.locator("//tbody")
            cantidad_tbodies = await tbodies.count()

            for i in range(cantidad_tbodies):
                tbody = tbodies.nth(i)
                fecha_locator = tbody.locator("xpath=./tr[1]/td[5]")
                if await fecha_locator.count() == 0:
                    continue

                try:
                    texto_fecha = (await fecha_locator.inner_text()).strip()
                    text_date = datetime.strptime(texto_fecha, "%d/%m/%Y")
                except ValueError:
                    self.logger.warning(f"Cordoba: Fecha inválida '{texto_fecha}'")
                    continue

                # Solo se evalúan registros dentro del rango
                if fecha_desde_date <= text_date:
                    clases = await tbody.get_attribute("class") or ""
                    if "noleida" in clases.split():
                        self.hay_notificacion = True
                        break

        except Exception as e:
            self.logger.error(f"Cordoba Error: {e}")
            raise ConsultarNotificacionesError(self.cliente) from e

        return self.hay_notificacion

    async def tomar_screenshot(self):
        try:
            await self.page.wait_for_load_state("networkidle", timeout=60000)
        except PlaywrightTimeoutError:
            self.logger.warning(
                "Cordoba Tiempo de espera superado, se toma screenshot igualmente"
            )
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
