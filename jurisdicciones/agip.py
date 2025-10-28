import os
from datetime import datetime

from playwright.async_api import Playwright, TimeoutError, async_playwright, expect

from jurisdicciones.jurisdiccion import (
    ConsultarNotificacionesError,
    DelegacionError,
    Jurisdiccion,
    LoginError,
    BuscarNotificacionError,
)


class Agip(Jurisdiccion):
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
            "Agip",
            "901 CABA",
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

    async def _login(self):
        """
        Por cambios en el flujo de ingreso de AGIP:
        Verifica si el ingreso de "Clave Ciudad" es visible.
        Si está visible, lo pulsa e intenta _login_clave_ciudad() primero.
        Si no está visible, intenta _login_miba() primero.
        Si el primer intento falla con LoginError, prueba el método alternativo.
        Solo lanza LoginError si ambos métodos de autenticación fallan.
        """
        await self.page.goto("https://claveciudad.agip.gob.ar/")
        await self.page.wait_for_load_state("networkidle")

        clave_ciudad_locator = self.page.locator(
            "xpath=//div[contains(@class, 'clave-ciudad-info')]/a[contains(text(), 'Clave Ciudad')]"
        )
        locator_visible = await clave_ciudad_locator.is_visible()
        if locator_visible:
            await clave_ciudad_locator.click()

        try:
            if locator_visible:
                await self._login_clave_ciudad()
            else:
                await self._login_miba()
        except LoginError:
            try:
                if locator_visible:
                    await self._login_miba()
                else:
                    await self._login_clave_ciudad()
            except LoginError:
                raise

    async def _login_clave_ciudad(self) -> None:
        """
        Handles the Clave Ciudad login flow.
        """
        await self.page.wait_for_load_state("networkidle")
        await expect(self.page.locator("input#cuit")).to_be_visible(timeout=180000)
        await self.page.locator("input#cuit").fill(f"{self._cuit}")
        await self.page.locator("input#clave").fill(f"{self._clave_fiscal}")
        await self.page.get_by_role("button", name="Ingresar").click()
        if await self.page.locator(
            "xpath=//div[contains(@class, 'msgError')]"
        ).is_visible():
            raise LoginError(self.cliente)
        await expect(
            self.page.get_by_role("heading", name="Búsqueda de aplicativos/")
        ).to_be_visible(timeout=180000)

    async def _login_miba(self) -> None:
        """
        Handles the MIBA login flow.
        """
        await self.page.goto("https://claveciudad.agip.gob.ar/")
        await self.page.get_by_role("button", name="Iniciar sesión").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.get_by_role("button", name="Ingresar con CUIL o email").click()
        await self.page.get_by_role(
            "textbox", name="CUIL / Correo electronico *"
        ).click()
        await self.page.get_by_role("textbox", name="CUIL / Correo electronico *").fill(
            f"{self._cuit}"
        )
        await self.page.get_by_role("textbox", name="Contraseña").click()
        await self.page.locator("#password-text-field").fill(f"{self._clave_fiscal}")
        await self.page.get_by_role("button", name="Ingresar").click()
        await self.page.wait_for_load_state("networkidle")

        await self._login_miba_check_login_errors()

        await self._login_miba_handle_permissions()

    async def _login_miba_check_login_errors(self):
        """Verifica si hay errores de login y lanza LoginError si corresponde."""
        error_locators = [
            "#kc-form-login-mail",
            "#modal-error-email",
            "#error-password",
        ]
        for locator in error_locators:
            if await self.page.locator(locator).is_visible():
                raise LoginError(self.cliente)

    async def _login_miba_handle_permissions(self):
        """Maneja la confirmación de permisos si aparece el mensaje correspondiente."""
        if (
            await self.page.locator(
                "xpath=//h1[contains(@class, 'titulo') and contains(., 'Confirmá los permisos')]"
            ).is_visible()
            and await self.page.locator("#confirmar-permisos #kc-login").is_visible()
        ):
            await self.page.locator("#confirmar-permisos #kc-login").click()
            await self.page.wait_for_load_state("load")

    async def consultar_notificaciones(self):
        try:
            await self._login()

            await self.page.select_option(
                "select[name='cuit_representado']", f"{self._cuit_cliente_input}"
            )
            await self.page.type(
                'xpath=//*[@id="filtro_app"]', "Domicilio Fiscal Electrónico", delay=1
            )

            selector_servicio_dfe = (
                f"xpath=//*[@onclick='ir_servicio(54,{self._cuit_cliente_input})']"
            )

            if await self.page.is_visible(selector_servicio_dfe):
                await self.page.click(selector_servicio_dfe, timeout=5000)
            else:
                await self.page.fill('xpath=//*[@id="filtro_app"]', "")
                await self.page.type(
                    'xpath=//*[@id="filtro_app"]',
                    "Nueva Cuenta Corriente Tributaria",
                    delay=1,
                )
                await self.page.get_by_role(
                    "link", name="Nueva Cuenta Corriente"
                ).click()
                await self.page.wait_for_load_state("networkidle")
                await self.page.wait_for_selector(
                    "p.text-razonsocial", state="visible", timeout=60000
                )
                await self.page.goto("https://portal-cct.agip.gob.ar/DFE")
                await self.page.wait_for_selector(
                    "xpath=//th[contains(., 'CUIT Representado')]",
                    timeout=10000,
                    state="visible",
                )
                await self.page.wait_for_load_state("networkidle")
        except LoginError:
            # Re-lanzar errores de login directamente sin convertirlos
            raise
        except DelegacionError:
            # Re-lanzar errores de delegación directamente sin convertirlos
            raise
        except Exception as e:
            # Otros errores se convierten a ConsultarNotificacionesError
            raise ConsultarNotificacionesError(
                self.cliente, f"Error al consultar notificaciones: {str(e)}"
            ) from e

    async def buscar_notificacion(self) -> bool:
        """
        Busca notificaciones en la tabla de mensajes de AGIP.

        Retorna True si:
        1. Existe alguna fila que contenga 's/Notificar'
        2. La fecha de esa fila es posterior o igual a self.fecha_desde
        """
        await self.page.wait_for_load_state("networkidle")

        # Intentar esperar por el locator h3 durante 5 minutos
        try:
            await self.page.locator("h3:has-text('Notificaciones Recibidas')").wait_for(
                state="visible", timeout=1200000
            )
            # Si aparece, proceder con la lógica de lb.agip.gob.ar
            return await self._buscar_en_lb_agip()
        except TimeoutError:
            # Si no aparece el h3 en 5 minutos, proceder con la lógica de portal-cct
            if "//portal-cct" in self.page.url:
                return await self._buscar_en_portal_cct()
            else:
                self.logger.debug(
                    "AGIP: No se encontró el locator esperado ni portal-cct en URL"
                )
                return False

    async def _buscar_en_lb_agip(self) -> bool:
        """Busca notificaciones en la tabla de lb.agip.gob.ar."""
        try:
            # Esperar a que la tabla esté visible
            await self.page.wait_for_selector(
                "table#tablaMensajes", state="visible", timeout=30000
            )

            # Obtener todas las filas que contienen 's/Notificar'
            filas_notificar = await self.page.query_selector_all(
                "xpath=//table[@id='tablaMensajes']/tbody/tr[td[contains(text(),'s/Notificar')]]"
            )

            self.logger.debug(
                f"AGIP: Se encontraron {len(filas_notificar)} filas con 's/Notificar'"
            )

            if len(filas_notificar) == 0:
                self.logger.debug("AGIP: No hay notificaciones pendientes")
                return False

            # Convertir fecha_desde a objeto datetime
            fecha_desde = datetime.strptime(self.fecha_desde, "%d%m%Y")

            for fila in filas_notificar:
                # Obtener la fecha de la columna 2
                fecha_td = await fila.query_selector("td:nth-child(2)")
                if fecha_td:
                    fecha_texto = (await fecha_td.text_content() or "").strip()

                    try:
                        # Convertir a formato datetime (asumiendo formato 'yyyy-mm-dd')
                        fecha_notificacion = datetime.strptime(fecha_texto, "%Y-%m-%d")

                        self.logger.debug(
                            f"AGIP: Comparando fecha {fecha_notificacion} con {fecha_desde}"
                        )

                        # Comparar fechas
                        if fecha_notificacion >= fecha_desde:
                            self.logger.debug(
                                f"AGIP: Notificación encontrada con fecha {fecha_texto}"
                            )
                            return True
                    except ValueError as e:
                        self.logger.warning(
                            f"AGIP: Error al procesar fecha '{fecha_texto}': {str(e)}"
                        )

            return False
        except Exception as e:
            self.logger.error(f"AGIP: Error en _buscar_en_lb_agip: {str(e)}")
            raise BuscarNotificacionError(self.cliente)

    async def _buscar_en_portal_cct(self) -> bool:
        """Busca notificaciones en la tabla de portal-cct.agip.gob.ar."""
        try:
            await self.page.wait_for_selector(
                "xpath=//th[contains(., 'CUIT Representado')]",
                timeout=10000,
                state="visible",
            )
            await self.page.wait_for_selector(
                "xpath=//tbody/tr/td[2]", timeout=10000, state="visible"
            )

            fecha_td = await self.page.query_selector("xpath=//tbody/tr[1]/td[2]/span")
            if fecha_td:
                fecha_texto = (await fecha_td.text_content() or "").strip()

                try:
                    fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
                    fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")
                    fecha_tabla_dt = datetime.strptime(fecha_texto, "%d/%m/%Y")

                    self.logger.debug(
                        f"AGIP: Fecha en tabla {fecha_tabla_dt}, desde {fecha_desde_dt}, hasta {fecha_hasta_dt}"
                    )

                    if fecha_desde_dt <= fecha_tabla_dt <= fecha_hasta_dt:
                        self.logger.debug(
                            "AGIP: Notificación encontrada en rango de fechas"
                        )
                        return True
                    else:
                        self.logger.debug("AGIP: Fecha fuera de rango")
                        return False
                except ValueError as e:
                    self.logger.warning(
                        f"AGIP: Error al procesar fecha '{fecha_texto}': {str(e)}"
                    )
                    return False
            else:
                self.logger.debug("AGIP: No se encontró la celda de fecha en la tabla")
                return False
        except Exception as e:
            self.logger.error(f"AGIP: Error en _buscar_en_portal_cct: {str(e)}")
            raise BuscarNotificacionError(self.cliente)

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_AGIP_CLIENT")
        cuit_Agip = os.getenv("TEST_AGIP_CUIT")
        clave_fiscal_Agip = os.getenv("TEST_AGIP_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_AGIP_CUIT_CLIENTE_INPUT")

        agip = await Agip.create(
            playwright,
            client,
            cuit_Agip,
            clave_fiscal_Agip,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await agip.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
