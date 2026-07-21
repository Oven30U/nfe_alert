"""
Tests unitarios de la jerarquía de excepciones definida en jurisdicciones/jurisdiccion.py.

Foco especial: LoginTimeoutError NO debe heredar de LoginError. Si algún día
alguien "simplifica" la jerarquía y hace que LoginTimeoutError herede de
LoginError, todo el código que hace `except LoginError` (incluyendo
`tipos_error_sin_reintento` en cliente_processor.py) empezaría a tratar los
timeouts de portal como errores de credenciales. Este test evita ese
regresión silenciosa.
"""
import pytest

from jurisdicciones.jurisdiccion import (
    DelegacionError,
    LoggedException,
    LoginError,
    LoginErrorAfip,
    LoginTimeoutError,
)

pytestmark = pytest.mark.unit


def test_login_timeout_error_no_hereda_de_login_error():
    """Es la invariante más importante de todo el módulo: un timeout de
    portal NUNCA debe poder ser atrapado por un `except LoginError`."""
    assert not issubclass(LoginTimeoutError, LoginError)


def test_login_timeout_error_hereda_de_logged_exception():
    assert issubclass(LoginTimeoutError, LoggedException)


def test_login_error_afip_hereda_de_login_error():
    # Este sí es un error de credenciales (específico de AFIP), por diseño.
    assert issubclass(LoginErrorAfip, LoginError)


def test_delegacion_error_no_hereda_de_login_error():
    # DelegacionError no implica credenciales inválidas, es un caso aparte.
    assert not issubclass(DelegacionError, LoginError)


def test_login_error_mensaje_default():
    err = LoginError(cliente="Cliente X")
    assert str(err) == LoginError.CREDENCIALES_INVALIDAS


def test_login_timeout_error_mensaje_default_menciona_timeout():
    err = LoginTimeoutError(cliente="Cliente X")
    mensaje = str(err).lower()
    assert "timeout" in mensaje or "caíd" in mensaje or "lentitud" in mensaje


def test_login_timeout_error_mensaje_custom():
    err = LoginTimeoutError(cliente="Cliente X", message="portal no respondió")
    assert str(err) == "portal no respondió"


@pytest.mark.parametrize(
    "cls,nombre_esperado",
    [
        (LoginError, "LoginError"),
        (LoginErrorAfip, "LoginErrorAfip"),
        (LoginTimeoutError, "LoginTimeoutError"),
        (DelegacionError, "DelegacionError"),
    ],
)
def test_class_name_usado_por_cliente_processor(cls, nombre_esperado):
    """cliente_processor.py compara por `error.__class__.__name__` (strings)
    en varios lugares (tipos_error_sin_reintento, actualizar_fecha_login_error).
    Si alguien renombra una clase, esas comparaciones se rompen en silencio."""
    assert cls.__name__ == nombre_esperado
