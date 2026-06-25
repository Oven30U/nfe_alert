from playwright.async_api import Playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Chaco(Jurisdiccion):
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
        headless=False,
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
        headless=False,
    ):
        self = await super().create(
            playwright,
            "Chaco",
            "906 CHACO",
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
        return self

    async def verificar_errores_login(self):
        if await self.page.is_visible("text=Contribuyente no habilitado"):
            raise LoginError(self.cliente, "Contribuyente no habilitado")
        if await self.page.is_visible("text=Ingrese su nueva Clave Fiscal"):
            raise LoginError(self.cliente, LoginError.CREDENCIALES_EXPIRADAS)
        if await self.page.is_visible("text=Clave Fiscal incorrecta"):
            raise LoginError(self.cliente, LoginError.CREDENCIALES_EXPIRADAS)

    async def consultar_notificaciones(self):
        await self.page.goto(
            "https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/iniciocontribuyente",
            wait_until="networkidle",
        )
        await self.page.goto(
            "https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/iniciocontribuyente",
            wait_until="networkidle",
        )
        await self.page.locator("#vCONCUIT").fill(f"{self._cuit}")
        await self.page.locator("#vCONTRASENA").fill(f"{self._clave_fiscal}")
        await self.page.locator("//input[@name='BUTTON1']").click()
        await self.verificar_errores_login()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_load_state("load")
        await self.page.locator("//input[@name='BTNACEPTAR']").click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_load_state("load")
        await self.page.goto(
            "https://atp-lb1.ecomchaco.com.ar/ATPWeb/servlet/notifica_miventanillaelectronicaadj?",
            wait_until="networkidle",
        )
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        await self.page.is_visible("text=Avisos - Mi Ventanilla Electrónica") #! TODO: Consultar si hay error de delegacion si no se ve
        filas = await self.page.locator(
            "//table[@id='Grid1ContainerTbl']//tbody//tr"
        ).all()
        return True if filas else False

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
