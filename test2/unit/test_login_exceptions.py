from unittest.mock import patch

import pytest

from jurisdicciones.jurisdiccion import LoginError, LoginErrorAfip


@pytest.mark.unit
@pytest.mark.smoke
def test_login_error_usa_mensaje_credenciales_por_defecto(cliente):
    with patch("jurisdicciones.jurisdiccion.Logger.get_logger"):
        error = LoginError(cliente)

    assert str(error) == LoginError.CREDENCIALES_INVALIDAS
    assert error.cliente == cliente


@pytest.mark.unit
@pytest.mark.credentials
def test_login_error_conserva_mensaje_explicito(cliente):
    with patch("jurisdicciones.jurisdiccion.Logger.get_logger"):
        error = LoginError(cliente, LoginError.CREDENCIALES_EXPIRADAS)

    assert str(error) == LoginError.CREDENCIALES_EXPIRADAS
    assert error.mensaje_original == LoginError.CREDENCIALES_EXPIRADAS


@pytest.mark.unit
@pytest.mark.credentials
def test_login_error_afip_es_subtipo_de_login_error(cliente):
    with patch("jurisdicciones.jurisdiccion.Logger.get_logger"):
        error = LoginErrorAfip(cliente)

    assert isinstance(error, LoginError)
    assert str(error) == LoginErrorAfip.DEFAULT_MESSAGE


@pytest.mark.unit
@pytest.mark.smoke
def test_excepciones_publicas_requeridas_existen():
    import jurisdicciones.jurisdiccion as modulo

    assert hasattr(modulo, "LoginError")
    assert hasattr(modulo, "LoginErrorAfip")


@pytest.mark.unit
@pytest.mark.known_issue
def test_no_exigir_login_timeout_error_inexistente():
    """
    Guardrail: la suite debe adaptarse al contrato productivo actual.
    No importa LoginTimeoutError porque esa clase no existe en main.
    """
    import jurisdicciones.jurisdiccion as modulo

    assert not hasattr(modulo, "LoginTimeoutError")
