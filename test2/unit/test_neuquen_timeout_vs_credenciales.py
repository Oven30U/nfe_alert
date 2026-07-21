"""
Test de regresión (known_issue) para
jurisdicciones/neuquen.py::login_neuquen_afip.

    except Exception as e:
        self.logger.error(f"Error completando login AFIP para Neuquen: {str(e)}")
        await self.tomar_screenshot_error("afip_login_error")
        if isinstance(e, LoginError):
            raise
        else:
            raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)

Es el mismo patrón que agip.py/salta.py: un `except Exception` genérico que
envuelve CUALQUIER excepción -- incluyendo un timeout de Playwright
esperando "Bandeja de Mensajes - Notificaciones" -- como `LoginError`.

No se modifica neuquen.py.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from jurisdicciones.jurisdiccion import LoginError

pytestmark = [pytest.mark.unit, pytest.mark.known_issue, pytest.mark.asyncio]


@pytest.fixture
def neuquen_instance():
    from jurisdicciones.neuquen import Neuquen
    from logger import Logger

    instance = object.__new__(Neuquen)
    instance.cliente = "Cliente QA"
    instance.client_folder = "cliente_qa"
    instance._cuit_cliente_input = "30111111112"
    instance.logger = Logger.get_logger()
    instance.tomar_screenshot_error = AsyncMock(return_value=None)
    return instance


async def test_timeout_esperando_bandeja_se_clasifica_como_login_error(neuquen_instance):
    """Simula que el combobox 'CUIT a Representar' no está visible (camino
    directo a la espera final) y que la bandeja de notificaciones nunca
    aparece (timeout puro, sin ningún mensaje de error de credenciales).
    Hoy esto se reempaqueta igual como LoginError."""
    page = MagicMock()
    combobox = MagicMock()
    combobox.click = AsyncMock()
    combobox.fill = AsyncMock()
    combobox.press = AsyncMock()
    page.get_by_role = MagicMock(return_value=combobox)

    class _PopupCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        @property
        def value(self):
            raise NotImplementedError

    page.expect_popup = MagicMock(side_effect=TimeoutError("no aparece el popup"))
    neuquen_instance.page = page
    neuquen_instance.AFIP_login = AsyncMock(return_value=None)

    with pytest.raises(LoginError) as exc_info:
        await neuquen_instance.login_neuquen_afip()

    assert str(exc_info.value) == LoginError.SERVICIO_NO_DISPONIBLE
    neuquen_instance.tomar_screenshot_error.assert_awaited_once()


async def test_login_error_explicito_se_propaga_sin_doble_envoltura(neuquen_instance):
    """Caso de control: si el error ya es un LoginError (por ejemplo,
    levantado por el propio AFIP_login), se re-lanza tal cual, sin
    envolverlo de nuevo -- esto ya funciona bien hoy."""
    neuquen_instance.page = MagicMock()
    neuquen_instance.AFIP_login = AsyncMock(
        side_effect=LoginError("Cliente QA", "Credenciales inválidas AFIP")
    )

    with pytest.raises(LoginError) as exc_info:
        await neuquen_instance.login_neuquen_afip()

    assert str(exc_info.value) == "Credenciales inválidas AFIP"
