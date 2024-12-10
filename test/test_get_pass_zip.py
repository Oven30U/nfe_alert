import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from conectar_db import get_pass_zip

@pytest.fixture
def mock_session():
    with patch('conectar_db.get_session') as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        yield mock_session

def test_get_pass_zip(mock_session):
    # Simular los resultados de la consulta
    mock_session.execute.return_value.fetchone.side_effect = [
        ('mocked_pass', '01-01-2023'),  # Primer resultado de la consulta
        (1,),  # Segundo resultado de la consulta (cliente_id)
    ]

    # Llamar a la función
    result = get_pass_zip('mocked_cliente', 'mocked_email@deloitte.com')

    # Aserciones
    assert result == 'mocked_pass'
    mock_session.execute.assert_called()
    mock_session.close.assert_called()

def test_get_pass_zip_no_result(mock_session):
    # Simular los resultados de la consulta para que no devuelvan resultados
    mock_session.execute.return_value.fetchone.return_value = None

    # Llamar a la función
    result = get_pass_zip('mocked_cliente', 'mocked_email@deloitte.com')

    # Aserciones
    assert result is None
    mock_session.execute.assert_called()
    mock_session.close.assert_called()