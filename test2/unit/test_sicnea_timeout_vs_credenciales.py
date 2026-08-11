"""
Test de regresión (known_issue) para jurisdicciones/sicnea.py::_select_cuit_from_dropdown.

    try:
        dropdown = await self.new_page_2.query_selector(dropdown_selector)
        ...
    except LoginError:
        raise
    except Exception as e:
        self.logger.error(f"Error selecting client CUIT: {str(e)}")
        raise LoginError(self.cliente, f"Failed to select client CUIT: {str(e)}")

Cualquier excepción durante la selección del CUIT en el dropdown (timeout
de Playwright esperando el frame/select, por ejemplo) se reempaqueta como
`LoginError` -- aunque el problema real no tenga nada que ver con
credenciales, sino con un timeout técnico durante un paso posterior al
login (selección de la empresa delegada).

No se modifica sicnea.py.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from jurisdicciones.jurisdiccion import DelegacionError, LoginError

pytestmark = [pytest.mark.unit, pytest.mark.known_issue, pytest.mark.asyncio]


@pytest.fixture
def sicnea_instance():
    from jurisdicciones.sicnea import Sicnea
    from logger import Logger

    instance = object.__new__(Sicnea)
    instance.cliente = "Cliente QA"
    instance.client_folder = "cliente_qa"
    instance.cuit_cliente_input = "30111111112"
    instance.logger = Logger.get_logger()
    return instance


async def test_timeout_en_query_selector_se_clasifica_como_login_error(sicnea_instance):
    """Un timeout de Playwright buscando el dropdown (nada que ver con
    credenciales) hoy termina siendo un LoginError."""
    new_page_2 = MagicMock()
    new_page_2.query_selector = AsyncMock(side_effect=TimeoutError("frame no responde"))
    sicnea_instance.new_page_2 = new_page_2

    with pytest.raises(LoginError) as exc_info:
        await sicnea_instance._select_cuit_from_dropdown()

    assert not isinstance(exc_info.value, DelegacionError)
    assert "Failed to select client CUIT" in str(exc_info.value)


async def test_cuit_no_delegado_tambien_termina_envuelto_como_login_error(sicnea_instance):
    """
    ⚠️ Segundo hallazgo en el mismo método: `DelegacionError` NO hereda de
    `LoginError` (son excepciones hermanas, no padre-hijo). El
    `except LoginError: raise` de arriba por lo tanto NO atrapa un
    `DelegacionError` interno -- cae al `except Exception` genérico y
    termina reempaquetado como `LoginError` con el mensaje de
    "Servicio pendiente de delegación" adentro del texto, en vez de
    propagarse como el `DelegacionError` que en realidad es.

    Comportamiento actual (no es el ideal, documentado acá): se pierde la
    distinción entre "no está delegado" y "credenciales inválidas" -- ambos
    terminan siendo un LoginError.
    """
    new_page_2 = MagicMock()
    dropdown = MagicMock()
    dropdown.evaluate = AsyncMock(return_value=["20000000001", "20000000002"])
    new_page_2.query_selector = AsyncMock(return_value=dropdown)
    sicnea_instance.new_page_2 = new_page_2

    with pytest.raises(LoginError) as exc_info:
        await sicnea_instance._select_cuit_from_dropdown()

    assert not isinstance(exc_info.value, DelegacionError)
    assert "delegaci" in str(exc_info.value).lower()
