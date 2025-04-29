import os
from datetime import datetime

from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import (
    ConsultarNotificacionesError,
    Jurisdiccion,
    LoginError,
)


class Agip(Jurisdiccion):
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
            "Agip",
            "901 CABA",
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
        try:
            await self.page.goto("https://claveciudad.agip.gob.ar/", timeout=100000)
            await self.page.fill('xpath=//*[@id="cuit"]', f"{self._cuit}")
            await self.page.fill('xpath=//*[@id="clave"]', f"{self._clave_fiscal}")
            await self.page.click("xpath=//a[normalize-space()='Ingresar']")
            await self.page.wait_for_load_state("load")

            # Verificar errores de login - este error NO debe ser convertido a ConsultarNotificacionesError
            if await self.page.is_visible("text=Clave/Usuario incorrecto."):
                raise LoginError(self.cliente)

            await self.page.select_option(
                "select[name='cuit_representado']", f"{self._cuit_cliente_input}"
            )
            await self.page.fill(
                'xpath=//*[@id="filtro_app"]',
                "Domicilio Fiscal Electrónico",
                timeout=10000,
            )

            # Intento principal de navegación
            try:
                await self.page.click(
                    f"xpath=//*[@onclick='ir_servicio(54,{self._cuit_cliente_input})']",
                    timeout=5000,
                )
            except Exception:
                # Ruta alternativa
                await self.page.click(
                    "xpath=//*[@onclick='ir_servicio(54, 0)']", timeout=100000
                )
                # Clickear en Representados
                await self.page.wait_for_selector(
                    f"xpath=//li[@id='opRepresentados']//a[@class='dropdown-toggle']",
                    timeout=900000,
                )
                await self.page.click(
                    f"xpath=//li[@id='opRepresentados']//a[@class='dropdown-toggle']",
                    timeout=900000,
                )
                # Seleccionar el DFE del CUIT representado
                await self.page.wait_for_selector(
                    f"a[data-id='{self._cuit_cliente_input}']", timeout=100000
                )
                await self.page.click(
                    f"xpath=//*[a[@data-id={self._cuit_cliente_input}]]", timeout=100000
                )

            # Esta parte siempre debe ejecutarse si no hubo excepciones previas
            boton_filtro = (
                "xpath=//button[@class='btnNoLeidas btn btn-default']"  # no_leidas
            )
            await self.page.wait_for_selector(boton_filtro, timeout=100000)
            await self.page.click(boton_filtro, timeout=100000)  # 10 min

        except LoginError as le:
            # Re-lanzar errores de login directamente sin convertirlos
            raise
        except Exception as e:
            # Otros errores se convierten a ConsultarNotificacionesError
            raise ConsultarNotificacionesError(
                self.cliente, f"Error al consultar notificaciones: {str(e)}"
            ) from e

    async def buscar_notificacion(self):
        """
        Busca notificaciones en la tabla de mensajes de AGIP.

        Retorna True si:
        1. Existe alguna fila que contenga 's/Notificar'
        2. La fecha de esa fila es posterior o igual a self.fecha_desde
        """
        try:
            # Esperar a que la tabla esté visible
            await self.page.wait_for_selector(
                "table#tablaMensajes", state="visible", timeout=30000
            )

            # Obtener todas las filas que contienen 's/Notificar'
            filas_notificar = await self.page.query_selector_all(
                "xpath=//table[@id='tablaMensajes']/tbody/tr[td[contains(text(),'s/Notificar')]]"
            )

            self.logger.debug(
                f"AGIP: Se encontraron {len(filas_notificar)} filas con 's/Notificar'"
            )

            if len(filas_notificar) == 0:
                self.logger.debug("AGIP: No hay notificaciones pendientes")
                return False

            # Convertir fecha_desde a objeto datetime
            # self.fecha_desde está en formato 'ddmmyyyy'
            fecha_desde = datetime.strptime(self.fecha_desde, "%d%m%Y")

            for fila in filas_notificar:
                # Obtener la fecha de la columna 2
                fecha_td = await fila.query_selector("td:nth-child(2)")
                if fecha_td:
                    fecha_texto = await fecha_td.text_content()
                    fecha_texto = fecha_texto.strip()

                    try:
                        # Convertir a formato datetime (asumiendo formato 'yyyy-mm-dd')
                        fecha_notificacion = datetime.strptime(fecha_texto, "%Y-%m-%d")

                        self.logger.debug(
                            f"AGIP: Comparando fecha {fecha_notificacion} con {fecha_desde}"
                        )

                        # Comparar fechas
                        if fecha_notificacion >= fecha_desde:
                            self.logger.debug(
                                f"AGIP: Notificación encontrada con fecha {fecha_texto}"
                            )
                            return True
                    except ValueError as e:
                        self.logger.warning(
                            f"AGIP: Error al procesar fecha '{fecha_texto}': {str(e)}"
                        )

            return False
        except Exception as e:
            self.logger.error(f"AGIP: Error en buscar_notificacion: {str(e)}")
            # En caso de error, mejor reportar que sí hay notificaciones para que se revise manualmente
            return True

    async def tomar_screenshot(self):
        return await super().tomar_screenshot(self.page)

    async def procesar_jurisdiccion(self):
        return await super().procesar_jurisdiccion()


async def main():
    async with async_playwright() as playwright:
        fecha_desde = os.getenv("FECHA_DESDE")
        fecha_hasta = os.getenv("FECHA_HASTA")

        client = os.getenv("TEST_AGIP_CLIENT")
        cuit_Agip = os.getenv("TEST_AGIP_CUIT")
        clave_fiscal_Agip = os.getenv("TEST_AGIP_CLAVE_FISCAL")
        cuit_cliente_input = os.getenv("TEST_AGIP_CUIT_CLIENTE_INPUT")

        agip = await Agip.create(
            playwright,
            client,
            cuit_Agip,
            clave_fiscal_Agip,
            fecha_desde,
            fecha_hasta,
            cuit_cliente_input,
            headless=False,
        )
        await agip.procesar_jurisdiccion()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
