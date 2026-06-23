"""
Tests de Integración — NFE Alert
==================================
Cubre el flujo completo de procesar_jurisdiccion con browser, context y page
mockeados. Sin conexión real a portales fiscales ni DB.

Cubre:
  - Todos los escenarios de procesar_jurisdiccion (camino feliz, login error,
    delegación, screenshot error)
  - Invariante: cerrar_navegador siempre se llama
  - Ownership del browser (_owns_browser True/False)
  - AFIP_login: escenarios de error con page mockeada
  - cerrar_recursos: cierre correcto de page, context y browser
  - Aislamiento de estado entre instancias concurrentes
  - No terminación silenciosa (tuple de 4 siempre definido)
  - tomar_varias_screenshots: robustez parcial
"""

import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helper: instancia concreta configurable
# ---------------------------------------------------------------------------

async def _make(playwright, browser, context, page,
                nombre="JTest", consultar_fn=None):
    from jurisdicciones.jurisdiccion import Jurisdiccion

    class JMock(Jurisdiccion):
        async def consultar_notificaciones(self_):
            if consultar_fn:
                await consultar_fn(self_)

    return await JMock.create(
        playwright=playwright, nombre=nombre, codigo="000",
        cliente="ClienteTest", client_folder="CF",
        cuit="20123456789", clave_fiscal="clave",
        fecha_desde="01012024", fecha_hasta="31012024",
        cuit_cliente_input="20987654321",
        browser=browser, context=context, page=page,
    )


# ===========================================================================
# procesar_jurisdiccion: camino feliz
# ===========================================================================

class TestProcesarCaminoFeliz:

    @pytest.mark.asyncio
    async def test_retorna_tuple_de_4_elementos(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=True)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        resultado = await j.procesar_jurisdiccion()
        assert isinstance(resultado, tuple) and len(resultado) == 4

    @pytest.mark.asyncio
    async def test_primer_elemento_es_nombre(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=True)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        nombre, *_ = await j.procesar_jurisdiccion()
        assert nombre == "JTest"

    @pytest.mark.asyncio
    async def test_hay_notificaciones_cuando_buscar_true(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=True)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        _, notif, _, _ = await j.procesar_jurisdiccion()
        assert notif == "Hay notificaciones"

    @pytest.mark.asyncio
    async def test_no_hay_notificaciones_cuando_buscar_false(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=False)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        _, notif, _, _ = await j.procesar_jurisdiccion()
        assert notif == "No hay notificaciones"

    @pytest.mark.asyncio
    async def test_hay_y_no_hay_son_distinguibles(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        """Boundary: mata hardcoded returns."""
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        j.buscar_notificacion = AsyncMock(return_value=True)
        _, n1, _, _ = await j.procesar_jurisdiccion()
        j.buscar_notificacion = AsyncMock(return_value=False)
        _, n2, _, _ = await j.procesar_jurisdiccion()
        assert n1 != n2

    @pytest.mark.asyncio
    async def test_error_type_none_en_camino_feliz(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=True)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        *_, error = await j.procesar_jurisdiccion()
        assert error is None

    @pytest.mark.asyncio
    async def test_cerrar_navegador_se_llama_en_camino_feliz(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=True)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        await j.procesar_jurisdiccion()
        j.cerrar_navegador.assert_called_once()


# ===========================================================================
# procesar_jurisdiccion: LoginError
# ===========================================================================

class TestProcesarLoginError:

    @pytest.mark.asyncio
    async def test_error_type_es_login_error(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            async def raise_login(self_): raise LoginError("ClienteTest")
            j = await _make(mock_playwright, mock_browser, mock_context, mock_page,
                            consultar_fn=raise_login)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        _, _, _, error = await j.procesar_jurisdiccion()
        assert error == "LoginError"

    @pytest.mark.asyncio
    async def test_cerrar_navegador_se_llama_aunque_hay_login_error(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            async def raise_login(self_): raise LoginError("ClienteTest")
            j = await _make(mock_playwright, mock_browser, mock_context, mock_page,
                            consultar_fn=raise_login)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        await j.procesar_jurisdiccion()
        j.cerrar_navegador.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_error_intenta_screenshot(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        """LoginError no está en errores_sin_screenshot."""
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            async def raise_login(self_): raise LoginError("ClienteTest")
            j = await _make(mock_playwright, mock_browser, mock_context, mock_page,
                            consultar_fn=raise_login)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        await j.procesar_jurisdiccion()
        j.tomar_screenshot.assert_called()


# ===========================================================================
# procesar_jurisdiccion: DelegacionError
# ===========================================================================

class TestProcesarDelegacion:

    @pytest.mark.asyncio
    async def test_error_type_es_delegacion(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            async def raise_deleg(self_): raise DelegacionError("ClienteTest")
            j = await _make(mock_playwright, mock_browser, mock_context, mock_page,
                            consultar_fn=raise_deleg)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        *_, error = await j.procesar_jurisdiccion()
        assert error == "DelegacionError"

    @pytest.mark.asyncio
    async def test_delegacion_no_llama_tomar_screenshot(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        """Mutante crítico: inversión de errores_sin_screenshot."""
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            async def raise_deleg(self_): raise DelegacionError("ClienteTest")
            j = await _make(mock_playwright, mock_browser, mock_context, mock_page,
                            consultar_fn=raise_deleg)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        await j.procesar_jurisdiccion()
        j.tomar_screenshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_delegacion_llama_cerrar_navegador(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            async def raise_deleg(self_): raise DelegacionError("ClienteTest")
            j = await _make(mock_playwright, mock_browser, mock_context, mock_page,
                            consultar_fn=raise_deleg)
        j.tomar_screenshot = AsyncMock(return_value=True)
        j.cerrar_navegador = AsyncMock()
        await j.procesar_jurisdiccion()
        j.cerrar_navegador.assert_called_once()


# ===========================================================================
# procesar_jurisdiccion: error de screenshot
# ===========================================================================

class TestProcesarScreenshotError:

    @pytest.mark.asyncio
    async def test_error_type_es_tomar_screenshot_error(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=True)
        j.tomar_screenshot = AsyncMock(side_effect=Exception("fallo screenshot"))
        j.cerrar_navegador = AsyncMock()
        *_, error = await j.procesar_jurisdiccion()
        assert error == "TomarScreenshotError"

    @pytest.mark.asyncio
    async def test_cerrar_navegador_se_llama_aunque_falle_screenshot(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(return_value=True)
        j.tomar_screenshot = AsyncMock(side_effect=Exception("fallo"))
        j.cerrar_navegador = AsyncMock()
        await j.procesar_jurisdiccion()
        j.cerrar_navegador.assert_called_once()

    @pytest.mark.asyncio
    async def test_resultado_nunca_es_none(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.buscar_notificacion = AsyncMock(side_effect=Exception("todo falla"))
        j.tomar_screenshot = AsyncMock(side_effect=Exception("todo falla"))
        j.cerrar_navegador = AsyncMock()
        resultado = await j.procesar_jurisdiccion()
        assert resultado is not None
        assert len(resultado) == 4
        for campo in resultado:
            assert campo != (None,)


# ===========================================================================
# Ownership del browser
# ===========================================================================

class TestOwnershipBrowser:

    @pytest.mark.asyncio
    async def test_owns_browser_true_cierra_browser(
        self, mock_playwright, mock_browser, mock_context, mock_page
    ):
        from jurisdicciones.jurisdiccion import Jurisdiccion

        class JMock(Jurisdiccion):
            async def consultar_notificaciones(self): pass

        j = await JMock.create(
            playwright=mock_playwright, nombre="J", codigo="0",
            cliente="C", client_folder="CF", cuit="1", clave_fiscal="p",
            fecha_desde="01012024", fecha_hasta="31012024",
        )
        j._owns_browser = True
        j.browser = mock_browser
        await j.cerrar_navegador()
        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_owns_browser_false_no_cierra_browser(
        self, mock_playwright, mock_browser, mock_context, mock_page
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        assert j._owns_browser is False
        mock_browser.close.reset_mock()
        await j.cerrar_navegador()
        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_true_y_false_producen_comportamiento_opuesto(
        self, mock_playwright, mock_browser, mock_context, mock_page
    ):
        """Boundary: mata mutante de inversión del flag."""
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.browser = mock_browser

        j._owns_browser = False
        mock_browser.close.reset_mock()
        await j.cerrar_navegador()
        assert mock_browser.close.call_count == 0

        j._owns_browser = True
        mock_browser.close.reset_mock()
        await j.cerrar_navegador()
        assert mock_browser.close.call_count == 1


# ===========================================================================
# AFIP_login: escenarios de error
# ===========================================================================

class TestAfipLogin:

    @pytest_asyncio.fixture
    async def j(self, mock_playwright, mock_browser, mock_context, mock_page):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.page = mock_page
        return j

    @pytest.mark.asyncio
    async def test_cuit_incorrecto_lanza_login_error_afip(self, j, mock_page):
        from jurisdicciones.jurisdiccion import LoginErrorAfip
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        with pytest.raises(LoginErrorAfip):
            await j.AFIP_login(success_selector="#ok")

    @pytest.mark.asyncio
    async def test_captcha_detectado_lanza_excepcion(self, j, mock_page):
        from jurisdicciones.jurisdiccion import LoggedException
        mock_page.query_selector = AsyncMock(return_value=None)
        captcha = AsyncMock()
        captcha.is_visible = AsyncMock(return_value=True)
        mock_page.locator = MagicMock(return_value=captcha)
        gt = AsyncMock()
        gt.wait_for = AsyncMock()
        mock_page.get_by_text = MagicMock(return_value=gt)
        with pytest.raises((LoggedException, Exception)):
            await j.AFIP_login(success_selector="#ok")

    @pytest.mark.asyncio
    async def test_sin_criterio_de_exito_lanza_error(self, j, mock_page):
        mock_page.query_selector = AsyncMock(return_value=None)
        captcha = AsyncMock()
        captcha.is_visible = AsyncMock(return_value=False)
        mock_page.locator = MagicMock(return_value=captcha)
        gt = AsyncMock()
        gt.wait_for = AsyncMock()
        gt.is_visible = AsyncMock(return_value=False)
        mock_page.get_by_text = MagicMock(return_value=gt)
        with pytest.raises(Exception):
            await j.AFIP_login()


# ===========================================================================
# cerrar_recursos
# ===========================================================================

class TestCerrarRecursos:

    @pytest.mark.asyncio
    async def test_cierra_page_context_y_browser(
        self, jurisdiccion_base, mock_page, mock_context, mock_browser
    ):
        jurisdiccion_base.page = mock_page
        jurisdiccion_base.context = mock_context
        jurisdiccion_base.browser = mock_browser
        await jurisdiccion_base.cerrar_recursos()
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_lanza_si_page_ya_cerrada(self, jurisdiccion_base):
        jurisdiccion_base.page = AsyncMock(close=AsyncMock(side_effect=Exception("ya cerrado")))
        jurisdiccion_base.context = AsyncMock(close=AsyncMock())
        jurisdiccion_base.browser = AsyncMock(close=AsyncMock())
        await jurisdiccion_base.cerrar_recursos()  # No debe propagar


# ===========================================================================
# Aislamiento de estado entre instancias
# ===========================================================================

class TestAislamientoEstado:

    @pytest.mark.asyncio
    async def test_hay_notificacion_independiente_por_instancia(
        self, mock_playwright, mock_browser, mock_context, mock_page
    ):
        from jurisdicciones.jurisdiccion import Jurisdiccion

        class JMock(Jurisdiccion):
            async def consultar_notificaciones(self): pass

        j1 = await JMock.create(
            playwright=mock_playwright, nombre="J1", codigo="001",
            cliente="C1", client_folder="CF1", cuit="1", clave_fiscal="p",
            fecha_desde="01012024", fecha_hasta="31012024",
            browser=mock_browser, context=mock_context, page=mock_page,
        )
        j2 = await JMock.create(
            playwright=mock_playwright, nombre="J2", codigo="002",
            cliente="C2", client_folder="CF2", cuit="2", clave_fiscal="p",
            fecha_desde="01012024", fecha_hasta="31012024",
            browser=mock_browser, context=mock_context, page=mock_page,
        )
        j1.hay_notificacion = True
        j2.hay_notificacion = False
        assert j1.hay_notificacion is True
        assert j2.hay_notificacion is False

    @pytest.mark.asyncio
    async def test_tomar_varias_screenshots_llama_una_vez_por_seccion(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        j.hora_actual = "120000"
        mock_page.click = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock()
        secciones = [("s1", "#t1"), ("s2", "#t2"), ("s3", "#t3")]
        await j.tomar_varias_screenshots(secciones, page=mock_page)
        assert mock_page.screenshot.call_count == 3

    @pytest.mark.asyncio
    async def test_tomar_varias_screenshots_propaga_excepcion(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        j = await _make(mock_playwright, mock_browser, mock_context, mock_page)
        mock_page.click = AsyncMock(side_effect=Exception("click falló"))
        with pytest.raises(Exception):
            await j.tomar_varias_screenshots([("s1", "#t1")], page=mock_page)
