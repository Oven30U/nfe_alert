from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from jurisdicciones.jurisdiccion import LoginError


@pytest.mark.unit
@pytest.mark.credentials
@pytest.mark.asyncio
async def test_clave_ciudad_error_visible_se_clasifica_como_login_error(
    agip_instance,
):
    page = MagicMock()
    cuit = MagicMock()
    cuit.fill = AsyncMock()
    clave = MagicMock()
    clave.fill = AsyncMock()
    boton = MagicMock()
    boton.click = AsyncMock()
    error = MagicMock()
    error.wait_for = AsyncMock(return_value=None)
    success = MagicMock()

    page.wait_for_load_state = AsyncMock()
    page.locator.side_effect = [cuit, clave, error]
    page.get_by_role.side_effect = [boton, success]
    agip_instance.page = page

    with patch("jurisdicciones.agip.expect") as mock_expect:
        mock_expect.return_value.to_be_visible = AsyncMock(return_value=None)
        with pytest.raises(LoginError) as exc:
            await agip_instance._login_clave_ciudad()

    assert str(exc.value) == LoginError.CREDENCIALES_INVALIDAS
# async def test_clave_ciudad_error_visible_se_clasifica_como_login_error(
#     agip_instance,
# ):
#     page = MagicMock()
#     cuit = MagicMock()
#     cuit.fill = AsyncMock()
#     clave = MagicMock()
#     clave.fill = AsyncMock()
#     boton = MagicMock()
#     boton.click = AsyncMock()
#     error = MagicMock()
#     error.wait_for = AsyncMock(return_value=None)
#     success = MagicMock()

#     page.wait_for_load_state = AsyncMock()
#     page.locator.side_effect = [cuit, clave, error]
#     page.get_by_role.side_effect = [boton, success]
#     agip_instance.page = page

#     with patch("jurisdicciones.agip.expect"):
#         with pytest.raises(LoginError) as exc:
#             await agip_instance._login_clave_ciudad()

#     assert str(exc.value) == LoginError.CREDENCIALES_INVALIDAS


@pytest.mark.unit
@pytest.mark.timeout
@pytest.mark.known_issue
@pytest.mark.asyncio
@pytest.mark.xfail(
    reason=(
        "Defecto conocido: un timeout esperando la pantalla de éxito se convierte "
        "en LoginError con mensaje 'Credenciales inválidas'."
    ),
    strict=True,
)
async def test_timeout_post_login_no_deberia_informarse_como_credenciales_invalidas(
    agip_instance,
):
    page = MagicMock()
    cuit = MagicMock()
    cuit.fill = AsyncMock()
    clave = MagicMock()
    clave.fill = AsyncMock()
    boton = MagicMock()
    boton.click = AsyncMock()
    error = MagicMock()
    error.wait_for = AsyncMock(side_effect=PlaywrightTimeoutError("sin error visible"))
    success = MagicMock()

    page.wait_for_load_state = AsyncMock()
    page.locator.side_effect = [cuit, clave, error]
    page.get_by_role.side_effect = [boton, success]
    agip_instance.page = page

    fake_expect = MagicMock()
    fake_expect.to_be_visible = AsyncMock(
        side_effect=PlaywrightTimeoutError("portal sin respuesta")
    )

    with patch("jurisdicciones.agip.expect", return_value=fake_expect):
        with pytest.raises(LoginError) as exc:
            await agip_instance._login_clave_ciudad()

    # Requisito QA: un timeout no debe comunicar que las credenciales son inválidas.
    assert str(exc.value) != LoginError.CREDENCIALES_INVALIDAS


@pytest.mark.unit
@pytest.mark.credentials
@pytest.mark.asyncio
async def test_miba_detecta_cualquiera_de_los_selectores_de_error(agip_instance):
    page = MagicMock()
    locators = []

    for visible in (False, True, False):
        locator = MagicMock()
        locator.is_visible = AsyncMock(return_value=visible)
        locators.append(locator)

    page.locator.side_effect = locators
    agip_instance.page = page

    with pytest.raises(LoginError):
        await agip_instance._login_miba_check_login_errors()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_miba_sin_indicadores_de_error_no_lanza_login_error(agip_instance):
    page = MagicMock()

    def locator_factory(_):
        locator = MagicMock()
        locator.is_visible = AsyncMock(return_value=False)
        return locator

    page.locator.side_effect = locator_factory
    agip_instance.page = page

    await agip_instance._login_miba_check_login_errors()
