"""
Tests de Mutación — NFE Alert
==============================
Tests diseñados específicamente para matar mutantes de alta prioridad.

A diferencia de los tests unitarios (que verifican comportamiento correcto),
estos tests verifican los LÍMITES EXACTOS de cada condición: el valor que
separa un caso del otro. Un mutante que cambia == por !=, o True por False,
o elimina un raise, debe ser detectado aquí.

Cada clase de test corresponde a un grupo de mutantes en un módulo específico.
El comentario "# Mutante:" indica exactamente qué cambio en el código mataría.

Configuración de mutmut:
  mutmut run --paths-to-mutate nfe_alert/jurisdicciones/jurisdiccion.py
  mutmut run --paths-to-mutate nfe_alert/cliente_processor.py

Umbrales objetivo:
  jurisdiccion.py      >= 80% mutation score
  cliente_processor.py >= 65% mutation score
"""

import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===========================================================================
# Mutantes en la jerarquía de excepciones
# ===========================================================================

class TestMutantesExcepciones:
    """
    Grupo de mutantes: cambios en isinstance(), herencia, mensajes default.
    """

    def _exc(self, cls, *args):
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            return cls(*args)

    def test_delegacion_no_es_login_error_ambos_sentidos(self):
        """
        Mutante: cambiar la clase base de DelegacionError a LoginError.
        Verificamos ambos sentidos para no dejar escape al mutante.
        """
        from jurisdicciones.jurisdiccion import DelegacionError, LoginError, LoggedException
        exc = self._exc(DelegacionError, "cliente")
        assert isinstance(exc, LoggedException)   # sí es LoggedException
        assert not isinstance(exc, LoginError)    # NO es LoginError

    def test_login_error_afip_si_es_login_error(self):
        """Mutante: quitar herencia de LoginErrorAfip a LoginError."""
        from jurisdicciones.jurisdiccion import LoginErrorAfip, LoginError
        exc = self._exc(LoginErrorAfip, "cliente")
        assert isinstance(exc, LoginError)

    def test_mensaje_delegacion_no_es_credenciales_invalidas(self):
        """
        Mutante: reemplazar el mensaje de DelegacionError por el de LoginError.
        Los mensajes de estas dos excepciones deben ser distintos.
        """
        from jurisdicciones.jurisdiccion import DelegacionError, LoginError
        exc_d = self._exc(DelegacionError, "cliente")
        exc_l = self._exc(LoginError, "cliente")
        assert exc_d.message != exc_l.message

    def test_mensaje_delegacion_contiene_delegacion(self):
        """Mutante: string incorrecto en DEFAULT_MESSAGE."""
        from jurisdicciones.jurisdiccion import DelegacionError
        exc = self._exc(DelegacionError, "cliente")
        assert "delegación" in exc.message.lower() or "delegacion" in exc.message.lower()

    def test_mensaje_afip_contiene_arca(self):
        """Mutante: string incorrecto en LoginErrorAfip.DEFAULT_MESSAGE."""
        from jurisdicciones.jurisdiccion import LoginErrorAfip
        exc = self._exc(LoginErrorAfip, "cliente")
        assert "arca" in exc.message.lower() or "credenciales" in exc.message.lower()

    def test_str_excepcion_es_mensaje_no_repr(self):
        """
        Mutante: __str__ retorna repr() en lugar de self.message.
        El repr de una excepción incluye el nombre de la clase.
        """
        from jurisdicciones.jurisdiccion import LoginError
        exc = self._exc(LoginError, "cliente", "mi mensaje preciso")
        resultado = str(exc)
        assert resultado == "mi mensaje preciso"
        assert "LoginError" not in resultado


# ===========================================================================
# Mutantes en routing de _ejecutar_consulta_notificaciones
# ===========================================================================

class TestMutantesRouting:
    """
    Mutantes objetivo:
      - Intercambio de strings de retorno entre excepciones
      - Captura de la excepción equivocada
      - Retorno de None en lugar de string en error
      - Retorno de string en lugar de None en camino feliz
    """

    @pytest.mark.asyncio
    async def test_routing_completo_sin_confusion(self, jurisdiccion_base):
        """
        Ejecuta todos los tipos de excepción y verifica que cada uno
        produce el string correcto.

        Nota: LoginErrorAfip hereda de LoginError, por lo que el bloque
        except LoginError lo captura primero — ese es el comportamiento
        real del código. El test verifica que sigue produciendo "LoginError"
        (no None ni DelegacionError).
        """
        from jurisdicciones.jurisdiccion import (
            LoginError, LoginErrorAfip, DelegacionError,
            ConsultarNotificacionesError,
        )

        # LoginErrorAfip hereda de LoginError → capturado por el bloque LoginError
        casos = [
            (LoginError,                   "LoginError"),
            (LoginErrorAfip,               "LoginError"),      # capturado por LoginError
            (DelegacionError,              "DelegacionError"),
            (ConsultarNotificacionesError, "ConsultarNotificacionesError"),
        ]

        for ExcClass, expected in casos:
            with patch("jurisdicciones.jurisdiccion.Logger") as ml:
                ml.get_logger.return_value = MagicMock()
                jurisdiccion_base.consultar_notificaciones = AsyncMock(
                    side_effect=ExcClass("cliente")
                )
            result = await jurisdiccion_base._ejecutar_consulta_notificaciones()
            assert result == expected, (
                f"{ExcClass.__name__} debería retornar '{expected}' pero retornó '{result}'"
            )

    @pytest.mark.asyncio
    async def test_ninguna_excepcion_retorna_none(self, jurisdiccion_base):
        """Mutante: retornar None en el camino de error."""
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.consultar_notificaciones = AsyncMock(
                side_effect=LoginError("cliente")
            )
        result = await jurisdiccion_base._ejecutar_consulta_notificaciones()
        assert result is not None

    @pytest.mark.asyncio
    async def test_camino_feliz_retorna_exactamente_none(self, jurisdiccion_base):
        """Mutante: retornar string vacío o False en el camino feliz."""
        jurisdiccion_base.consultar_notificaciones = AsyncMock()
        result = await jurisdiccion_base._ejecutar_consulta_notificaciones()
        assert result is None
        # Verificar que no sea False, "", 0, o cualquier otro falsy
        assert result is None  # explícito: None, no solo falsy


# ===========================================================================
# Mutantes en _ejecutar_tomar_screenshot
# ===========================================================================

class TestMutantesSkipScreenshot:
    """
    Mutante crítico: si se invierte 'in errores_sin_screenshot' o se
    saca DelegacionError de la lista, el sistema tomaría capturas de
    CUITs no autorizados.
    """

    @pytest.mark.asyncio
    async def test_solo_delegacion_salta_screenshot(self, jurisdiccion_base):
        """
        Verifica que DelegacionError es el ÚNICO tipo que salta el screenshot.
        Probamos todos los demás tipos para asegurar que ninguno hace skip.
        """
        from jurisdicciones.jurisdiccion import (
            LoginError, LoginErrorAfip, ConsultarNotificacionesError,
            TomarScreenshotError, BuscarNotificacionError,
        )

        tipos_que_si_usan_screenshot = [
            LoginError, LoginErrorAfip, ConsultarNotificacionesError,
        ]

        for ExcClass in tipos_que_si_usan_screenshot:
            with patch("jurisdicciones.jurisdiccion.Logger") as ml:
                ml.get_logger.return_value = MagicMock()
                jurisdiccion_base.error = ExcClass("cliente")

            jurisdiccion_base.tomar_screenshot = AsyncMock(return_value=True)
            await jurisdiccion_base._ejecutar_tomar_screenshot()
            assert jurisdiccion_base.tomar_screenshot.called, (
                f"{ExcClass.__name__} no debería saltar el screenshot pero lo saltó"
            )

    @pytest.mark.asyncio
    async def test_delegacion_nunca_llama_screenshot(self, jurisdiccion_base):
        """El caso contrario: DelegacionError NUNCA llama tomar_screenshot."""
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.error = DelegacionError("cliente")
        jurisdiccion_base.tomar_screenshot = AsyncMock(return_value=True)
        await jurisdiccion_base._ejecutar_tomar_screenshot()
        jurisdiccion_base.tomar_screenshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_boundary_delegacion_vs_login_en_mismo_test(self, jurisdiccion_base):
        """
        Boundary en un solo test: con DelegacionError no llama, con LoginError llama.
        Un mutante que invierta la condición fallará en uno de los dos asserts.
        """
        from jurisdicciones.jurisdiccion import DelegacionError, LoginError

        # Con DelegacionError: NO debe llamar
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.error = DelegacionError("cliente")
        jurisdiccion_base.tomar_screenshot = AsyncMock(return_value=True)
        await jurisdiccion_base._ejecutar_tomar_screenshot()
        count_delegacion = jurisdiccion_base.tomar_screenshot.call_count
        assert count_delegacion == 0

        # Con LoginError: SÍ debe llamar
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.error = LoginError("cliente")
        jurisdiccion_base.tomar_screenshot = AsyncMock(return_value=True)
        await jurisdiccion_base._ejecutar_tomar_screenshot()
        count_login = jurisdiccion_base.tomar_screenshot.call_count
        assert count_login == 1


# ===========================================================================
# Mutantes en ownership del browser
# ===========================================================================

class TestMutantesOwnership:
    """
    Mutante: cambiar 'if _owns_browser' por 'if not _owns_browser'.
    """

    @pytest.mark.asyncio
    async def test_boundary_owns_browser(
        self, mock_playwright, mock_browser, mock_context, mock_page
    ):
        """
        Test de boundary puro: True cierra, False no cierra.
        Si se invierte la condición, ambos asserts no pueden pasar juntos.
        """
        from jurisdicciones.jurisdiccion import Jurisdiccion

        class JMock(Jurisdiccion):
            async def consultar_notificaciones(self): pass

        j = await JMock.create(
            playwright=mock_playwright, nombre="J", codigo="0",
            cliente="C", client_folder="CF", cuit="1", clave_fiscal="p",
            fecha_desde="01012024", fecha_hasta="31012024",
        )
        j.browser = mock_browser

        # _owns_browser = False → NO cierra
        j._owns_browser = False
        mock_browser.close.reset_mock()
        await j.cerrar_navegador()
        assert mock_browser.close.call_count == 0, "Con False no debería cerrar"

        # _owns_browser = True → SÍ cierra
        j._owns_browser = True
        mock_browser.close.reset_mock()
        await j.cerrar_navegador()
        assert mock_browser.close.call_count == 1, "Con True debería cerrar"


# ===========================================================================
# Mutantes en la búsqueda de notificaciones
# ===========================================================================

class TestMutantesBusqueda:
    """
    Mutantes: inversión de is not None / is None, hardcoded return values.
    """

    @pytest.mark.asyncio
    async def test_boundary_elemento_presente_vs_ausente(
        self, jurisdiccion_base, mock_page
    ):
        """
        Boundary en un solo test: con elemento retorna True, sin elemento False.
        Un mutante que hardcodee True o False fallará en uno de los dos.
        """
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        r_presente = await jurisdiccion_base.buscar_notificacion(mock_page, "t")

        mock_page.query_selector = AsyncMock(return_value=None)
        r_ausente = await jurisdiccion_base.buscar_notificacion(mock_page, "t")

        assert r_presente is True
        assert r_ausente is False
        assert r_presente != r_ausente

    @pytest.mark.asyncio
    async def test_boundary_texto_visible_vs_invisible(
        self, jurisdiccion_base, mock_page
    ):
        mock_page.is_visible = AsyncMock(return_value=True)
        r_visible = await jurisdiccion_base.buscar_notificacion_texto_visible("t", mock_page)

        mock_page.is_visible = AsyncMock(return_value=False)
        r_invisible = await jurisdiccion_base.buscar_notificacion_texto_visible("t", mock_page)

        assert r_visible is True
        assert r_invisible is False

    @pytest.mark.asyncio
    async def test_boundary_xpath_visible_vs_invisible(
        self, jurisdiccion_base, mock_page
    ):
        mock_page.is_visible = AsyncMock(return_value=True)
        r1 = await jurisdiccion_base.buscar_notificacion_xpath_visible("//x", mock_page)

        mock_page.is_visible = AsyncMock(return_value=False)
        r2 = await jurisdiccion_base.buscar_notificacion_xpath_visible("//x", mock_page)

        assert r1 is True
        assert r2 is False

    @pytest.mark.asyncio
    async def test_xpath_none_no_devuelve_false_silenciosamente(
        self, jurisdiccion_base, mock_page
    ):
        """Mutante: convertir raise ValueError en return False."""
        with pytest.raises(Exception):
            await jurisdiccion_base.buscar_notificacion_xpath_visible(None, mock_page)


# ===========================================================================
# Mutantes en filtrado de errores técnicos (cliente_processor.py)
# ===========================================================================

class TestMutantesFiltradoErrores:
    """
    Mutante crítico: cambiar '~isin' por 'isin' en el filtro de errores excluidos.
    Si se invierte, LoginError se trataría como error técnico y bloquearía el correo.
    """

    def _processor(self, monkeypatch):
        import datetime, pandas as pd
        monkeypatch.setenv("PATH_ESTRUCTURA_ROBOT", "/tmp/nfe_test")
        monkeypatch.setenv("CORREO_NOTIFICACION_ERROR", "t@t.com")
        monkeypatch.setenv("CORREO_TEST", "t@t.com")
        monkeypatch.setenv("ENVIAR_CORREO_TEST", "false")
        os.makedirs("/tmp/nfe_test/CF/Output", exist_ok=True)
        os.makedirs("/tmp/nfe_test/CF/Backup", exist_ok=True)
        with patch("cliente_processor.conectar_db"), \
             patch("cliente_processor.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            from cliente_processor import ClienteProcessor
            group = pd.DataFrame({
                "Jurisdiccion": ["Nacional"],
                "Correo Output": ["c@t.com"],
                "CC: Equipo Deloitte": ["cc@t.com"],
            })
            return ClienteProcessor(
                cliente="C", group=group, cuit_cliente="1",
                inicio=datetime.datetime.now(), client_folder="CF",
            )

    def test_boundary_tecnico_vs_credenciales(self, monkeypatch):
        """
        Boundary en un solo test: error técnico retorna True, error de
        credenciales retorna False. Si se invierte ~isin, ambos cambiarían.
        """
        import pandas as pd
        p = self._processor(monkeypatch)

        # Error técnico → True
        df_t = pd.DataFrame({"Nombre": ["C"], "Error": ["ConsultarNotificacionesError"]})
        assert p._hay_errores_en_resultados(df_t) is True

        # Error de credenciales → False
        df_c = pd.DataFrame({"Nombre": ["C"], "Error": ["LoginError"]})
        assert p._hay_errores_en_resultados(df_c) is False

    def test_los_tres_errores_excluidos_son_distintos_de_tecnico(self, monkeypatch):
        """
        Verifica individualmente que LoginError, LoginErrorAfip y DelegacionError
        no se tratan como errores técnicos. Un mutante que saque uno de los tres
        de la lista fallará en el assert correspondiente.
        """
        import pandas as pd
        p = self._processor(monkeypatch)

        for error in ["LoginError", "LoginErrorAfip", "DelegacionError"]:
            df = pd.DataFrame({"Nombre": ["C"], "Error": [error]})
            result = p._hay_errores_en_resultados(df)
            assert result is False, (
                f"'{error}' fue tratado como error técnico (debería ser False)"
            )

    def test_boundary_con_y_sin_jurisdiccion_deshabilitada(self, monkeypatch):
        """
        Boundary: misma jurisdicción con error técnico — deshabilitada retorna False,
        habilitada retorna True. Mata mutante de inversión del filtro ~isin.
        """
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Cordoba"], "Error": ["ConsultarNotificacionesError"]})

        with patch.dict(os.environ, {"JURISDICCIONES_DESHABILITADAS": "Cordoba"}):
            assert p._hay_errores_en_resultados(df) is False

        with patch.dict(os.environ, {"JURISDICCIONES_DESHABILITADAS": ""}):
            assert p._hay_errores_en_resultados(df) is True


# ===========================================================================
# Mutantes en no terminación silenciosa
# ===========================================================================

class TestMutantesNoTerminacionSilenciosa:
    """
    Mutante: retornar None en algún campo del tuple de resultado.
    """

    @pytest.mark.asyncio
    async def test_todos_los_campos_definidos_en_error_total(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        """
        Incluso si consultar, buscar y screenshot fallan, los 4 campos
        deben estar definidos y ser distintos de (None,) — el valor inicial.
        """
        from jurisdicciones.jurisdiccion import Jurisdiccion

        class JMock(Jurisdiccion):
            async def consultar_notificaciones(self):
                raise RuntimeError("todo falla")

        j = await JMock.create(
            playwright=mock_playwright, nombre="JTotal", codigo="000",
            cliente="C", client_folder="CF", cuit="1", clave_fiscal="p",
            fecha_desde="01012024", fecha_hasta="31012024",
            browser=mock_browser, context=mock_context, page=mock_page,
        )
        j.tomar_screenshot = AsyncMock(side_effect=Exception("fallo"))
        j.cerrar_navegador = AsyncMock()

        resultado = await j.procesar_jurisdiccion()
        nombre, notif, screenshot, error = resultado

        assert nombre is not None and nombre == "JTotal"
        assert notif is not None and notif is not (None,)
        assert screenshot is not None and screenshot is not (None,)
        # error puede ser None (camino feliz) o string — pero nunca (None,)
        assert error is not (None,)

    @pytest.mark.asyncio
    async def test_nombre_siempre_presente_independiente_del_error(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        """El primer campo del tuple SIEMPRE debe ser el nombre de la jurisdicción."""
        from jurisdicciones.jurisdiccion import Jurisdiccion

        class JMock(Jurisdiccion):
            async def consultar_notificaciones(self):
                raise RuntimeError("fallo crítico")

        j = await JMock.create(
            playwright=mock_playwright, nombre="NombreEsperado", codigo="0",
            cliente="C", client_folder="CF", cuit="1", clave_fiscal="p",
            fecha_desde="01012024", fecha_hasta="31012024",
            browser=mock_browser, context=mock_context, page=mock_page,
        )
        j.cerrar_navegador = AsyncMock()
        nombre, *_ = await j.procesar_jurisdiccion()
        assert nombre == "NombreEsperado"


# ===========================================================================
# Configuración: verificar que mutmut.toml existe y apunta a los módulos correctos
# ===========================================================================

class TestConfiguracionMutmut:

    def test_mutmut_toml_existe(self):
        raiz = os.path.join(os.path.dirname(__file__), "..")
        assert os.path.exists(os.path.join(raiz, "mutmut.toml")), (
            "mutmut.toml no encontrado en la raíz del proyecto"
        )

    def test_mutmut_toml_incluye_modulos_criticos(self):
        raiz = os.path.join(os.path.dirname(__file__), "..")
        ruta = os.path.join(raiz, "mutmut.toml")
        if not os.path.exists(ruta):
            pytest.skip("mutmut.toml no existe")
        with open(ruta) as f:
            contenido = f.read()
        assert "jurisdiccion" in contenido
        assert "cliente_processor" in contenido
