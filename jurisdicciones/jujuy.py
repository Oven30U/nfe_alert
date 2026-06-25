from datetime import datetime

from playwright.async_api import Playwright

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


class Jujuy(Jurisdiccion):
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
            "Jujuy",
            "910 JUJUY",
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

    async def formatear_fechas(self, fecha):
        # Convierte las posiciones a quitar en un conjunto para un acceso más eficiente
        posiciones_set = set({4, 5})
        # Utiliza una comprensión de cadena para construir la cadena resultante
        fecha_formateada = "".join(
            caracter for i, caracter in enumerate(fecha) if i not in posiciones_set
        )
        return fecha_formateada

    async def consultar_notificaciones(self):
        # while True:
        await self.page.goto("https://www.rentasjujuyonline.gob.ar/")
        await self.page.wait_for_load_state("networkidle")
        await self.page.fill("#vUSUID", self._cuit)
        await self.page.fill("#vCONTRING", self._clave_fiscal)
        await self.page.click("#vBTN_INGRESAR")
        await self.page.wait_for_load_state("networkidle")
        incorrect_login = self.page.locator(
            'xpath=//div[text()="Verifique el Usuario-Contraseña ingresados!"]'
        )
        if await incorrect_login.count() > 0:
            raise LoginError(self.cliente)

        await self.page.locator('text="DOMICILIO FISCAL ELECTRONICO"').wait_for(
            state="visible", timeout=60000
        )
        await self.page.goto(
            "https://www.rentasjujuyonline.gob.ar/cedulavirtual/HCon_NotDFEwwRes.aspx"
        )
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator(
            'text="NOTIFICACIONES DE DOMICILIO FISCAL ELECTRONICO"'
        ).wait_for(state="visible", timeout=60000)
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        await self.page.wait_for_load_state("networkidle")
        await self.page.locator("table#Grid1ContainerTbl").wait_for(
            state="visible", timeout=60000
        )
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_load_state("load")
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_selector(
            "table#Grid1ContainerTbl", state="visible", timeout=60000
        )

        self.hay_notificaciones = False

        fecha_columna = await self.page.locator(
            'xpath=//table[@id="Grid1ContainerTbl"]//tbody//tr[1]/td[7]'
        ).inner_text()
        fecha_columna = datetime.strptime(fecha_columna, "%d/%m/%Y")
        fecha_desde = datetime.strptime(self.fecha_desde, "%d%m%Y")

        # Verificar si la notificación ya fue leída (columna 9 - Fecha Leído)
        fecha_leido_element = self.page.locator(
            'xpath=//table[@id="Grid1ContainerTbl"]//tbody//tr[1]/td[9]'
        )
        fecha_leido_text = await fecha_leido_element.inner_text()
        
        # Si hay una fecha en la columna "Fecha Leído", verificar si es menor a hoy
        if fecha_leido_text and fecha_leido_text.strip():
            try:
                fecha_leido = datetime.strptime(fecha_leido_text.strip(), "%d/%m/%Y")
                fecha_hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Si la fecha de lectura es menor a hoy, la notificación ya fue procesada
                if fecha_leido < fecha_hoy:
                    return False
            except ValueError:
                # Si no se puede parsear la fecha, continuar con la validación normal
                pass

        if fecha_columna > fecha_desde:
            self.hay_notificaciones = True

        return self.hay_notificaciones

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
