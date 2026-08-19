"""
Tests para jurisdicciones/sicnea.py::_select_cuit_from_dropdown.

ACTUALIZADO (rama nfe_alert_agip_agosto): el manejo de excepciones de este
método cambió respecto de la versión original que se auditó primero. Antes:

    try:
        dropdown = await self.new_page_2.query_selector(dropdown_selector)
        ...
    except LoginError:
        raise
    except Exception as e:
        raise LoginError(self.cliente, f"Failed to select client CUIT: {str(e)}")

Ahora:

    try:
        dropdown = await self.new_page_2.query_selector(dropdown_selector)
        ...
        if self.cuit_cliente_input not in options:
            raise DelegacionError(self.cliente)
        ...
    except DelegacionError:
        raise
    except Exception as e:
        raise DelegacionError(self.cliente)

Qué se arregló: el hallazgo original (un `DelegacionError` legítimo -- CUIT
no encontrado en el dropdown -- se reempaquetaba como `LoginError`, perdiendo
la distinción entre "no delegado" y "credenciales inválidas") está
resuelto: ahora un `DelegacionError` real se propaga como tal.

Qué sigue sin resolverse (dev lo tiene identificado, no es urgente):
cualquier OTRA excepción durante este paso -- por ejemplo, un timeout de
Playwright buscando el dropdown, que no tiene nada que ver con delegación
-- también se envuelve como `DelegacionError` ahora, en vez de cómo un
error técnico. Es la misma ambigüedad "timeout vs. clasificación
específica" que ya vimos en Agip/Salta/Neuquen, sólo que la categoría a la
que cae cambió de LoginError a DelegacionError.

No se modifica sicnea.py desde acá.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from jurisdicciones.jurisdiccion import DelegacionError, LoginError

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


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


@pytest.mark.known_issue
async def test_timeout_en_query_selector_se_clasifica_como_delegacion_error(sicnea_instance):
    """Un timeout de Playwright buscando el dropdown (nada que ver con
    delegación ni con credenciales) hoy termina siendo un DelegacionError.
    Antes del fix de sicnea.py caía en LoginError; sigue siendo una
    clasificación incorrecta, sólo que cambió de categoría. Dev: no
    prioritario por ahora."""
    new_page_2 = MagicMock()
    new_page_2.query_selector = AsyncMock(side_effect=TimeoutError("frame no responde"))
    sicnea_instance.new_page_2 = new_page_2

    with pytest.raises(DelegacionError) as exc_info:
        await sicnea_instance._select_cuit_from_dropdown()

    assert not isinstance(exc_info.value, LoginError)


async def test_cuit_no_delegado_se_propaga_como_delegacion_error(sicnea_instance):
    """
    ✅ Confirma el fix: cuando el CUIT del cliente no está entre las
    opciones del dropdown (no está delegado), la excepción se propaga
    limpiamente como `DelegacionError` -- ya no se reempaqueta como
    `LoginError`. Si este test empieza a fallar, es porque sicnea.py volvió
    a envolver este caso mal; no debería tocarse sin avisar."""
    new_page_2 = MagicMock()
    dropdown = MagicMock()
    dropdown.evaluate = AsyncMock(return_value=["20000000001", "20000000002"])
    new_page_2.query_selector = AsyncMock(return_value=dropdown)
    sicnea_instance.new_page_2 = new_page_2

    with pytest.raises(DelegacionError) as exc_info:
        await sicnea_instance._select_cuit_from_dropdown()

    assert str(exc_info.value) == DelegacionError.DEFAULT_MESSAGE
