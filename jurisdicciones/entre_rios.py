from playwright.async_api import Playwright, Page, TimeoutError as PlaywrightTimeoutError

from jurisdicciones.jurisdiccion import Jurisdiccion, DelegacionError


class EntreRios(Jurisdiccion):
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
        slow_mo=0,
        browser=None,
        context=None,
        page=None,
    ):
        self = await super().create(
            playwright,
            "EntreRios",
            "908 ENTRE RIOS",
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
            slow_mo=slow_mo,
            browser=browser,
            context=context,
            page=page,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    # Existing methods...
    async def AFIP_login(self, success_selector: str = None):
        return await super().AFIP_login(success_selector=success_selector)

    async def formatear_cuit(self, cuit):
        """
        Esta función formatea un número de CUIT 20386165476 al formato 20-38616547-6.

        Args:
        cuit: El número de CUIT a formatear.

        Returns:
        El número de CUIT formateado.
        """
        # Convertir el número de CUIT a una cadena.
        cuit_str = str(cuit)
        # Insertar un guión después del segundo dígito.
        cuit_str = cuit_str[:2] + "-" + cuit_str[2:]
        # Insertar un guión después del décimo dígito.
        cuit_str = cuit_str[:11] + "-" + cuit_str[11:]
        # Devolver el número de CUIT formateado.
        return cuit_str

    async def consultar_notificaciones(self):
        await self.AFIP_login(success_selector="input#buscadorInput")
        await self.page.fill(
            "input#buscadorInput", "Servicios Administradora Tributaria de Entre Ríos"
        )
        await self.page.click("a.dropdown-item")
        popup_info = await self.page.wait_for_event("popup")
        self.new_page: Page = popup_info
        await self.new_page.wait_for_load_state("networkidle")

        # Si aparece el botón de cerrar modal, darle click
        if await self.new_page.is_visible("button.close[data-dismiss='modal']"):
            await self.new_page.click("button.close[data-dismiss='modal']")

        cuit_contribuyente = await self.formatear_cuit(self._cuit_cliente_input)

        try:
            await self.new_page.locator(
                f"xpath=//*[contains(text(), '{cuit_contribuyente}')]"
            ).click()
        except PlaywrightTimeoutError as e:
            raise DelegacionError(self.cliente) from e

        await self.new_page.wait_for_load_state("load")
        await self.new_page.wait_for_load_state("domcontentloaded")
        await self.new_page.wait_for_load_state("networkidle")

        # Esperar por el botón de cerrar modal hasta 5 segundos y darle click si aparece
        try:
            await self.new_page.wait_for_selector(
                "button.close[data-dismiss='modal']", timeout=10000
            )
            await self.new_page.click("button.close[data-dismiss='modal']")
        except Exception:
            pass

        await self.new_page.goto(
            "https://portal.ater.gob.ar/ventanillaVirtual/adhesionVentanilla.aspx"
        )
        await self.new_page.wait_for_load_state("load")

    async def buscar_notificacion(self):
        await self.new_page.wait_for_load_state("networkidle")

        await self.new_page.locator("i.fa.fa-caret-down").click()
        await self.new_page.locator("li[data-range-key='Últimos 30 días']").click()

        # Obtener los valores de cantidad_avisos y cantidad_notificaciones
        cantidad_avisos = (await self.new_page.locator("#avisos").inner_text()).strip(
            "()"
        )
        cantidad_notificaciones = (
            await self.new_page.locator("#notificaciones").inner_text()
        ).strip("()")
        total_notificaciones = int(cantidad_avisos) + int(cantidad_notificaciones)
        self.hay_notificacion = total_notificaciones > 0
        return self.hay_notificacion

    async def tomar_screenshot(self):
        """Tomar dos screenshot's en la jurisdicción de Entre Rios."""
        secciones = [
            ("notificaciones", "a.nav-link.notificaciones"),
            ("avisos", "a.nav-link.avisos"),
        ]
        self.hay_screenshot = await super().tomar_varias_screenshots(
            secciones, self.new_page
        )
        return self.hay_screenshot

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
