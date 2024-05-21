import asyncio
from datetime import datetime
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion, LoginError


class Jujuy(Jurisdiccion):
    @classmethod
    async def create(
        cls,
        playwright: Playwright,
        cliente,
        cuit,
        clave_fiscal,
        fecha_desde,
        fecha_hasta,
        cuit_cliente_input,
    ):
        self = await super().create(
            playwright,
            "Jujuy",
            "910 JUJUY",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
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
        while True:
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
                raise LoginError("Login CUIT incorrecto", self.cliente)

            while True:
                await self.page.wait_for_load_state("networkidle")
                title = await self.page.title()
                if title == "Inicio":
                    break

            await self.page.wait_for_load_state("networkidle")

            title = await self.page.title()
            if title != "Página de Autenticación":
                break

        await self.page.goto(
            "https://www.rentasjujuyonline.gob.ar/cedulavirtual/HCon_NotDFEwwRes.aspx"
        )
        await self.page.wait_for_load_state("networkidle")
        await self.page.fill(
            "#vFECDESDE", await self.formatear_fechas(self.fecha_desde)
        )
        await self.page.fill(
            "#vFECHASTA", await self.formatear_fechas(self.fecha_hasta)
        )
        await self.page.click("#IMAGE1")  # boton de buscar
        await self.page.wait_for_load_state("networkidle")

    async def buscar_notificacion(self):
        filas_de_notificaciones = await self.page.query_selector(
            'xpath=//*[@id="Grid1ContainerTbl"]/tbody/tr'
        )
        self.hay_notificaciones = filas_de_notificaciones is not None
        return self.hay_notificacion

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "EDGE ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Jujuy = "30714604356"
        clave_fiscal_Jujuy = "Edge2021!"
        cuit_cliente_input = "30714604356"
        jujuy = await Jujuy.create(
            playwright,
            client,
            cuit_Jujuy,
            clave_fiscal_Jujuy,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await jujuy.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
