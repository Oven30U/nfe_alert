import pytest
from unittest.mock import patch, MagicMock
from conectar_db import (
    get_related_users_emails,
    verify_and_add_users,
    verify_and_add_user_client_relationship,
    set_pass,
    get_pass_zip,
)
from models import UsuarioAutorizado


@pytest.fixture
def mock_session():
    with patch("conectar_db.get_sqlite_session") as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        yield mock_session


def test_get_related_users_emails(mock_session):
    # Mock the query result
    mock_session.query().join().filter().all.return_value = [
        ("user1@example.com",),
        ("user2@example.com",),
    ]

    cliente_id = 1
    result = get_related_users_emails(cliente_id)

    assert result == ["user1@example.com", "user2@example.com"]
    mock_session.query().join().filter().all.assert_called_once()


def test_verify_and_add_users(mock_session):
    # Mock the query result
    mock_session.query().filter().all.return_value = [("user1@example.com",)]

    correo_output = ["user1@example.com", "user2@example.com"]
    existing_users, missing_users = verify_and_add_users(correo_output)

    assert existing_users == {"user1@example.com"}
    assert missing_users == ["user2@example.com"]
    mock_session.query().filter().all.assert_called_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


def test_verify_and_add_user_client_relationship(mock_session):
    # Mock the query result
    mock_user = MagicMock()
    mock_user.username = "lmarinaro@deloitte.com"
    mock_user.id = 1
    mock_session.query().filter().all.return_value = [mock_user]
    mock_session.query().filter_by().count.return_value = 0

    cliente_id = 1
    correo_output = ["lmarinaro@deloitte.com"]
    cliente = "Test Cliente"
    new_pass = "newpassword"

    (
        usuarios_autorizados,
        dias,
        inserted_users,
        all_successful_emails,
        all_failed_emails,
    ) = verify_and_add_user_client_relationship(
        cliente_id, correo_output, cliente, new_pass
    )

    assert usuarios_autorizados == {"lmarinaro@deloitte.com": 1}
    assert dias == 90
    assert inserted_users == ["lmarinaro@deloitte.com"]
    assert all_successful_emails == ["lmarinaro@deloitte.com"]
    assert all_failed_emails == []
    mock_session.query().filter().all.assert_called_once()
    mock_session.query().filter_by().count.assert_called_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


def test_set_pass(mock_session):
    # Mock the query result
    mock_session.query().filter_by().first.return_value = MagicMock(
        id=1, pass_="oldpassword", fecha_actualizacion_pass=datetime.now()
    )

    cliente = "Test Cliente"
    correo_output = ["user1@example.com"]
    new_pass = set_pass(cliente, correo_output)

    assert new_pass is not None
    mock_session.query().filter_by().first.assert_called_once()
    mock_session.commit.assert_called_once()


def test_get_pass_zip(mock_session):
    # Mock the query result
    mock_session.query().filter_by().order_by().first.return_value = MagicMock(
        id=1, pass_="oldpassword", fecha_actualizacion_pass=datetime.now()
    )

    cliente = "Test Cliente"
    correo_output = ["user1@example.com"]
    pass_value = get_pass_zip(cliente, correo_output)

    assert pass_value is not None
    mock_session.query().filter_by().order_by().first.assert_called_once()
    mock_session.commit.assert_called_once()
