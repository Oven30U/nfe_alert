from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest


def construir_processor_sin_init(group):
    from cliente_processor import ClienteProcessor

    processor = object.__new__(ClienteProcessor)
    processor.group = group
    processor.cliente_id = None
    processor.client_folder = "qa"
    processor.output_folder = "."
    processor.renombrar_screenshots_error = MagicMock()
    processor.eliminar_screenshots_errores = MagicMock()
    processor.limpiar_screenshots_errores = MagicMock()
    return processor


@pytest.mark.integration
@pytest.mark.credentials
@pytest.mark.asyncio
async def test_login_error_no_se_reintenta():
    group = pd.DataFrame([{"Jurisdiccion": "Agip"}])
    processor = construir_processor_sin_init(group)
    processor.crear_instancia_jurisdiccion = AsyncMock()

    df = pd.DataFrame(
        [{
            "Nombre": "Agip",
            "Notificacion": "Credenciales inválidas",
            "Screenshot": "No se realizó Screenshot",
            "Error": "LoginError",
        }]
    )

    resultado = await processor.reintentar_errores(MagicMock(), df)

    processor.crear_instancia_jurisdiccion.assert_not_awaited()
    assert resultado.iloc[0]["Error"] == "LoginError"


@pytest.mark.integration
@pytest.mark.timeout
@pytest.mark.asyncio
async def test_error_tecnico_si_se_reintenta():
    group = pd.DataFrame([{"Jurisdiccion": "Agip"}])
    processor = construir_processor_sin_init(group)

    instancia = MagicMock()
    instancia.procesar_jurisdiccion = AsyncMock(
        return_value=("Agip", False, "Se realizó Screenshot", None)
    )
    processor.crear_instancia_jurisdiccion = AsyncMock(return_value=instancia)

    df = pd.DataFrame(
        [{
            "Nombre": "Agip",
            "Notificacion": "La página se encuentra caída",
            "Screenshot": "No se realizó Screenshot",
            "Error": "PlaywrightTimeoutError",
        }]
    )

    resultado = await processor.reintentar_errores(MagicMock(), df)

    processor.crear_instancia_jurisdiccion.assert_awaited()
    assert pd.isna(resultado.iloc[0]["Error"])


@pytest.mark.integration
@pytest.mark.timeout
@pytest.mark.known_issue
@pytest.mark.xfail(
    reason=(
        "Cuando AGIP convierte un timeout en LoginError, ClienteProcessor no "
        "reintenta y puede persistir fecha_login_error como si fueran credenciales."
    ),
    strict=True,
)
@pytest.mark.asyncio
async def test_timeout_mal_clasificado_no_deberia_bloquear_reintento():
    group = pd.DataFrame([{"Jurisdiccion": "Agip"}])
    processor = construir_processor_sin_init(group)
    processor.crear_instancia_jurisdiccion = AsyncMock()

    df = pd.DataFrame(
        [{
            "Nombre": "Agip",
            "Notificacion": "Credenciales inválidas",
            "Screenshot": "No se realizó Screenshot",
            "Error": "LoginError",
        }]
    )

    await processor.reintentar_errores(MagicMock(), df)

    # Requisito esperado para un timeout real: debería haber reintento.
    processor.crear_instancia_jurisdiccion.assert_awaited()
