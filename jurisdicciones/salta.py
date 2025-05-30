import os
from datetime import datetime

# import requests
from playwright_stealth import stealth_async
from playwright.async_api import Playwright, async_playwright

from jurisdicciones.jurisdiccion import (
    Jurisdiccion,
    LoginError,
    DelegacionError,
    LoginErrorAfip,
)


class Salta(Jurisdiccion):
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
            "Salta",
            "917 SALTA",
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

    async def afip_login(
        self,
        url_afip_login: str = "https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=dgrsalta_rentas",
        salta_success_url: str = None,
    ) -> None:
        """
        Realiza el login en AFIP y selecciona el CUIT asociado correspondiente.

        Args:
            url_afip_login: URL del portal de login de AFIP específico para Salta
            salta_success_url: URL de éxito para verificar el login

        Raises:
            DelegacionError: Cuando el CUIT cliente no está disponible en la lista de CUITs asociados
            LoginErrorAfip: Cuando hay errores en el proceso de login de AFIP
        """
        # Realizar el login básico en AFIP
        await super().AFIP_login(url_afip_login, success_url=salta_success_url)

        try:
            # Verificar si aparece el selector de CUITs asociados (no es obligatorio)
            cuit_selector_exists = await self.page.wait_for_selector(
                "#cuitAsociados", timeout=5000, state="visible"
            )

            if cuit_selector_exists:
                self.logger.debug(
                    "SALTA: Selector de CUITs asociados encontrado, procediendo con selección"
                )
                await self._seleccionar_cuit_asociado()
                return

        except Exception:
            # Si no aparece el selector de CUITs, no es un error
            self.logger.debug(
                "SALTA: No se encontró selector de CUITs asociados, verificando login directo"
            )

        # Verificar que el login fue exitoso buscando el selector de logout
        try:
            await self.page.wait_for_selector(
                "#enviaLogout", timeout=15000, state="visible"
            )
            self.logger.debug(
                "SALTA: Login exitoso verificado mediante selector de logout"
            )

        except Exception as e:
            self.logger.error(f"SALTA: Error verificando login exitoso: {str(e)}")
            # Verificar si hay mensajes de error explícitos
            if await self.page.is_visible("div.error_text"):
                error_text = await self.page.locator("div.error_text").text_content()
                raise LoginErrorAfip(self.cliente, f"Error de login: {error_text}")
            
            if "https://www.dgrsalta.gov.ar/Inicio" in self.page.url:
                self.logger.warning(
                    f"SALTA: Detectada URL de inicio sin delegación: {self.page.url}"
                )
                raise DelegacionError(
                    self.cliente,
                )
            else:
                raise LoginErrorAfip(
                    self.cliente, "No se pudo verificar el login exitoso en AFIP"
                )

    async def _seleccionar_cuit_asociado(self) -> None:
        """
        Selecciona el CUIT cliente del dropdown de CUITs asociados e ingresa al sistema.

        Este método maneja la selección del CUIT específico del cliente y la navegación
        posterior al sistema de Salta.

        Raises:
            DelegacionError: Cuando el CUIT cliente no está disponible en la lista de CUITs asociados
            LoginErrorAfip: Cuando hay errores en el proceso de selección o ingreso
        """
        try:
            # Verificar si existe la opción con el CUIT cliente
            option_selector = (
                f"#cuitAsociados option[value='{self.cuit_cliente_input}']"
            )
            option_element = await self.page.query_selector(option_selector)

            if not option_element:
                self.logger.error(
                    f"SALTA: CUIT cliente {self.cuit_cliente_input} no encontrado en CUITs asociados"
                )
                raise DelegacionError(
                    self.cliente,
                    f"CUIT {self.cuit_cliente_input} no está delegado en el servicio",
                )

            # Seleccionar el CUIT cliente
            await self.page.select_option(
                "#cuitAsociados", value=self.cuit_cliente_input
            )
            self.logger.debug(
                f"SALTA: CUIT cliente {self.cuit_cliente_input} seleccionado"
            )

            # Hacer click en el botón "Ingresar"
            await self._click_ingresar_button()

            # Esperar a que la página cargue después del ingreso
            await self.page.wait_for_load_state("networkidle", timeout=30000)

        except DelegacionError:
            # Re-lanzar DelegacionError sin modificaciones
            raise
        except Exception as e:
            self.logger.error(f"SALTA: Error en selección de CUIT asociado: {str(e)}")
            # Convertir errores relacionados con la selección en DelegacionError
            if any(
                keyword in str(e) for keyword in ["cuitAsociados", "option", "select"]
            ):
                raise DelegacionError(
                    self.cliente, f"Error al acceder a CUITs asociados: {str(e)}"
                )
            else:
                # Para otros errores, mantener como error de login
                raise LoginErrorAfip(
                    self.cliente, f"Error en proceso de selección: {str(e)}"
                )

    async def _click_ingresar_button(self) -> None:
        """
        Hace click en el botón "Ingresar" para acceder al sistema de Salta.

        Intenta múltiples estrategias de selección para mayor robustez.

        Raises:
            LoginErrorAfip: Cuando no se puede encontrar o hacer click en el botón "Ingresar"
        """
        try:
            # Estrategia principal: buscar span con texto "Ingresar"
            ingresar_span = await self.page.query_selector("span:has-text('Ingresar')")

            if ingresar_span:
                await ingresar_span.click()
                self.logger.debug("SALTA: Click en botón 'Ingresar' realizado")
            else:
                # Estrategia alternativa: click directo por selector
                await self.page.click("span:has-text('Ingresar')")
                self.logger.debug(
                    "SALTA: Click en botón 'Ingresar' realizado (selector alternativo)"
                )

        except Exception as e:
            self.logger.error(
                f"SALTA: Error al hacer click en botón 'Ingresar': {str(e)}"
            )
            raise LoginErrorAfip(self.cliente, f"Error al acceder al sistema: {str(e)}")

    async def consultar_notificaciones(self):
        if int(str(self._cuit)[0]) != 3:
            await self.afip_login(
                salta_success_url="https://www.dgrsalta.gov.ar/rentassalta/form.login"
            )
        else:
            await self.login()

        # Mejorar la verificación de login exitoso con timeout adecuado
        try:
            # Esperar adecuadamente a que la página cargue
            await self.page.wait_for_load_state("networkidle", timeout=30000)

            # Esperar específicamente al selector de logout con un timeout razonable
            await self.page.wait_for_selector(
                "#enviaLogout", timeout=15000, state="visible"
            )
            self.logger.debug("SALTA: Login exitoso, se encontró el selector de logout")
        except Exception as e:
            # Verificar si hay errores explícitos antes de concluir que falló el login
            if await self.page.is_visible("div.error_text"):
                error_text = await self.page.locator("div.error_text").text_content()
                self.logger.error(f"SALTA: Error de login detectado: {error_text}")
                raise LoginError(self.cliente, error_text)

            # Verificar una última vez si el selector existe pero tardó en aparecer
            if await self.page.query_selector("#enviaLogout"):
                self.logger.warning(
                    "SALTA: El selector de logout apareció después del timeout"
                )
            else:
                self.logger.error("SALTA: No se pudo verificar el login exitoso")
                # Usar mensaje predefinido en lugar de exponer la excepción
                raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)

        # Continuar con las acciones en la página (resto del código sin cambios)
        await self.page.wait_for_selector(
            "//a[contains(text(), 'Domicilio Fiscal Electrónico')]"
        )
        await self.page.locator(
            "//a[contains(text(), 'Domicilio Fiscal Electrónico')]"
        ).click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector(
            "//a[contains(text(), 'Ventanilla Única de Novedades')]"
        )
        await self.page.locator(
            "//a[contains(text(), 'Ventanilla Única de Novedades')]"
        ).click()
        await self.page.wait_for_load_state("networkidle")

    async def login(self) -> None:
        """
        Realiza login directo en el portal de Salta.

        Verifica el éxito del login mediante la URL de redirección.
        URL exitosa: https://www.dgrsalta.gov.ar/rentassalta/form.login
        URL de error: https://www.dgrsalta.gov.ar/rentassalta/login.jsp

        Raises:
            LoginError: Cuando las credenciales son incorrectas o el login falla
        """
        try:
            await self.page.goto("https://www.dgrsalta.gov.ar/rentassalta/login.jsp")
            await self.page.wait_for_load_state()
            await self.page.wait_for_selector("input#usuario")
            await self.page.fill("input#usuario", self._cuit)
            await self.page.fill("input#password", self._clave_fiscal)
            await self.page.click("a#enviaLogin")

            # Esperar a que la página cargue completamente
            await self.page.wait_for_load_state("networkidle", timeout=15000)

            # Verificar URL para determinar éxito del login
            current_url = self.page.url

            if "https://www.dgrsalta.gov.ar/rentassalta/login.jsp" in current_url:
                # Sigue en la página de login, verificar mensaje de error específico
                error_selector = "//div[@class='error_text' and contains(text(), 'Usuario o Password Incorrecto')]"
                if await self.page.is_visible(error_selector):
                    self.logger.error("SALTA: Credenciales incorrectas detectadas")
                    raise LoginError(self.cliente, LoginError.CREDENCIALES_INVALIDAS)
                else:
                    self.logger.error(
                        "SALTA: Login falló, permanece en página de login"
                    )
                    raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)

            elif "https://www.dgrsalta.gov.ar/rentassalta/form.login" in current_url:
                # Login exitoso, verificar selector de logout
                await self.page.wait_for_selector(
                    "#enviaLogout", timeout=15000, state="visible"
                )
                self.logger.debug("SALTA: Login directo exitoso verificado")

            else:
                # URL inesperada
                self.logger.warning(
                    f"SALTA: URL inesperada después del login: {current_url}"
                )
                # Intentar verificar logout como fallback
                await self.page.wait_for_selector(
                    "#enviaLogout", timeout=15000, state="visible"
                )

        except LoginError:
            # Re-lanzar errores de login sin modificaciones
            raise
        except Exception as e:
            self.logger.error(f"SALTA: Error inesperado en login directo: {str(e)}")
            raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)

    async def buscar_notificacion(self):
        elements = await self.page.locator(
            "//td[contains(text(),'Por el momento no tiene novedades...')]"
        ).all()
        return False if len(elements) == 2 else True

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
            client = os.getenv("TEST_SALTA_CLIENT")
            cuit_Salta = os.getenv("TEST_SALTA_CUIT")
            clave_fiscal_Salta = os.getenv("TEST_SALTA_CLAVE_FISCAL")
            cuit_cliente_input = os.getenv("TEST_SALTA_CUIT_CLIENTE_INPUT")

            salta = await Salta.create(
                playwright,
                client,
                cuit_Salta,
                clave_fiscal_Salta,
                fecha_desde,
                fecha_hasta,
                cuit_cliente_input,
                headless=False,
            )
            await salta.procesar_jurisdiccion()

    asyncio.run(main())
