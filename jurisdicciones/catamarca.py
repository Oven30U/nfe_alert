import re
from typing import Optional

from playwright.async_api import Playwright, Page

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError, DelegacionError


class Catamarca(Jurisdiccion):
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
        browser: Optional[object] = None,
        context: Optional[object] = None,
        page: Optional[Page] = None,
    ):
        # Propagar browser/context/page a super().create para reutilizar el contexto
        self = await super().create(
            playwright,
            "Catamarca",
            "903 CATAMARCA",
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
            page=page,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def consultar_notificaciones(self) -> None:
        """
        Consulta las notificaciones en la web de Catamarca usando el login centralizado.
        """
        URL_AFIP_CATAMARCA_LOGIN = "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=arca_dgr_contrib"
        await super().AFIP_login(
            URL_AFIP_LOGIN=URL_AFIP_CATAMARCA_LOGIN,
            success_url="https://dgrentas.arcat.gob.ar/",
        )
        await self.page.wait_for_selector("#vPERSONAID")

        representado_pattern: str = rf"^\s*{re.escape(self._cuit_cliente_input)}\b"
        options = self.page.locator("#vPERSONAID option")
        count = await options.count()
        selected = False
        for i in range(count):
            opt = options.nth(i)
            try:
                text = (await opt.inner_text() or "").strip()
            except Exception:
                text = ""
            if re.search(representado_pattern, text):
                value = await opt.get_attribute("value")
                if value is not None:
                    await self.page.locator("#vPERSONAID").select_option(value=value)
                else:
                    await self.page.locator("#vPERSONAID").select_option(label=text)
                selected = True
                break
        if not selected:
            # Si no se encuentra la opción para el CUIT del cliente, levantar LoginError indicando delegación pendiente
            raise DelegacionError(self.cliente)
        await self.page.get_by_role("button", name="Domicilio Fiscal").click()
        # Esperar a que se abra la nueva pestaña y usarla como la página activa
        async with self.page.expect_popup() as page1_info:
            pass  # El click anterior debería disparar el popup
        page1 = await page1_info.value
        self.page = page1
        await page1.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        """
        Determinar si hay notificaciones.

        Reglas:
        - Si aparece 'No se encontraron novedades' y 'Ud. no tiene Notificaciones' -> False
        - Si aparece un texto que contiene 'No Leídas' y el número asociado es 0 -> False
        - Si 'No Leídas' contiene un número distinto de 0 y la fecha de //tr[1]//td[2] está en el rango -> True
        - En ausencia de los mensajes negativos, asumimos que hay notificaciones -> True
        """
        # Mensajes explícitos que indican ausencia de novedades y notificaciones
        if await self.page.is_visible(
            "text=No se encontraron novedades"
        ) and await self.page.is_visible("text=Ud. no tiene Notificaciones"):
            return False

        try:
            import re
            from datetime import datetime

            try:
                html = await self.page.content()
            except Exception:
                html = ""

            m = re.search(r"No\s*Leídas\s*[:\|\-]?\s*(\d+)", html, re.IGNORECASE)
            if m:
                no_leidas = int(m.group(1))
                if no_leidas == 0:
                    return False
                # Si hay no leídas, analizar la fecha de la primera notificación
                # Extraer la fecha de //tr[1]//td[2]
                try:
                    fecha_str = await self.page.locator("//tr[1]//td[2]").inner_text()
                    fecha_str = fecha_str.strip()
                    # Convertir self.fecha_desde y self.fecha_hasta de ddmmYYYY a datetime
                    fecha_desde = datetime.strptime(self.fecha_desde, "%d%m%Y")
                    fecha_hasta = datetime.strptime(self.fecha_hasta, "%d%m%Y")
                    # Convertir fecha_str de dd-mm-YYYY a datetime
                    fecha_notif = datetime.strptime(fecha_str, "%d-%m-%Y")
                    if fecha_desde <= fecha_notif <= fecha_hasta:
                        return True
                    else:
                        return False
                except Exception:
                    # Si no se puede extraer la fecha, asumimos que hay notificación
                    return True

        except Exception:
            pass

        # Si no se detectan los mensajes negativos, asumimos que hay notificaciones
        return True

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()
