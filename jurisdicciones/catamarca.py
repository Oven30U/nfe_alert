import os
import logging
from datetime import datetime
from typing import Optional

from playwright.async_api import Playwright, async_playwright, Page
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage

from jurisdicciones.jurisdiccion import Jurisdiccion, LoginError


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
        Consulta las notificaciones en la web de Catamarca.
        """
        await self.page.goto("https://arcat.gob.ar/")
        await self.page.get_by_role("link", name="Acceso con Clave Fiscal").click()
        await self.page.get_by_role("spinbutton").click()
        await self.page.get_by_role("spinbutton").fill("20412371667")
        await self.page.get_by_role("button", name="Siguiente").click()
        await self.page.get_by_role("textbox", name="TU CLAVE").fill("FC!t@X.1BB8!")
        await self.page.get_by_role("button", name="Ingresar").click()
        async with self.page.expect_popup() as page1_info:
            await self.page.get_by_role("button", name="Domicilio Fiscal").click()
            page1 = await page1_info.value
            # Usar la nueva pestaña como la página activa para los siguientes pasos
            self.page = page1
            await page1.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        """
        Determinar si hay notificaciones.

        Reglas:
        - Si aparece 'No se encontraron novedades' y 'Ud. no tiene Notificaciones' -> False
        - Si aparece un texto que contiene 'No Leídas' y el número asociado es 0 -> False
        - Si 'No Leídas' contiene un número distinto de 0 -> True
        - En ausencia de los mensajes negativos, asumimos que hay notificaciones -> True
        """
        # Mensajes explícitos que indican ausencia de novedades y notificaciones
        if await self.page.is_visible(
            "text=No se encontraron novedades"
        ) and await self.page.is_visible("text=Ud. no tiene Notificaciones"):
            return False

        # Buscar cantidad de 'No Leídas' != 0.
        try:
            import re

            try:
                html = await self.page.content()
            except Exception:
                html = ""

            m = re.search(r"No\s*Leídas\s*[:\|\-]?\s*(\d+)", html, re.IGNORECASE)
            if m:
                return int(m.group(1)) != 0

        except Exception:
            pass

        # Si no se detectan los mensajes negativos, asumimos que hay notificaciones
        return True

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    async def main():
        async with async_playwright() as playwright:
            fecha_desde = os.getenv("FECHA_DESDE")
            fecha_hasta = os.getenv("FECHA_HASTA")

            client = os.getenv("TEST_CATAMARCA_CLIENT")
            cuit_Catamarca = os.getenv("TEST_CATAMARCA_CUIT")
            clave_fiscal_Catamarca = os.getenv("TEST_CATAMARCA_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_CATAMARCA_CUIT_CLIENTE_INPUT")

            catamarca = await Catamarca.create(
                playwright,
                client,
                cuit_Catamarca,
                clave_fiscal_Catamarca,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await catamarca.procesar_jurisdiccion()

    asyncio.run(main())
