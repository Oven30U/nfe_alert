"""
Test de regresión GENÉRICO, parametrizado sobre las 24 jurisdicciones
implementadas: dado un `page` completamente mockeado donde NINGÚN
indicador de error de credenciales está presente (todo `is_visible()` /
`.count()` devuelve "no encontrado"), llamar a `consultar_notificaciones()`
NO debe terminar en `LoginError`/`LoginErrorAfip`.

Esto no reemplaza los tests específicos y más profundos de
agip/salta/sicnea/neuquen (ver archivos known_issue dedicados): esos
reproducen el escenario exacto de timeout con precisión quirúrgica. Este
test genérico es la red de seguridad amplia que cubre las jurisdicciones
restantes con un único mock "todo niega que haya error", parametrizado.

No importa si `consultar_notificaciones()` termina en otra excepción
(Playwright chocando con un Mock al querer leer texto real, por ejemplo):
lo único que se audita acá es que esa excepción NUNCA sea LoginError o
LoginErrorAfip, porque eso es exactamente lo que le pasó al cliente real
que reportaste (Salta) y lo que queremos detectar en cualquier otra.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from jurisdicciones.jurisdiccion import LoginError, LoginErrorAfip

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

# Jurisdicciones excluidas de este test genérico porque ya tienen su propio
# test dedicado, mucho más preciso (ver tests/unit/test_<clase>_timeout_vs_credenciales.py):
EXCLUIDAS_TIENEN_TEST_DEDICADO = {"Agip", "Salta", "Sicnea", "Neuquen"}

# El resto de las 24 (config.jurisdiccion_clases) menos las 2 sin
# implementar (SantaFe, TierraDelFuego) y las excluidas de arriba.
JURISDICCIONES_A_TESTEAR = [
    "Arba", "Catamarca", "Chaco", "Chubut", "Cordoba", "Corrientes",
    "EntreRios", "Formosa", "Jujuy", "LaPampa", "LaRioja", "Mendoza",
    "Misiones", "Nacional", "RioNegro", "SanJuan", "SanLuis", "SantaCruz",
    "SantiagoDelEstero", "Tucuman",
]


def _kwargs_base(clase: str) -> dict:
    return dict(
        nombre=clase,
        codigo=f"000 {clase.upper()}",
        cliente="Cliente QA",
        client_folder="cliente_qa",
        cuit="20111111112",
        clave_fiscal="clave-test",
        fecha_desde="01072026",
        fecha_hasta="31072026",
        cuit_cliente_input="30111111112",
    )


def _page_que_no_encuentra_ningun_error():
    """Page/locator completamente mockeado: cualquier is_visible()/count()
    consultado devuelve "no encontrado". Todo lo demás (fill, click, goto,
    wait_for_load_state, etc.) es un AsyncMock genérico que "funciona" sin
    hacer nada real."""
    page = MagicMock()

    async def _is_visible(*args, **kwargs):
        return False

    locator_mock = MagicMock()
    locator_mock.is_visible = AsyncMock(return_value=False)
    locator_mock.count = AsyncMock(return_value=0)
    locator_mock.click = AsyncMock()
    locator_mock.fill = AsyncMock()
    locator_mock.wait_for = AsyncMock(side_effect=TimeoutError("no aparece"))
    locator_mock.nth = MagicMock(return_value=locator_mock)
    locator_mock.first = locator_mock
    locator_mock.all = AsyncMock(return_value=[])
    locator_mock.inner_text = AsyncMock(return_value="")

    page.is_visible = AsyncMock(side_effect=_is_visible)
    page.locator = MagicMock(return_value=locator_mock)
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock(side_effect=TimeoutError("no aparece"))
    page.content = AsyncMock(return_value="")
    page.get_by_role = MagicMock(return_value=locator_mock)
    page.get_by_placeholder = MagicMock(return_value=locator_mock)
    page.get_by_label = MagicMock(return_value=locator_mock)
    page.frame = MagicMock(return_value=None)
    page.frame_locator = MagicMock(return_value=locator_mock)
    return page


@pytest.mark.parametrize("clase", JURISDICCIONES_A_TESTEAR)
async def test_sin_indicadores_de_error_nunca_clasifica_como_login_error(clase):
    import jurisdicciones
    from logger import Logger

    JurisdictionClass = getattr(jurisdicciones, clase)
    instancia = JurisdictionClass(**_kwargs_base(clase))
    instancia.logger = Logger.get_logger()
    instancia.page = _page_que_no_encuentra_ningun_error()
    instancia.new_page = instancia.page
    instancia._cuit = instancia.cuit if hasattr(instancia, "cuit") else "20111111112"
    instancia._clave_fiscal = "clave-test"
    instancia._cuit_cliente_input = "30111111112"

    try:
        await instancia.consultar_notificaciones()
    except (LoginError, LoginErrorAfip) as e:
        pytest.fail(
            f"'{clase}': sin ningún indicador de error visible en la página, "
            f"consultar_notificaciones() clasificó igual como "
            f"{type(e).__name__} ({e}). Esto es exactamente el bug de "
            f"'timeout reportado como credenciales inválidas'."
        )
    except Exception:
        # Cualquier otra excepción es aceptable para este test: sólo audita
        # que NO sea un error de credenciales.
        pass
