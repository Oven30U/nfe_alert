import asyncio
from playwright.async_api import Playwright, async_playwright, expect
from jurisdiccion import Jurisdiccion, LoginError, ConsultarNotificacionesError


class Agip(Jurisdiccion):
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
            "Agip",
            "901 CABA",
            cliente,
            cuit,
            clave_fiscal,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self

    async def consultar_notificaciones(self):
        try:
            await self.page.goto("https://claveciudad.agip.gob.ar/")
            await self.page.fill('xpath=//*[@id="cuit"]', f"{self._cuit}")
            await self.page.fill('xpath=//*[@id="clave"]', f"{self._clave_fiscal}")
            await self.page.click("xpath=//a[normalize-space()='Ingresar']")
            await self.page.wait_for_load_state("load")
            if await self.page.is_visible("text=Clave/Usuario incorrecto."):
                raise LoginError("CUIT no registrado", self.cliente)
            await self.page.select_option(
                "select[name='cuit_representado']", f"{self._cuit_cliente_input}"
            )
            await self.page.click(
                f"xpath=//*[@onclick='ir_servicio(54,{self._cuit_cliente_input})']"
            )
            await self.page.click(
                "xpath=//*[@class='btnNoLeidas btn btn-default']", timeout=900000
            )  # 15 min
        except Exception as e:
            raise ConsultarNotificacionesError(
                f"Error al consultar notificaciones: {str(e)}", self.cliente
            )

    async def buscar_notificacion(self):
        return await super().buscar_notificacion(self.page, texto="---")

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        client = "FACEBOOK ARGENTINA S.R.L"
        fecha_desde = "01052024"
        fecha_hasta = "30052024"
        cuit_Agip = "20236063586"
        clave_fiscal_Agip = "Bart41051"
        cuit_cliente_input = "30712132554"
        agip = await Agip.create(
            playwright,
            client,
            cuit_Agip,
            clave_fiscal_Agip,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
        )
        await agip.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
