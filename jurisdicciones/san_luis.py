from playwright.async_api import Playwright, TimeoutError as PlaywrightTimeoutError

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError, DelegacionError


class SanLuis(Jurisdiccion):
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
            "SanLuis",
            "919 SAN LUIS",
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

    async def consultar_notificaciones(self):
        await self.page.goto(
            "https://sistematributario.dpip.sanluis.gov.ar/ords/clavefiscal/r/miclave/login"
        )
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("//input[@id='P101_USERNAME']").fill(f"{self._cuit}")
        await self.page.locator("//input[@name='P101_PASSWORD']").fill(
            f"{self._clave_fiscal}"
        )
        await self.page.locator("button:has(span:text('Conectar'))").first.click()
        await self.page.wait_for_load_state("networkidle")
        if await self.page.is_visible("text=Credenciales de conexión no válidas"):
            raise LoginError(self.cliente)
        await self.page.wait_for_load_state("networkidle")

        try:
            await self.page.locator(
                f"//td[b[contains(text(), '{self._cuit_cliente_input}')]]/following-sibling::td//button"
            ).click()
        except PlaywrightTimeoutError as e:
            raise DelegacionError(self.cliente) from e

        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        if await self.page.is_visible(
            "h2.t-Region-title:has-text('Notificaciones recibidas')"
        ):
            return True

        await self.page.wait_for_selector(
            "//a[div[h3[contains(text(), 'Buzón Electrónico')]]]"
        )
        await self.page.locator(
            "//a[div[h3[contains(text(), 'Buzón Electrónico')]]]"
        ).click()
        await self.page.wait_for_load_state("load")
        iframe = self.page.frame_locator(
            "iframe[src*='/ords/clavefiscal/r/miclave/notificaciones-domicilio-electr%C3%B3nico1']"
        )
        await self.page.wait_for_load_state("load")
        await iframe.locator("//input[@id='P11_FECHA_DESDE']").fill(
            f"{self.fecha_desde}"
        )
        await iframe.locator("//input[@id='P11_FECHA_HASTA']").fill(
            f"{self.fecha_hasta}"
        )
        await iframe.locator("select#P11_ESTADO").select_option("ENVIADA")
        await iframe.locator("//div//button[span[contains(text(), 'Buscar')]]").click()
        await self.page.wait_for_load_state("networkidle")
        iframe = self.page.frame_locator(
            "iframe[src*='/ords/clavefiscal/r/miclave/notificaciones-domicilio-electr%C3%B3nico1']"
        )
        await iframe.locator(
            "//span[contains(text(),'No se han encontrado datos para mostrar')]"
        ).wait_for(state="visible", timeout=10000)

        # Check if 'no data' message is visible
        no_data_visible = await iframe.locator(
            "//span[contains(text(),'No se han encontrado datos para mostrar')]"
        ).is_visible()

        if not no_data_visible:
            # Optional: Confirm presence of actual data (e.g., table rows)
            data_rows = iframe.locator("//table//tbody//tr")
            return await data_rows.count() > 0

        return False

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
