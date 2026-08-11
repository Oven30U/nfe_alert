"""
Fixtures que faltaban tras juntar la suite QA original en test2/: la suite
QA definía `cliente` y `agip_instance` en su propio conftest.py, que se
perdió al fusionar todo en una sola carpeta test2/. Este archivo los
repone, sin tocar el conftest.py raíz existente (el de la DB de
test/credenciales).

Colocar una copia idéntica de este archivo en:
  - test2/unit/conftest.py
  - test2/integration/conftest.py
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def cliente() -> str:
    return "CLIENTE_QA"


@pytest.fixture
def agip_instance(cliente, tmp_path):
    """Crea Agip sin abrir navegador ni ejecutar __init__ productivo."""
    from jurisdicciones.agip import Agip

    instance = object.__new__(Agip)
    instance.cliente = cliente
    instance.client_folder = str(tmp_path)
    instance._cuit = "20123456789"
    instance._clave_fiscal = "clave-ficticia"
    instance._cuit_cliente_input = "20123456789"
    instance.cuit_cliente_input = "20123456789"
    instance.fecha_desde = "01072026"
    instance.fecha_hasta = "31072026"
    instance.logger = MagicMock()
    instance.page = MagicMock()
    return instance


@pytest.fixture
def fake_locator():
    locator = MagicMock()
    locator.is_visible = AsyncMock(return_value=False)
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.wait_for = AsyncMock()
    return locator
