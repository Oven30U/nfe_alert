from playwright.async_api import Playwright, async_playwright
from datetime import datetime
from jurisdicciones.jurisdiccion import Jurisdiccion


class Nacional(Jurisdiccion):
    @classmethod
    async def create(
            cls,
            playwright: Playwright,
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input=None,
    ):
        # Convertir las fechas al formato dd/mm/yyyy
        fecha_desde = datetime.strptime(fecha_desde, "%d%m%Y").strftime("%d/%m/%Y")
        fecha_hasta = datetime.strptime(fecha_hasta, "%d%m%Y").strftime("%d/%m/%Y")
        self = await super().create(
            playwright,
            "Nacional",
            "Nacional",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
        )

        self.cuit_cliente_input = str(cuit_cliente_input)
        self.hay_screenshots_filtrados = False
        return self

    async def AFIP_login(
            self, URL_AFIP_LOGIN="https://auth.afip.gob.ar/contribuyente_/login.xhtml"
    ):
        return await super().AFIP_login(URL_AFIP_LOGIN)

    async def consultar_notificaciones(self):
        await self.AFIP_login()
        await self.page.fill("input#buscadorInput", "Domicilio Fiscal Electrónico")
        # Click en la opción de DFE desplegada
        await self.page.click("a.dropdown-item")
        popup_info = await self.page.wait_for_event("popup")
        self.new_page = popup_info
        await self.new_page.wait_for_load_state("networkidle")
        # await self.new_page.wait_for_selector('text="Recordar más tarde"')
        await self.new_page.click('text="Recordar más tarde"')
        await self.new_page.click('text=" Comunicaciones de mis representados "')
        # await self.new_page.click("#d-select-81")
        await self.new_page.click("(//div[@class='input-group'])[5]//div[@class='form-control dropdown-toggle']")
        await self.new_page.click(f'xpath=//button[@id="{self.cuit_cliente_input}"]')
        await self.page.wait_for_load_state("networkidle")
        try:
            await self.new_page.wait_for_selector('text="Cerrar"', timeout=2000)
            await self.new_page.click('text="Cerrar"')
        except Exception:
            pass
        # await self.new_page.fill("xpath=(//input)[5]", f"{self.fecha_desde}")
        await self.new_page.fill("xpath=(//label[contains(text(), 'Desde')]/following::input[1])[2]",
                                 f"{self.fecha_desde}")
        # await self.new_page.fill("xpath=(//input)[6]", f"{self.fecha_hasta}") #\t\n
        await self.new_page.fill("xpath=(//label[contains(text(), 'Hasta')]/following::input[1])[2]",
                                 f"{self.fecha_hasta}")  # \t\n
        await self.new_page.locator('//button[contains(text(), "Aplicar")]').nth(1).click()
        # await self.new_page.keyboard.press("Tab")
        # await self.new_page.keyboard.press("Enter")

        # async def completar_fechas(page, fecha_desde, fecha_hasta):
        # await self.page.fill("xpath=(//input)[5]", f"{self.fecha_desde}")
        # await self.page.fill("xpath=(//input)[6]", f"{self.fecha_hasta}")
        # await self.page.wait_for_load_state("networkidle")
        # await self.page.keyboard.press("Tab")
        # await self.page.keyboard.press("Enter")
        # await self.page.wait_for_load_state("networkidle")
        await self.new_page.select_option("select[name='filtroEstado']", "No Leída")

        # await completar_fechas(self.new_page, self.fecha_desde, self.fecha_hasta)

    async def buscar_notificacion(self):
        selectores = {
            "notificaciones": "xpath=//a[contains(text(), ' Notificaciones ')]",
            "requerimientos": "xpath=//a[contains(text(), ' Requerimientos ')]",
            "otras_notificaciones": "xpath=//a[contains(text(), ' Otras notificaciones ')]",
            "fce": "xpath=//a[contains(text(), ' Factura de Crédito Electrónica ')]"
        }
        contador_filtro_hay_notificacion = 0
        todos_screenshots_exitosos = True
        selectores_validos = 0

        for clave, selector in selectores.items():
            try:
                await self.new_page.click(selector)
                await self.new_page.wait_for_load_state("networkidle")
                selectores_validos += 1
            except Exception:
                continue

            no_hay_notificaciones = await super().buscar_notificacion(self.new_page, "No hay comunicaciones para mostrar")

            if not no_hay_notificaciones:
                contador_filtro_hay_notificacion += 1

            screen_estado = await self.tomar_screenshot_filtrado(clave)
            if not screen_estado:
                todos_screenshots_exitosos = False

        self.hay_screenshots_filtrados = todos_screenshots_exitosos
        return True if contador_filtro_hay_notificacion > 0 else False

    async def tomar_screenshot_filtrado(self, tipo_notificacion) -> bool:
        self.fecha_desde = self.fecha_desde.replace("/", "")
        self.fecha_hasta = self.fecha_hasta.replace("/", "")
        while True:
            # Primer Screenshot
            await super().tomar_screenshot(self.new_page, nombre_extra=tipo_notificacion)

            # Contar la cantidad de elementos <tr> dentro del selector especificado
            selector_notificaciones = "//div[@class='tab-pane active card-body']//tbody[@role='rowgroup']/tr"
            cantidad_notificaciones = await self.new_page.locator(selector_notificaciones).count()

            # Sólo si hay 7 o más notificaciones continuo tomando screenshots
            if cantidad_notificaciones >= 7:
                # Scroll hasta la última notificación
                selector_ultima_notificacion = "(//div[@class='tab-pane active card-body']//tr)[last()]"
                await self.new_page.evaluate("""
                    (selector) => {
                        document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.scrollIntoView();
                    }
                """, selector_ultima_notificacion)

                # Segundo Screenshot
                await super().tomar_screenshot(self.new_page, nombre_extra=tipo_notificacion)

            # Verificar si hay más páginas, si hay -> navegar a la próxima y repetir
            selector_flecha_siguiente = "(//button[@role='menuitem'])[4]"
            clases_flecha_siguiente = await self.new_page.get_attribute(selector_flecha_siguiente, "class")
            if "disabled" in clases_flecha_siguiente:
                return True
            await self.new_page.click(selector_flecha_siguiente)

            # Scroll hasta la primera notificación
            selector_primera_notificacion = "(//div[@class='tab-pane active card-body']//tr)[1]"
            await self.new_page.evaluate("""
                (selector) => {
                    document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.scrollIntoView();
                }
            """, selector_primera_notificacion)

    async def tomar_screenshot(self):
        return self.hay_screenshots_filtrados

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        # client = "EDGE ARGENTINA S.R.L"
        # cuit_cliente_input = "30714604356"
        client = "FACEBOOK ARGENTINA S.R.L"
        cuit_cliente_input = "30712132554"

        clave_fiscal_Nacional = "Gabriel1994"
        cuit_Nacional = "20386165476"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"

        nacional = await Nacional.create(
            playwright,
            client,
            cuit_Nacional,
            clave_fiscal_Nacional,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await nacional.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
