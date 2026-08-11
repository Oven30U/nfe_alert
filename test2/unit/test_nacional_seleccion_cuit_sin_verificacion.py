"""
Tests para jurisdicciones/nacional.py::_seleccionar_cuit_cliente.

ACTUALIZADO (rama nfe_alert_agip_agosto): el incidente original reportado
("Dolar App ingresó pero se quedó con el CUIT de la persona en lugar de la
empresa") ya tiene una corrección en el código real: ahora, después de
clickear el CUIT del cliente, el método SÍ vuelve a leer la página (hasta 3
intentos) para confirmar que el "representado activo" que quedó mostrado en
pantalla coincide con el nombre de la empresa esperada. Si después de 3
intentos no logra confirmarlo, corta con una excepción nueva y específica:
`RepresentadoNoDisponible` (antes no existía; antes el método terminaba
"silenciosamente exitoso" sin verificar nada -- ver test que reemplazamos
más abajo).

No se modifica nacional.py desde acá.
"""
import re
import unicodedata
from unittest.mock import AsyncMock, MagicMock

import pytest

from jurisdicciones.jurisdiccion import DelegacionError, RepresentadoNoDisponible
from jurisdicciones.nacional import Nacional

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

BOTON_SELECTOR = 'xpath=//button[@id="30111111112"]'
ACTIVO_SELECTOR = "a.nav-link.active .selected-represented span"


@pytest.fixture
def nacional_instance():
    instance = object.__new__(Nacional)
    instance.cliente = "Cliente QA"
    instance.client_folder = "cliente_qa"
    instance.cuit_cliente_input = "30111111112"
    instance.logger = MagicMock()
    # `_seleccionar_cuit_cliente` usa self.page (distinto de self.new_page)
    # sólo para wait_for_load_state tras el click.
    instance.page = MagicMock()
    instance.page.wait_for_load_state = AsyncMock()
    # El popup de confirmación se maneja aparte; no es el foco de este test.
    instance._click_boton_cerrar = AsyncMock()
    return instance


def _make_new_page(
    boton_visible: bool,
    boton_texto: str = "",
    activo_encontrado: bool = False,
    activo_texto: str = "",
):
    """Arma un new_page mockeado configurable para los 2 puntos de lectura
    que ejercita `_seleccionar_cuit_cliente`: el texto del botón del CUIT
    (para saber qué empresa se espera) y el texto del "representado activo"
    después del click (para validar que efectivamente cambió el contexto)."""
    boton_locator = MagicMock()
    boton_locator.inner_text = AsyncMock(return_value=boton_texto)

    activo_locator = MagicMock()
    activo_locator.count = AsyncMock(return_value=1 if activo_encontrado else 0)
    activo_locator.first.inner_text = AsyncMock(return_value=activo_texto)

    def _locator(selector, *args, **kwargs):
        if selector == BOTON_SELECTOR:
            return boton_locator
        if selector == ACTIVO_SELECTOR:
            return activo_locator
        return MagicMock()

    page = MagicMock()
    page.is_visible = AsyncMock(return_value=boton_visible)
    page.click = AsyncMock()
    page.locator = MagicMock(side_effect=_locator)
    if activo_encontrado:
        page.wait_for_selector = AsyncMock(return_value=True)
    else:
        page.wait_for_selector = AsyncMock(side_effect=TimeoutError("no aparece"))
    return page


async def test_boton_no_visible_lanza_delegacion_error(nacional_instance):
    """Caso de control, sin cambios: si el botón del CUIT no está en el DOM,
    corta de entrada con DelegacionError, sin llegar a intentar nada más."""
    new_page = _make_new_page(boton_visible=False)
    nacional_instance.new_page = new_page

    with pytest.raises(DelegacionError):
        await nacional_instance._seleccionar_cuit_cliente()

    new_page.click.assert_not_called()


async def test_verificacion_exitosa_no_lanza_excepcion(nacional_instance):
    """
    ✅ Confirma el fix del incidente reportado: cuando el botón está visible,
    el click funciona, y el "representado activo" que queda en pantalla
    después SÍ coincide con la empresa esperada, el método termina
    normalmente (sin excepción) -- y ahora, a diferencia de la versión
    vieja, SÍ leyó contenido de la página para confirmarlo (antes no leía
    nada, se explica en el docstring del módulo)."""
    new_page = _make_new_page(
        boton_visible=True,
        boton_texto="Empresa Demo SA - 30.111.111.112",
        activo_encontrado=True,
        activo_texto="Empresa Demo SA",
    )
    nacional_instance.new_page = new_page

    await nacional_instance._seleccionar_cuit_cliente()

    new_page.click.assert_awaited_once()
    nacional_instance._click_boton_cerrar.assert_awaited()


async def test_verificacion_que_nunca_coincide_lanza_representado_no_disponible(
    nacional_instance,
):
    """
    ⚠️ Caso "click funciona pero el contexto real nunca cambia" -- el
    escenario que originó el incidente reportado. Ahora, en vez de terminar
    silenciosamente exitoso (bug viejo), el método agota 3 reintentos
    intentando confirmar el representado activo y, si nunca coincide,
    corta con `RepresentadoNoDisponible` en vez de seguir de largo leyendo
    notificaciones bajo el contexto equivocado."""
    new_page = _make_new_page(
        boton_visible=True,
        boton_texto="Empresa Demo SA - 30.111.111.112",
        activo_encontrado=False,  # nunca aparece el representado activo esperado
    )
    nacional_instance.new_page = new_page

    with pytest.raises(RepresentadoNoDisponible):
        await nacional_instance._seleccionar_cuit_cliente()

    assert new_page.click.await_count == 3  # agotó los 3 intentos
