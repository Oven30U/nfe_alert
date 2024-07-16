import asyncio
from datetime import datetime
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
            await self.page.fill('xpath=//*[@id="filtro_app"]', "Domicilio Fiscal Electrónico", timeout=90000)

            try:
                # if await self.page.wait_for_selector(f"xpath=//*[@onclick='ir_servicio(54,{self._cuit_cliente_input})']", timeout=900000):
                await self.page.click(f"xpath=//*[@onclick='ir_servicio(54,{self._cuit_cliente_input})']", timeout=5000)
            except Exception as e:
                # else:
                # Si el selector del servicio no se encuentra, hacer click en el DFE de arriba
                await self.page.click("xpath=//*[@onclick='ir_servicio(54, 0)']", timeout=900000)
                # Clickear en Representados
                await self.page.wait_for_selector(f"xpath=//li[@id='opRepresentados']//a[@class='dropdown-toggle']",
                                                  timeout=900000)
                await self.page.click(f"xpath=//li[@id='opRepresentados']//a[@class='dropdown-toggle']", timeout=900000)
                # Seleccionar el DFE del CUIT representado
                await self.page.wait_for_selector(f"a[data-id='{self._cuit_cliente_input}']", timeout=900000)
                await self.page.click(f"xpath=//*[a[@data-id={self._cuit_cliente_input}]]", timeout=900000)
            finally:
                await self.page.wait_for_selector("xpath=//button[@class='btnNoLeidas btn btn-default']",
                                                  timeout=900000)
                await self.page.click(
                    "xpath=//button[@class='btnNoLeidas btn btn-default']", timeout=900000
                )  # 15 min
        except Exception as e:
            raise ConsultarNotificacionesError(
                f"Error al consultar notificaciones: {str(e)}", self.cliente
            )

    async def buscar_notificacion(self):
        return await super().buscar_notificacion(self.page, texto="s/Notificar")
        # hay_notificaciones_sin_leer = await super().buscar_notificacion(self.page, texto="---")
        # if hay_notificaciones_sin_leer:
        #     # Esperar a que la tabla esté visible
        #     await self.page.wait_for_selector('table#tablaMensajes', state='visible')
        #     # Obtener todas las filas de la tabla
        #     filas = await self.page.query_selector_all('table#tablaMensajes > tbody > tr')
        #     # Iterar sobre cada fila
        #     for fila in filas:
        #         # Obtener el tercer td de la fila actual
        #         tercer_td = await fila.query_selector('td:nth-child(3)')
        #         # Obtener el texto del tercer td
        #         fecha_notificado = await tercer_td.text_content()
        #         # Realizar análisis o acción deseada con el fecha_notificado
        #         if fecha_notificado == "---":
        #             return True
        #         fecha_desde = datetime.strptime(self.fecha_desde, '%d%m%Y')
        #         fecha_notificado_date = datetime.strptime(fecha_notificado, '%Y-%m-%d')
        #         if fecha_notificado_date > fecha_desde:
        #             return True
        #     return False

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = "01052024"
        fecha_hasta = "30052024"

        # client = "ABBOTT LABORATORIES ARG. S.A"
        # cuit_Agip = "27262736364"
        # clave_fiscal_Agip = "Cambio2020"
        # cuit_cliente_input = "30500846301"

        # client = "EDGE ARGENTINA S.R.L"
        # cuit_Agip = "20236063586"
        # clave_fiscal_Agip = "Bart41051"
        # cuit_cliente_input = "30714604356"

        client = "NATURA COSMETICOS S.A"
        cuit_Agip = "20937892692"
        clave_fiscal_Agip = "Natura1860"
        cuit_cliente_input = "30677757295"

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
