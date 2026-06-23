"""
Fixtures compartidos para toda la suite de tests de NFE Alert.

Proporciona instancias mockeadas de Playwright, browser, context y page
para evitar cualquier conexión real a portales fiscales durante los tests.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Agregar el directorio raíz del proyecto al path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixtures de infraestructura Playwright (todos mockeados)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_page():
    """Mock de playwright.async_api.Page con los métodos más usados."""
    page = AsyncMock()
    page.url = "https://example.com"
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.wait_for_function = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.is_visible = AsyncMock(return_value=False)
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.screenshot = AsyncMock()
    page.reload = AsyncMock()
    page.locator = MagicMock(return_value=AsyncMock())
    page.get_by_role = MagicMock(return_value=AsyncMock())
    page.get_by_label = MagicMock(return_value=AsyncMock())
    page.get_by_text = MagicMock(return_value=AsyncMock())
    page.close = AsyncMock()
    page.context = AsyncMock()
    return page


@pytest.fixture
def mock_context(mock_page):
    """Mock de playwright BrowserContext."""
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page)
    context.close = AsyncMock()
    return context


@pytest.fixture
def mock_browser(mock_context):
    """Mock de playwright Browser."""
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=mock_context)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_playwright(mock_browser):
    """Mock del objeto Playwright principal."""
    playwright = MagicMock()
    playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    return playwright


# ---------------------------------------------------------------------------
# Fixture base para instanciar Jurisdiccion con mocks inyectados
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def jurisdiccion_base(mock_playwright, mock_browser, mock_context, mock_page):
    """
    Instancia concreta de Jurisdiccion usando una subclase mínima,
    con browser/context/page inyectados para evitar lanzar Chrome real.
    """
    from jurisdicciones.jurisdiccion import Jurisdiccion

    class JurisdiccionConcreta(Jurisdiccion):
        """Subclase mínima para poder instanciar la clase abstracta en tests."""
        async def consultar_notificaciones(self):
            pass

    instancia = await JurisdiccionConcreta.create(
        playwright=mock_playwright,
        nombre="TestJurisdiccion",
        codigo="999 TEST",
        cliente="ClienteTest",
        client_folder="ClienteTest_Folder",
        cuit="20123456789",
        clave_fiscal="clave123",
        fecha_desde="01012024",
        fecha_hasta="31012024",
        cuit_cliente_input="20987654321",
        browser=mock_browser,
        context=mock_context,
        page=mock_page,
    )
    return instancia


# ---------------------------------------------------------------------------
# Fixture de variables de entorno para tests de configuración
# ---------------------------------------------------------------------------

@pytest.fixture
def env_basico(monkeypatch):
    """Variables de entorno mínimas necesarias para que el sistema funcione."""
    monkeypatch.setenv("PATH_ESTRUCTURA_ROBOT", "/tmp/nfe_test")
    monkeypatch.setenv("LIMITES_REINTENTO", "3")
    monkeypatch.setenv("JURISDICCIONES_CONCURRENTES", "2")
    monkeypatch.setenv("JURISDICCIONES_DESHABILITADAS", "")
    monkeypatch.setenv("CLIENTES_ENVIAR_AUNQUE_ERROR", "")
    monkeypatch.setenv("MODO_CONTINUO", "false")
    os.makedirs("/tmp/nfe_test/ClienteTest_Folder/Output", exist_ok=True)
    yield
    # La limpieza de /tmp es automática
