"""
Test de regresión (known_issue) para jurisdicciones/salta.py::consultar_notificaciones.

CONFIRMADO EN VIVO (no es teoría): corriendo tests/e2e_live/ contra el
portal real de Salta con las credenciales de Adidas, un timeout esperando
"#enviaLogout" (sin ningún mensaje de error de credenciales visible) generó:

    LoginError: Servicio no disponible

Código responsable:

    try:
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        await self._click_aceptar_button()
        await self.page.wait_for_selector("#enviaLogout", timeout=15000, state="visible")
    except Exception as e:
        if await self.page.is_visible("div.error_text"):
            error_text = await self.page.locator("div.error_text").text_content()
            raise LoginError(self.cliente, error_text)          # <- esto SÍ está bien
        if await self.page.query_selector("#enviaLogout"):
            ... (siguió de largo, no es el caso que nos interesa)
        else:
            raise LoginError(self.cliente, LoginError.SERVICIO_NO_DISPONIBLE)  # <- BUG

Cuando ni el error explícito ni el selector de éxito aparecen (la
ambigüedad real: ¿fue un timeout de portal o credenciales malas?), el
código decide por descarte que son credenciales inválidas.

No se modifica salta.py.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from jurisdicciones.jurisdiccion import LoginError

pytestmark = [pytest.mark.unit, pytest.mark.known_issue, pytest.mark.asyncio]


@pytest.fixture
def salta_instance():
    from jurisdicciones.salta import Salta
    from logger import Logger

    instance = object.__new__(Salta)
    instance.cliente = "Cliente QA"
    instance.client_folder = "cliente_qa"
    instance._cuit = "30111111112"  # empieza con 3 -> usa login() directo
    instance._clave_fiscal = "clave-test"
    instance.cuit_cliente_input = "30111111112"
    instance.logger = Logger.get_logger()
    return instance


def _mock_page_ambiguo():
    """Ni error de credenciales visible, ni selector de éxito -- la
    ambigüedad real que hoy se resuelve (mal) como LoginError."""
    page = MagicMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock(side_effect=TimeoutError("no aparece"))
    page.is_visible = AsyncMock(return_value=False)  # ni error_text ni nada
    page.query_selector = AsyncMock(return_value=None)  # tampoco aparece tarde
    return page


async def test_timeout_ambiguo_hoy_se_clasifica_como_login_error(salta_instance):
    """Ya confirmado en vivo contra el portal real. Acá se reproduce
    determinísticamente con mocks para tener una regresión rápida sin
    depender de la disponibilidad real del portal de Salta."""
    salta_instance.page = _mock_page_ambiguo()
    salta_instance.login = AsyncMock(return_value=None)  # login "exitoso"
    salta_instance._click_aceptar_button = AsyncMock(return_value=None)

    with pytest.raises(LoginError) as exc_info:
        await salta_instance.consultar_notificaciones()

    # Comportamiento actual: LoginError con mensaje "Servicio no disponible".
    # (No se testea explícitamente que NO sea LoginTimeoutError porque esa
    # clase no existe en este repo -- ver COBERTURA_TIMEOUT_VS_CREDENCIALES.md.)
    assert str(exc_info.value) == LoginError.SERVICIO_NO_DISPONIBLE


async def test_error_de_credenciales_explicito_si_se_clasifica_bien(salta_instance):
    """Caso de control: cuando SÍ hay un div.error_text visible, la
    clasificación como LoginError es correcta y ya funciona bien hoy."""
    page = _mock_page_ambiguo()
    page.is_visible = AsyncMock(return_value=True)
    error_locator = MagicMock()
    error_locator.text_content = AsyncMock(return_value="Usuario o clave incorrecta")
    page.locator = MagicMock(return_value=error_locator)
    salta_instance.page = page
    salta_instance.login = AsyncMock(return_value=None)
    salta_instance._click_aceptar_button = AsyncMock(return_value=None)

    with pytest.raises(LoginError) as exc_info:
        await salta_instance.consultar_notificaciones()

    assert str(exc_info.value) == "Usuario o clave incorrecta"
