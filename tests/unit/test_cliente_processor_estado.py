"""
Tests unitarios de ClienteProcessor enfocados en cómo se tratan los distintos
tipos de error (sin tocar DB ni Playwright real).

Puntos clave que se verifican:
1. `_hay_errores_en_resultados` excluye LoginError/LoginErrorAfip/DelegacionError
   del conteo de "errores técnicos", pero SÍ cuenta LoginTimeoutError como
   error técnico (es decir: un timeout de portal debe seguir generando alerta
   operativa, en vez de desaparecer silenciosamente).
2. `reintentar_errores` NO reintenta LoginError/LoginErrorAfip/DelegacionError,
   pero SÍ debe reintentar LoginTimeoutError (un timeout amerita otro intento,
   una credencial inválida no).
"""
import asyncio
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from cliente_processor import ClienteProcessor

pytestmark = pytest.mark.unit


def _make_processor(estructura_robot_tmp, df_cliente_factory):
    group = df_cliente_factory()
    return ClienteProcessor(
        cliente="Cliente Demo SA",
        group=group,
        cuit_cliente="30111111112",
        inicio=pd.Timestamp.now(),
        client_folder="cliente_demo",
        cliente_id=None,
        procesamiento_id=None,
    )


class TestHayErroresEnResultados:
    @pytest.mark.parametrize(
        "error_tipo",
        ["LoginError", "LoginErrorAfip", "DelegacionError"],
    )
    def test_errores_de_credenciales_o_delegacion_no_cuentan_como_tecnicos(
        self, estructura_robot_tmp, df_cliente_factory, error_tipo
    ):
        processor = _make_processor(estructura_robot_tmp, df_cliente_factory)
        df = pd.DataFrame(
            {
                "Nombre": ["Chaco"],
                "Notificacion": ["Credenciales inválidas"],
                "Screenshot": ["No se realizó Screenshot"],
                "Error": [error_tipo],
            }
        )
        assert processor._hay_errores_en_resultados(df) is False

    def test_login_timeout_error_si_cuenta_como_error_tecnico(
        self, estructura_robot_tmp, df_cliente_factory
    ):
        """Este es el caso crítico pedido: un timeout de portal NO debe
        desaparecer como si nada hubiera pasado; debe seguir marcando que
        hubo un problema técnico a resolver (a diferencia de LoginError)."""
        processor = _make_processor(estructura_robot_tmp, df_cliente_factory)
        df = pd.DataFrame(
            {
                "Nombre": ["Chaco"],
                "Notificacion": ["Timeout esperando confirmación de login"],
                "Screenshot": ["No se realizó Screenshot"],
                "Error": ["LoginTimeoutError"],
            }
        )
        assert processor._hay_errores_en_resultados(df) is True

    def test_sin_errores(self, estructura_robot_tmp, df_cliente_factory):
        processor = _make_processor(estructura_robot_tmp, df_cliente_factory)
        df = pd.DataFrame(
            {
                "Nombre": ["Chaco"],
                "Notificacion": [None],
                "Screenshot": ["Se realizó Screenshot"],
                "Error": [None],
            }
        )
        assert processor._hay_errores_en_resultados(df) is False


class TestReintentarErrores:
    @pytest.mark.parametrize(
        "error_tipo",
        ["LoginError", "LoginErrorAfip", "DelegacionError"],
    )
    def test_no_reintenta_errores_de_credenciales_o_delegacion(
        self, estructura_robot_tmp, df_cliente_factory, monkeypatch, error_tipo
    ):
        processor = _make_processor(estructura_robot_tmp, df_cliente_factory)
        df_final = pd.DataFrame(
            {
                "Nombre": ["Chaco"],
                "Notificacion": ["Credenciales inválidas"],
                "Screenshot": ["No se realizó Screenshot"],
                "Error": [error_tipo],
            }
        )

        crear_instancia_mock = AsyncMock()
        monkeypatch.setattr(processor, "crear_instancia_jurisdiccion", crear_instancia_mock)

        asyncio.run(processor.reintentar_errores(playwright=None, df_final=df_final))

        crear_instancia_mock.assert_not_called()

    def test_reintenta_login_timeout_error(
        self, estructura_robot_tmp, df_cliente_factory, monkeypatch
    ):
        """Un LoginTimeoutError SÍ debe generar un reintento: es exactamente
        el comportamiento que se busca al distinguirlo de LoginError."""
        processor = _make_processor(estructura_robot_tmp, df_cliente_factory)
        df_final = pd.DataFrame(
            {
                "Nombre": ["Chaco"],
                "Notificacion": ["Timeout esperando confirmación de login"],
                "Screenshot": ["No se realizó Screenshot"],
                "Error": ["LoginTimeoutError"],
            }
        )

        instancia_reintento = AsyncMock()
        instancia_reintento.procesar_jurisdiccion = AsyncMock(
            return_value=("Chaco", None, "Se realizó Screenshot", None)
        )
        crear_instancia_mock = AsyncMock(return_value=instancia_reintento)
        monkeypatch.setattr(processor, "crear_instancia_jurisdiccion", crear_instancia_mock)

        resultado = asyncio.run(
            processor.reintentar_errores(playwright=None, df_final=df_final)
        )

        crear_instancia_mock.assert_awaited()
        fila = resultado.loc[resultado["Nombre"] == "Chaco"].iloc[0]
        assert pd.isna(fila["Error"])  # se resolvió en el reintento
