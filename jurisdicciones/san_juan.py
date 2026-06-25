from datetime import datetime

from playwright.async_api import Playwright, Page, TimeoutError as PlaywrightTimeoutError

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError, DelegacionError


class SanJuan(Jurisdiccion):
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
        self._cuit = int(str(self._cuit)[2:-1])  # ? Saco el DNI unicamente del cuit

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
            "SanJuan",
            "918 SAN JUAN",
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

    async def consultar_notificaciones(self):
        async def iniciar_sesion_san_juan(page: Page):
            await page.goto("https://rentas.dgrsj.gob.ar/", wait_until="load")
            # await page.locator("(//button[contains(text(),'Iniciar Sesión')])[2]").click()
            # await page.locator("(//span[contains(text(),'Iniciar con CID')])[2]").click()
            # await page.wait_for_selector("#CuitCUR", state="visible")
            # await page.locator("#CuitCUR").fill(f"{self._cuit}")
            # await page.wait_for_selector("#PassCUR", state="visible")
            # await page.locator("#PassCUR").fill(f"{self._clave_fiscal}")
            # await page.wait_for_selector("#btnFormValidarCur", state="visible")
            # await page.wait_for_load_state("networkidle")
            # await page.locator("#btnFormValidarCur").click()
            await page.get_by_role("button", name="Iniciar Sesión").click()
            await page.get_by_role("link", name="Iniciar con CIDI").click()
            await page.locator("//input[@placeholder='D.N.I.']").wait_for(timeout=5000)
            await page.get_by_placeholder("D.N.I.").click()
            await page.get_by_placeholder("D.N.I.").fill(f"{self._cuit}")
            await page.locator("//input[contains(@id,'clave')]").wait_for(timeout=5000)
            await page.get_by_placeholder("Clave").click()
            await page.get_by_placeholder("Clave").fill(f"{self._clave_fiscal}")
            await page.get_by_role("combobox").select_option("F")
            await page.wait_for_load_state("networkidle")
            await page.get_by_role("button", name="Iniciar Sesión").click()

            if await page.is_visible(
                "//label[contains(.,'El usuario no se ha logueado correctamente.')]",
                timeout=5000,
            ):
                await page.get_by_role("combobox").select_option("M")
                await page.wait_for_load_state("networkidle")
                await page.get_by_role("button", name="Iniciar Sesión").click()
            if await page.is_visible(
                "//label[contains(.,'El usuario no se ha logueado correctamente.')]",
                timeout=5000,
            ):
                await page.get_by_role("combobox").select_option("X")
                await page.wait_for_load_state("networkidle")
                await page.get_by_role("button", name="Iniciar Sesión").click()

        await iniciar_sesion_san_juan(self.page)
        retry_limit = 3
        retries = 0
        # while await self.page.is_visible("//span[contains(text(), 'ValiRdar CU')]") and retries < retry_limit:
        while (
            await self.page.is_visible(
                "//label[contains(.,'El usuario no se ha logueado correctamente.')]"
            )
            and retries < retry_limit
        ):
            await iniciar_sesion_san_juan(self)
            retries += 1

        if (
            # await  self.page.is_visible("text=El N° de CUIT no es válido")
            await self.page.is_visible(
                "//label[contains(.,'El usuario no se ha logueado correctamente.')]"
            )
        ):
            raise LoginError(self.cliente)

        await self.page.wait_for_load_state("networkidle")
        await self.page.locator(
            "(//button[contains(@class,'btn btn-primary bg-primary dropdown-toggle-split dropdown-toggle text-white')])[2]"
        ).click()

        try:
            await self.page.locator(f"a:has(.text-muted:has-text('{self.cuit_cliente_input}')):visible").click()
        except PlaywrightTimeoutError as e:
            raise DelegacionError(self.cliente) from e

        if await self.page.is_visible(
            "//button[contains(@id,'btnMensajeAceptar')]", timeout=5000
        ):
            await self.page.get_by_text("Ver Notificaciones").click()
        await self.page.goto(
            "https://rentas.dgrsj.gob.ar/DatosContribuyente/EDomicilioFiscal"
        )

    async def buscar_notificacion(self):
        await self.page.locator("//table[@id='dtDetalleDeNotificaciones']").wait_for(
            state="visible"
        )
        cells = await self.page.locator(
            "//table[@id='dtDetalleDeNotificaciones']//tbody//tr/td[4]"
        ).all()
        fecha_desde_dt = datetime.strptime(self.fecha_desde, "%d%m%Y")
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, "%d%m%Y")
        for cell in cells:
            text = await cell.inner_text()
            try:
                cell_date = datetime.strptime(text, "%d/%m/%Y %H:%M")
                if fecha_desde_dt <= cell_date <= fecha_hasta_dt:
                    return True
            except ValueError:
                continue
        return False

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
