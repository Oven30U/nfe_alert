from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from jurisdicciones.jurisdiccion import LoginError

PASOS_MANUALES_AMBOS_METODOS_FALLAN = """\
Cómo reproducir esto a mano, sin correr pytest ni leer código:
1. Abrí una ventana de incógnito en Chrome.
2. Andá a: https://claveciudad.agip.gob.ar/
3. Iniciá sesión con un CUIT/clave INCORRECTOS a propósito (para forzar que
  tanto "Clave Ciudad" como el método alternativo "MiBA" rechacen el login).
4. En producción, cuando AMBOS métodos de login fallan, el sistema debería
  mostrar un mensaje claro de "Credenciales inválidas" para esa jurisdicción.
5. Lo que en realidad pasa hoy: el código revienta con un error interno de
  Python (TypeError: LoginError.__init__() missing 1 required positional
  argument: 'cliente') en vez de reportar el error de forma prolija. Esto
  está en jurisdicciones/agip.py, método _login, línea:
      raise LoginError from e
  (le falta pasarle el cliente: raise LoginError(self.cliente) from e)
6. Si el robot corre en producción y esto pasa, probablemente el proceso
  completo para esa jurisdicción/cliente se corte de forma abrupta en vez
  de registrar prolijamente "Credenciales inválidas".
"""


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_login_usa_fallback_miba_si_clave_ciudad_falla(agip_instance):
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()

    link = MagicMock()
    link.is_visible = AsyncMock(return_value=True)
    link.click = AsyncMock()
    page.locator.return_value = link
    agip_instance.page = page

    agip_instance._login_clave_ciudad = AsyncMock(
        side_effect=LoginError(agip_instance.cliente)
    )
    agip_instance._login_miba = AsyncMock(return_value=None)

    await agip_instance._login()

    agip_instance._login_clave_ciudad.assert_awaited_once()
    agip_instance._login_miba.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.timeout
@pytest.mark.asyncio
async def test_login_usa_fallback_si_primer_metodo_hace_timeout(agip_instance):
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()

    link = MagicMock()
    link.is_visible = AsyncMock(return_value=True)
    link.click = AsyncMock()
    page.locator.return_value = link
    agip_instance.page = page

    agip_instance._login_clave_ciudad = AsyncMock(
        side_effect=PlaywrightTimeoutError("timeout inicial")
    )
    agip_instance._login_miba = AsyncMock(return_value=None)

    await agip_instance._login()

    agip_instance._login_miba.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.credentials
@pytest.mark.manual_repro(PASOS_MANUALES_AMBOS_METODOS_FALLAN)
@pytest.mark.asyncio
async def test_login_lanza_error_si_ambos_metodos_fallan(agip_instance):
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()

    link = MagicMock()
    link.is_visible = AsyncMock(return_value=True)
    link.click = AsyncMock()
    page.locator.return_value = link
    agip_instance.page = page

    agip_instance._login_clave_ciudad = AsyncMock(
        side_effect=LoginError(agip_instance.cliente)
    )
    agip_instance._login_miba = AsyncMock(
        side_effect=LoginError(agip_instance.cliente)
    )

    with pytest.raises(LoginError):
        await agip_instance._login()
