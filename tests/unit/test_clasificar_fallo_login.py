"""
Tests unitarios de Jurisdiccion.clasificar_fallo_login (jurisdicciones/jurisdiccion.py).

Este es el mecanismo que el propio repo ya provee para NO confundir un
timeout de portal con credenciales inválidas: sólo debe levantar LoginError
si efectivamente encuentra un selector de error explícito en la página; si
no encuentra nada, debe levantar LoginTimeoutError.

Se usa un mock de Page (AsyncMock) para no depender de un browser real:
esto los hace rápidos y 100% deterministas.
"""
from unittest.mock import AsyncMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from jurisdicciones.jurisdiccion import LoginError, LoginTimeoutError

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_sin_selector_de_error_visible_clasifica_como_timeout(make_jurisdiccion_fake):
    """Si ningún selector de error de credenciales aparece en la ventana de
    verificación, se debe asumir portal caído/lento, NO credenciales."""
    page = AsyncMock()
    page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeoutError("no aparece"))
    jurisdiccion = make_jurisdiccion_fake(page=page)

    with pytest.raises(LoginTimeoutError):
        await jurisdiccion.clasificar_fallo_login(
            error_selectors=[":has-text('Usuario o clave incorrecta')"]
        )


@pytest.mark.asyncio
async def test_selector_de_error_visible_clasifica_como_credenciales(make_jurisdiccion_fake):
    """Si el selector de error de credenciales SÍ aparece, ahí sí es un
    LoginError legítimo."""
    page = AsyncMock()
    page.wait_for_selector = AsyncMock(return_value=object())  # elemento encontrado
    jurisdiccion = make_jurisdiccion_fake(page=page)

    with pytest.raises(LoginError) as exc_info:
        await jurisdiccion.clasificar_fallo_login(
            error_selectors=[":has-text('Usuario o clave incorrecta')"]
        )
    assert not isinstance(exc_info.value, LoginTimeoutError)


@pytest.mark.asyncio
async def test_sin_error_selectors_configurados_clasifica_como_timeout(make_jurisdiccion_fake):
    """Si la jurisdicción no pasa ningún selector de error (lista vacía/None),
    nunca podrá confirmar credenciales inválidas, así que debe optar
    siempre por el camino seguro: LoginTimeoutError."""
    page = AsyncMock()
    jurisdiccion = make_jurisdiccion_fake(page=page)

    with pytest.raises(LoginTimeoutError):
        await jurisdiccion.clasificar_fallo_login(error_selectors=None)

    page.wait_for_selector.assert_not_called()


@pytest.mark.asyncio
async def test_primer_selector_falla_segundo_confirma_credenciales(make_jurisdiccion_fake):
    """Con múltiples selectores candidatos, si el primero no aparece pero el
    segundo sí, debe seguir clasificando como LoginError (no debe cortar en
    el primer intento fallido)."""
    page = AsyncMock()
    page.wait_for_selector = AsyncMock(
        side_effect=[PlaywrightTimeoutError("no aparece"), object()]
    )
    jurisdiccion = make_jurisdiccion_fake(page=page)

    with pytest.raises(LoginError):
        await jurisdiccion.clasificar_fallo_login(
            error_selectors=[
                ":has-text('mensaje que no aparece')",
                ":has-text('Usuario o clave incorrecta')",
            ]
        )


@pytest.mark.asyncio
async def test_mensaje_timeout_custom_se_propaga(make_jurisdiccion_fake):
    page = AsyncMock()
    page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeoutError("no aparece"))
    jurisdiccion = make_jurisdiccion_fake(page=page)

    with pytest.raises(LoginTimeoutError) as exc_info:
        await jurisdiccion.clasificar_fallo_login(
            error_selectors=[], mensaje_timeout="Portal XYZ no respondió en 30s"
        )
    assert str(exc_info.value) == "Portal XYZ no respondió en 30s"
