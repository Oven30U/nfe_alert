from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import (ConsultarNotificacionesError,
                                         Jurisdiccion, LoginError)


class Agip(Jurisdiccion):
    def __init__(self, nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input=None, razon_social_cliente_input=None, texto_notificacion=None, headless=True):
        super().__init__(nombre, codigo, cliente, cuit, clave_fiscal, fecha_desde, fecha_hasta, cuit_cliente_input, razon_social_cliente_input, texto_notificacion, headless)
        self.cuit_cliente_input = str(cuit_cliente_input)

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
            razon_social_cliente_input=None,
            texto_notificacion=None,
            headless=True
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
            razon_social_cliente_input,
            texto_notificacion,
            headless=headless
        )
        self.cuit_cliente_input = str(cuit_cliente_input)
        return self
    async def consultar_notificaciones(self):
        try:
            await self.page.goto("https://claveciudad.agip.gob.ar/", timeout=1200000)
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
                boton_filtro = "xpath=//button[@class='btnNoLeidas btn btn-default']" # no_leidas
                # boton_filtro = "xpath=//button[@class='btnSinNotificar btn btn-default']" # sin_notificar
                await self.page.wait_for_selector(boton_filtro,
                                                  timeout=900000)
                await self.page.click(
                    boton_filtro, timeout=900000
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

        client = "ABBOTT LABORATORIES ARG. S.A"
        cuit_Agip = "27262736364"
        clave_fiscal_Agip = "Cambio2020"
        cuit_cliente_input = "30500846301"

        agip = await Agip.create(
            playwright,
            client,
            cuit_Agip,
            clave_fiscal_Agip,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False
        )
        await agip.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
