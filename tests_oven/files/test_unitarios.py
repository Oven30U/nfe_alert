"""
Tests Unitarios — NFE Alert
============================
Lógica pura sin browser, sin DB, sin red.
Todo lo externo está mockeado.

Cubre:
  - Jerarquía y comportamiento de excepciones tipificadas
  - Atributos de inicialización de Jurisdiccion
  - Métodos de búsqueda (buscar_notificacion, texto_visible, xpath_visible)
  - Patrón de nombre de archivo de screenshot
  - Routing de excepciones en _ejecutar_consulta_notificaciones
  - Lógica de skip de screenshot por DelegacionError
  - Jerarquía de clases de todas las jurisdicciones
  - Parsing de variables de entorno (CLIENTES_ENVIAR_AUNQUE_ERROR, LIMITES_REINTENTO)
  - Lógica de filtrado de errores técnicos vs. credenciales
"""

import os
import sys
import pytest
import pytest_asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===========================================================================
# Excepciones tipificadas
# ===========================================================================

class TestExcepciones:

    def test_logged_exception_es_exception(self):
        from jurisdicciones.jurisdiccion import LoggedException
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoggedException("cliente", "mensaje")
        assert isinstance(exc, Exception)

    def test_logged_exception_guarda_cliente_y_mensaje(self):
        from jurisdicciones.jurisdiccion import LoggedException
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoggedException("ClienteABC", "Error X")
        assert exc.cliente == "ClienteABC"
        assert exc.message == "Error X"

    def test_logged_exception_str_devuelve_mensaje(self):
        from jurisdicciones.jurisdiccion import LoggedException
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoggedException("cliente", "mi mensaje")
        assert str(exc) == "mi mensaje"

    def test_login_error_hereda_de_logged_exception(self):
        from jurisdicciones.jurisdiccion import LoginError, LoggedException
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoginError("cliente")
        assert isinstance(exc, LoggedException)

    def test_login_error_mensaje_default(self):
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoginError("cliente")
        assert exc.message == "Credenciales inválidas"

    def test_login_error_acepta_mensaje_custom(self):
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoginError("cliente", "Error específico")
        assert exc.message == "Error específico"

    def test_login_error_afip_hereda_de_login_error(self):
        from jurisdicciones.jurisdiccion import LoginErrorAfip, LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoginErrorAfip("cliente")
        assert isinstance(exc, LoginError)

    def test_login_error_afip_mensaje_default(self):
        from jurisdicciones.jurisdiccion import LoginErrorAfip
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = LoginErrorAfip("cliente")
        assert exc.message == "Credenciales ARCA inválidas"

    def test_delegacion_error_no_es_login_error(self):
        """Crítico: DelegacionError y LoginError no son intercambiables."""
        from jurisdicciones.jurisdiccion import DelegacionError, LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = DelegacionError("cliente")
        assert not isinstance(exc, LoginError)

    def test_delegacion_error_mensaje_default(self):
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = DelegacionError("cliente")
        assert exc.message == "Servicio pendiente de delegación"

    def test_consultar_notificaciones_error_mensaje_default(self):
        from jurisdicciones.jurisdiccion import ConsultarNotificacionesError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = ConsultarNotificacionesError("cliente")
        assert exc.message == "La página se encuentra caída"

    def test_buscar_notificacion_error_mensaje_default(self):
        from jurisdicciones.jurisdiccion import BuscarNotificacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = BuscarNotificacionError("cliente")
        assert exc.message == "La página se encuentra caída"

    def test_tomar_screenshot_error_mensaje_default(self):
        from jurisdicciones.jurisdiccion import TomarScreenshotError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            exc = TomarScreenshotError("cliente")
        assert exc.message == "No hay screenshot"

    def test_todas_las_excepciones_heredan_logged_exception(self):
        from jurisdicciones.jurisdiccion import (
            LoggedException, LoginError, LoginErrorAfip,
            ConsultarNotificacionesError, BuscarNotificacionError,
            TomarScreenshotError, DelegacionError,
        )
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            for cls in [LoginError, LoginErrorAfip, ConsultarNotificacionesError,
                        BuscarNotificacionError, TomarScreenshotError, DelegacionError]:
                assert isinstance(cls("cliente"), LoggedException), (
                    f"{cls.__name__} no hereda de LoggedException"
                )


# ===========================================================================
# Inicialización de Jurisdiccion
# ===========================================================================

class TestJurisdiccionInit:

    @pytest.mark.asyncio
    async def test_atributos_basicos(self, jurisdiccion_base):
        j = jurisdiccion_base
        assert j.nombre == "TestJurisdiccion"
        assert j.codigo == "999 TEST"
        assert j.cliente == "ClienteTest"
        assert j.client_folder == "ClienteTest_Folder"

    @pytest.mark.asyncio
    async def test_cuit_se_convierte_a_string(self, jurisdiccion_base):
        assert isinstance(jurisdiccion_base._cuit, str)
        assert jurisdiccion_base._cuit == "20123456789"

    @pytest.mark.asyncio
    async def test_hay_notificacion_inicia_en_false(self, jurisdiccion_base):
        assert jurisdiccion_base.hay_notificacion is False

    @pytest.mark.asyncio
    async def test_hay_screenshot_inicia_en_false(self, jurisdiccion_base):
        assert jurisdiccion_base.hay_screenshot is False

    @pytest.mark.asyncio
    async def test_owns_browser_false_con_browser_inyectado(self, jurisdiccion_base):
        """Con browser externo inyectado, la instancia no debe cerrarlo."""
        assert jurisdiccion_base._owns_browser is False

    @pytest.mark.asyncio
    async def test_fechas_asignadas(self, jurisdiccion_base):
        assert jurisdiccion_base.fecha_desde == "01012024"
        assert jurisdiccion_base.fecha_hasta == "31012024"


# ===========================================================================
# Métodos de búsqueda
# ===========================================================================

class TestMetodosBusqueda:

    @pytest.mark.asyncio
    async def test_buscar_notificacion_retorna_true_si_elemento_existe(
        self, jurisdiccion_base, mock_page
    ):
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        assert await jurisdiccion_base.buscar_notificacion(mock_page, "texto") is True
        assert jurisdiccion_base.hay_notificacion is True

    @pytest.mark.asyncio
    async def test_buscar_notificacion_retorna_false_si_no_existe(
        self, jurisdiccion_base, mock_page
    ):
        mock_page.query_selector = AsyncMock(return_value=None)
        assert await jurisdiccion_base.buscar_notificacion(mock_page, "texto") is False
        assert jurisdiccion_base.hay_notificacion is False

    @pytest.mark.asyncio
    async def test_buscar_notificacion_true_y_false_distinguibles(
        self, jurisdiccion_base, mock_page
    ):
        """Mata hardcoded returns."""
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        r1 = await jurisdiccion_base.buscar_notificacion(mock_page, "texto")
        mock_page.query_selector = AsyncMock(return_value=None)
        r2 = await jurisdiccion_base.buscar_notificacion(mock_page, "texto")
        assert r1 != r2

    @pytest.mark.asyncio
    async def test_texto_visible_retorna_true(self, jurisdiccion_base, mock_page):
        mock_page.is_visible = AsyncMock(return_value=True)
        assert await jurisdiccion_base.buscar_notificacion_texto_visible("t", mock_page) is True

    @pytest.mark.asyncio
    async def test_texto_visible_retorna_false(self, jurisdiccion_base, mock_page):
        mock_page.is_visible = AsyncMock(return_value=False)
        assert await jurisdiccion_base.buscar_notificacion_texto_visible("t", mock_page) is False

    @pytest.mark.asyncio
    async def test_texto_visible_true_y_false_distinguibles(
        self, jurisdiccion_base, mock_page
    ):
        mock_page.is_visible = AsyncMock(return_value=True)
        r1 = await jurisdiccion_base.buscar_notificacion_texto_visible("t", mock_page)
        mock_page.is_visible = AsyncMock(return_value=False)
        r2 = await jurisdiccion_base.buscar_notificacion_texto_visible("t", mock_page)
        assert r1 is True and r2 is False

    @pytest.mark.asyncio
    async def test_xpath_visible_retorna_true(self, jurisdiccion_base, mock_page):
        mock_page.is_visible = AsyncMock(return_value=True)
        assert await jurisdiccion_base.buscar_notificacion_xpath_visible("//div", mock_page) is True

    @pytest.mark.asyncio
    async def test_xpath_visible_retorna_false(self, jurisdiccion_base, mock_page):
        mock_page.is_visible = AsyncMock(return_value=False)
        assert await jurisdiccion_base.buscar_notificacion_xpath_visible("//div", mock_page) is False

    @pytest.mark.asyncio
    async def test_xpath_none_lanza_value_error(self, jurisdiccion_base, mock_page):
        with pytest.raises(ValueError):
            await jurisdiccion_base.buscar_notificacion_xpath_visible(None, mock_page)


# ===========================================================================
# Nombre de archivo de screenshot
# ===========================================================================

class TestNombreArchivoScreenshot:

    @pytest.mark.asyncio
    async def test_patron_nombre_correcto(self, jurisdiccion_base, mock_page, env_basico):
        jurisdiccion_base.hora_actual = "120000"
        mock_page.screenshot = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        with patch("os.path.exists", return_value=False):
            await jurisdiccion_base.tomar_screenshot(page=mock_page)
        path = mock_page.screenshot.call_args.kwargs.get("path", "")
        assert "TestJurisdiccion" in path
        assert "ClienteTest_Folder" in path
        assert path.endswith(".png")

    @pytest.mark.asyncio
    async def test_fechas_con_barras_se_normalizan(
        self, mock_playwright, mock_browser, mock_context, mock_page, env_basico
    ):
        from jurisdicciones.jurisdiccion import Jurisdiccion

        class JMock(Jurisdiccion):
            async def consultar_notificaciones(self): pass

        j = await JMock.create(
            playwright=mock_playwright, nombre="J", codigo="0",
            cliente="C", client_folder="CF", cuit="1", clave_fiscal="p",
            fecha_desde="01/01/2024", fecha_hasta="31/01/2024",
            browser=mock_browser, context=mock_context, page=mock_page,
        )
        j.hora_actual = "090000"
        mock_page.screenshot = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        with patch("os.path.exists", return_value=False):
            await j.tomar_screenshot(page=mock_page)
        path = mock_page.screenshot.call_args.kwargs.get("path", "")
        assert "/" not in os.path.basename(path)

    @pytest.mark.asyncio
    async def test_contador_incrementa_si_archivo_existe(
        self, jurisdiccion_base, mock_page, env_basico
    ):
        jurisdiccion_base.hora_actual = "100000"
        mock_page.screenshot = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        with patch("os.path.exists", side_effect=[True, False]):
            await jurisdiccion_base.tomar_screenshot(page=mock_page)
        path = mock_page.screenshot.call_args.kwargs.get("path", "")
        assert "_1.png" in path


# ===========================================================================
# Routing de excepciones
# ===========================================================================

class TestRoutingExcepciones:

    @pytest.mark.asyncio
    async def test_login_error_retorna_string_correcto(self, jurisdiccion_base):
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.consultar_notificaciones = AsyncMock(
                side_effect=LoginError("cliente")
            )
        assert await jurisdiccion_base._ejecutar_consulta_notificaciones() == "LoginError"

    @pytest.mark.asyncio
    async def test_login_error_no_retorna_delegacion(self, jurisdiccion_base):
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.consultar_notificaciones = AsyncMock(
                side_effect=LoginError("cliente")
            )
        result = await jurisdiccion_base._ejecutar_consulta_notificaciones()
        assert result != "DelegacionError"
        assert result != "ConsultarNotificacionesError"

    @pytest.mark.asyncio
    async def test_delegacion_error_retorna_string_correcto(self, jurisdiccion_base):
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.consultar_notificaciones = AsyncMock(
                side_effect=DelegacionError("cliente")
            )
        assert await jurisdiccion_base._ejecutar_consulta_notificaciones() == "DelegacionError"

    @pytest.mark.asyncio
    async def test_delegacion_no_retorna_login_error(self, jurisdiccion_base):
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.consultar_notificaciones = AsyncMock(
                side_effect=DelegacionError("cliente")
            )
        assert await jurisdiccion_base._ejecutar_consulta_notificaciones() != "LoginError"

    @pytest.mark.asyncio
    async def test_consultar_error_retorna_string_correcto(self, jurisdiccion_base):
        from jurisdicciones.jurisdiccion import ConsultarNotificacionesError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.consultar_notificaciones = AsyncMock(
                side_effect=ConsultarNotificacionesError("cliente")
            )
        assert await jurisdiccion_base._ejecutar_consulta_notificaciones() == "ConsultarNotificacionesError"

    @pytest.mark.asyncio
    async def test_sin_error_retorna_none(self, jurisdiccion_base):
        jurisdiccion_base.consultar_notificaciones = AsyncMock()
        assert await jurisdiccion_base._ejecutar_consulta_notificaciones() is None

    @pytest.mark.asyncio
    async def test_excepcion_generica_mapea_a_consultar_error(self, jurisdiccion_base):
        jurisdiccion_base.consultar_notificaciones = AsyncMock(
            side_effect=RuntimeError("error inesperado")
        )
        assert await jurisdiccion_base._ejecutar_consulta_notificaciones() == "ConsultarNotificacionesError"


# ===========================================================================
# Skip de screenshot por DelegacionError
# ===========================================================================

class TestSkipScreenshotDelegacion:

    @pytest.mark.asyncio
    async def test_delegacion_no_llama_tomar_screenshot(self, jurisdiccion_base):
        """Mutante crítico: inversión de 'in errores_sin_screenshot'."""
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.error = DelegacionError("cliente")
        jurisdiccion_base.tomar_screenshot = AsyncMock(return_value=True)
        await jurisdiccion_base._ejecutar_tomar_screenshot()
        jurisdiccion_base.tomar_screenshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_delegacion_establece_mensaje_de_skip(self, jurisdiccion_base):
        from jurisdicciones.jurisdiccion import DelegacionError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.error = DelegacionError("cliente")
        await jurisdiccion_base._ejecutar_tomar_screenshot()
        assert isinstance(jurisdiccion_base.hay_screenshot, str)
        assert len(jurisdiccion_base.hay_screenshot) > 0

    @pytest.mark.asyncio
    async def test_login_error_si_llama_tomar_screenshot(self, jurisdiccion_base):
        """LoginError NO está en errores_sin_screenshot."""
        from jurisdicciones.jurisdiccion import LoginError
        with patch("jurisdicciones.jurisdiccion.Logger") as ml:
            ml.get_logger.return_value = MagicMock()
            jurisdiccion_base.error = LoginError("cliente")
        jurisdiccion_base.tomar_screenshot = AsyncMock(return_value=True)
        await jurisdiccion_base._ejecutar_tomar_screenshot()
        jurisdiccion_base.tomar_screenshot.assert_called()

    @pytest.mark.asyncio
    async def test_sin_error_llama_tomar_screenshot(self, jurisdiccion_base):
        jurisdiccion_base.error = None
        jurisdiccion_base.tomar_screenshot = AsyncMock(return_value=True)
        await jurisdiccion_base._ejecutar_tomar_screenshot()
        jurisdiccion_base.tomar_screenshot.assert_called_once()


# ===========================================================================
# Jerarquía de clases de jurisdicción
# ===========================================================================

MODULO_MAP = {
    "Agip": "agip", "Arba": "arba", "Catamarca": "catamarca",
    "Chaco": "chaco", "Chubut": "chubut", "Cordoba": "cordoba",
    "Corrientes": "corrientes", "EntreRios": "entre_rios",
    "Formosa": "formosa", "Jujuy": "jujuy", "LaPampa": "la_pampa",
    "LaRioja": "la_rioja", "Mendoza": "mendoza", "Misiones": "misiones",
    "Nacional": "nacional", "Neuquen": "neuquen", "RioNegro": "rio_negro",
    "Salta": "salta", "SanJuan": "san_juan", "SanLuis": "san_luis",
    "SantaCruz": "santa_cruz", "SantiagoDelEstero": "santiago_del_estero",
    "Sicnea": "sicnea", "Tucuman": "tucuman",
}


class TestJerarquiaJurisdicciones:

    @pytest.mark.parametrize("clase_nombre,modulo_nombre", MODULO_MAP.items())
    def test_clase_hereda_de_jurisdiccion(self, clase_nombre, modulo_nombre):
        from jurisdicciones.jurisdiccion import Jurisdiccion
        mod = importlib.import_module(f"jurisdicciones.{modulo_nombre}")
        clase = getattr(mod, clase_nombre, None)
        assert clase is not None, f"Clase {clase_nombre} no encontrada"
        assert issubclass(clase, Jurisdiccion), f"{clase_nombre} no hereda de Jurisdiccion"

    @pytest.mark.parametrize("clase_nombre,modulo_nombre", MODULO_MAP.items())
    def test_clase_implementa_consultar_notificaciones(self, clase_nombre, modulo_nombre):
        mod = importlib.import_module(f"jurisdicciones.{modulo_nombre}")
        clase = getattr(mod, clase_nombre)
        assert hasattr(clase, "consultar_notificaciones")
        assert callable(getattr(clase, "consultar_notificaciones"))

    @pytest.mark.parametrize("clase_nombre,modulo_nombre", MODULO_MAP.items())
    def test_clase_tiene_create_y_procesar(self, clase_nombre, modulo_nombre):
        mod = importlib.import_module(f"jurisdicciones.{modulo_nombre}")
        clase = getattr(mod, clase_nombre)
        assert hasattr(clase, "create") and callable(clase.create)
        assert hasattr(clase, "procesar_jurisdiccion") and callable(clase.procesar_jurisdiccion)


# ===========================================================================
# Parsing de variables de entorno
# ===========================================================================

class TestParsingEnvVars:

    def test_clientes_enviar_aunque_error_lista_vacia(self, monkeypatch):
        monkeypatch.setenv("CLIENTES_ENVIAR_AUNQUE_ERROR", "")
        with patch("cliente_processor.Logger") as ml, patch("cliente_processor.conectar_db"):
            ml.get_logger.return_value = MagicMock()
            import cliente_processor
            importlib.reload(cliente_processor)
            assert len(cliente_processor.CLIENTES_ENVIAR_AUNQUE_ERROR_LIST) == 0

    def test_clientes_enviar_aunque_error_varios(self, monkeypatch):
        monkeypatch.setenv("CLIENTES_ENVIAR_AUNQUE_ERROR", "Cliente1,Cliente2,Cliente3")
        with patch("cliente_processor.Logger") as ml, patch("cliente_processor.conectar_db"):
            ml.get_logger.return_value = MagicMock()
            import cliente_processor
            importlib.reload(cliente_processor)
            lista = cliente_processor.CLIENTES_ENVIAR_AUNQUE_ERROR_LIST
        assert len(lista) == 3
        assert "Cliente1" in lista and "Cliente2" in lista and "Cliente3" in lista

    def test_clientes_enviar_aunque_error_strip_espacios(self, monkeypatch):
        monkeypatch.setenv("CLIENTES_ENVIAR_AUNQUE_ERROR", " Cliente1 , Cliente2 ")
        with patch("cliente_processor.Logger") as ml, patch("cliente_processor.conectar_db"):
            ml.get_logger.return_value = MagicMock()
            import cliente_processor
            importlib.reload(cliente_processor)
            lista = cliente_processor.CLIENTES_ENVIAR_AUNQUE_ERROR_LIST
        assert "Cliente1" in lista and "Cliente2" in lista
        assert " Cliente1 " not in lista

    def test_limites_reintento_default_es_5(self, monkeypatch):
        monkeypatch.delenv("LIMITES_REINTENTO", raising=False)
        with patch("cliente_processor.Logger") as ml, patch("cliente_processor.conectar_db"):
            ml.get_logger.return_value = MagicMock()
            import cliente_processor
            importlib.reload(cliente_processor)
            assert cliente_processor.LIMITES_REINTENTO == 5

    def test_limites_reintento_se_parsea_como_int(self, monkeypatch):
        monkeypatch.setenv("LIMITES_REINTENTO", "3")
        with patch("cliente_processor.Logger") as ml, patch("cliente_processor.conectar_db"):
            ml.get_logger.return_value = MagicMock()
            import cliente_processor
            importlib.reload(cliente_processor)
            assert isinstance(cliente_processor.LIMITES_REINTENTO, int)
            assert cliente_processor.LIMITES_REINTENTO == 3


# ===========================================================================
# Filtrado de errores técnicos vs. credenciales
# ===========================================================================

class TestFiltradoErroresTecnicos:

    def _processor(self, monkeypatch):
        monkeypatch.setenv("PATH_ESTRUCTURA_ROBOT", "/tmp/nfe_test")
        monkeypatch.setenv("CORREO_NOTIFICACION_ERROR", "test@test.com")
        monkeypatch.setenv("CORREO_TEST", "test@test.com")
        monkeypatch.setenv("ENVIAR_CORREO_TEST", "false")
        os.makedirs("/tmp/nfe_test/CF/Output", exist_ok=True)
        os.makedirs("/tmp/nfe_test/CF/Backup", exist_ok=True)
        import pandas as pd
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
                inicio=__import__("datetime").datetime.now(), client_folder="CF",
            )

    def test_error_tecnico_retorna_true(self, monkeypatch):
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Cordoba"], "Error": ["ConsultarNotificacionesError"]})
        assert p._hay_errores_en_resultados(df) is True

    def test_sin_errores_retorna_false(self, monkeypatch):
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Cordoba"], "Error": [None]})
        assert p._hay_errores_en_resultados(df) is False

    def test_login_error_no_es_error_tecnico(self, monkeypatch):
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Nacional"], "Error": ["LoginError"]})
        assert p._hay_errores_en_resultados(df) is False

    def test_login_error_afip_no_es_error_tecnico(self, monkeypatch):
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Nacional"], "Error": ["LoginErrorAfip"]})
        assert p._hay_errores_en_resultados(df) is False

    def test_delegacion_error_no_es_error_tecnico(self, monkeypatch):
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Cordoba"], "Error": ["DelegacionError"]})
        assert p._hay_errores_en_resultados(df) is False

    def test_tecnico_y_no_tecnico_distinguibles(self, monkeypatch):
        """Boundary: los dos casos deben retornar valores opuestos."""
        import pandas as pd
        p = self._processor(monkeypatch)
        df_t = pd.DataFrame({"Nombre": ["Cordoba"], "Error": ["TomarScreenshotError"]})
        df_n = pd.DataFrame({"Nombre": ["Nacional"], "Error": ["LoginError"]})
        assert p._hay_errores_en_resultados(df_t) is True
        assert p._hay_errores_en_resultados(df_n) is False

    def test_jurisdiccion_deshabilitada_excluida(self, monkeypatch):
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Cordoba"], "Error": ["ConsultarNotificacionesError"]})
        with patch.dict(os.environ, {"JURISDICCIONES_DESHABILITADAS": "Cordoba"}):
            assert p._hay_errores_en_resultados(df) is False

    def test_jurisdiccion_no_deshabilitada_sigue_contando(self, monkeypatch):
        import pandas as pd
        p = self._processor(monkeypatch)
        df = pd.DataFrame({"Nombre": ["Cordoba"], "Error": ["ConsultarNotificacionesError"]})
        with patch.dict(os.environ, {"JURISDICCIONES_DESHABILITADAS": ""}):
            assert p._hay_errores_en_resultados(df) is True
