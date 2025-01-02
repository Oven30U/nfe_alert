import pytest
from unittest.mock import patch, mock_open, MagicMock, ANY

# Constants utilizados en el bloque principal de correo_cli.py
SENDER_EMAIL = "lmarinaro@deloitte.com"
RECEIVER_EMAILS = ["lmarinaro@deloitte.com", "receiver2@deloitte.com"]  # Añadido un segundo receptor para pruebas parciales
SUBJECT_OUTLOOK = "Hola desde Python en Outlook!"
SUBJECT = "Hola desde Python!"
HTML_FILE_PATH = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\System\archivos_plantilla\SIMPLOT ARGENTINA S.R.L_20240918.html"
ZIP_FILE_PATHS = [
    r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot\System\archivos_plantilla_dfe.zip"
]

# 1. Mockear Logger.get_logger antes de importar correo_cli
with patch('correo_cli.Logger.get_logger') as mock_logger_get:
    mock_logger_instance = MagicMock()
    mock_logger_get.return_value = mock_logger_instance
    from correo_cli import send_email_smtp, notify_error  # Importar después del mock

# # 2. Definir fixtures para mock_env, mock_smtp y mock_notify_error
# @pytest.fixture
# def mock_env():
#     """Fixture para mockear os.getenv."""
#     with patch('correo_cli.os.getenv') as mock_getenv:
#         # Definir valores de retorno para las variables de entorno
#         mock_getenv.side_effect = lambda key, default=None: {
#             "SERVIDOR_SMTP": "smtp.example.com",
#             "PUERTO_SMTP": "587",
#             "CORREO_NOTIFICACION_ERROR": "error@example.com"
#         }.get(key, default)
#         yield mock_getenv
@pytest.fixture
def mock_env():
    """Fixture to mock os.getenv."""
    with patch("correo_cli.os.getenv") as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "SERVIDOR_SMTP": "appmail.atrame.deloitte.com",
            "PUERTO_SMTP": 25,
            "CORREO_NOTIFICACION_ERROR": "lmarinaro@deloitte.com",
        }.get(key, default)
        yield mock_getenv


@pytest.fixture
def mock_smtp():
    """Fixture para mockear smtplib.SMTP."""
    with patch('correo_cli.smtplib.SMTP') as mock_smtp:
        yield mock_smtp

@pytest.fixture
def mock_notify_error():
    """Fixture para mockear la función notify_error."""
    with patch('correo_cli.notify_error') as mock_notify_error:
        yield mock_notify_error

# 3. Definir los casos de prueba

def test_send_email_success(mock_smtp, mock_notify_error, mock_env):
    """Test para el envío exitoso de emails."""
    # Arrange
    smtp_instance = mock_smtp.return_value.__enter__.return_value
    smtp_instance.sendmail.return_value = {}
    
    # Act
    successful, failed = send_email_smtp(
        sender_email=SENDER_EMAIL,
        receiver_emails=RECEIVER_EMAILS,
        subject=SUBJECT,
        html_file_path=HTML_FILE_PATH,
        zip_file_paths=ZIP_FILE_PATHS,
        html_content=None
    )
    
    # Assert
    assert successful == RECEIVER_EMAILS
    assert failed == []
    smtp_instance.starttls.assert_called_once()
    assert smtp_instance.sendmail.call_count == len(RECEIVER_EMAILS)
    mock_notify_error.assert_not_called()
    mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[0])
    mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[1])

def test_send_email_smtp_connection_error(mock_smtp, mock_notify_error, mock_env):
    """Test para fallos en la conexión SMTP."""
    # Arrange
    mock_smtp.side_effect = Exception("Connection failed")
    
    # Act
    successful, failed = send_email_smtp(
        sender_email=SENDER_EMAIL,
        receiver_emails=RECEIVER_EMAILS,
        subject=SUBJECT,
        html_file_path=None,
        zip_file_paths=None,
        html_content=None
    )
    
    # Assert
    assert successful == []
    assert failed == []
    mock_notify_error.assert_called_once_with(
        SENDER_EMAIL,
        "Error conectando al servidor SMTP",
        [],
        []
    )
    mock_logger_instance.error.assert_called_with("%s", "Error conectando al servidor SMTP")

def test_send_email_partial_failures(mock_smtp, mock_notify_error, mock_env):
    """Test para fallos parciales al enviar emails."""
    # Arrange
    smtp_instance = mock_smtp.return_value.__enter__.return_value
    
    def sendmail_side_effect(sender, receiver, msg):
        if receiver == RECEIVER_EMAILS[1]:
            raise Exception("Failed to send")
    
    smtp_instance.sendmail.side_effect = sendmail_side_effect
    
    # Act
    successful, failed = send_email_smtp(
        sender_email=SENDER_EMAIL,
        receiver_emails=RECEIVER_EMAILS,
        subject=SUBJECT,
        html_file_path=None,
        zip_file_paths=None,
        html_content=None
    )
    
    # Assert
    assert successful == [RECEIVER_EMAILS[0]]
    assert failed == [RECEIVER_EMAILS[1]]
    smtp_instance.starttls.assert_called_once()
    assert smtp_instance.sendmail.call_count == 2
    mock_notify_error.assert_not_called()
    mock_logger_instance.info.assert_called_once_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[0])
    mock_logger_instance.error.assert_called_once_with("Error enviando email a %s", RECEIVER_EMAILS[1])


def test_send_email_with_html_file(mock_smtp, mock_notify_error, mock_env):
    """Test para enviar email con un archivo HTML."""
    with patch('correo_cli.open', mock_open(read_data="<h1>HTML Content</h1>")) as mock_file:
        # Arrange
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        smtp_instance.sendmail.return_value = {}
        
        # Act
        successful, failed = send_email_smtp(
            sender_email=SENDER_EMAIL,
            receiver_emails=RECEIVER_EMAILS,
            subject=SUBJECT,
            html_file_path=HTML_FILE_PATH,
            zip_file_paths=None,
            html_content=None
        )
        
        # Assert
        mock_file.assert_called_with(HTML_FILE_PATH, "r", encoding="utf-8")
        assert successful == RECEIVER_EMAILS
        assert failed == []
        smtp_instance.starttls.assert_called_once()
        assert smtp_instance.sendmail.call_count == len(RECEIVER_EMAILS)
        mock_notify_error.assert_not_called()
        mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[0])
        mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[1])

def test_send_email_with_html_content(mock_smtp, mock_notify_error, mock_env):
    """Test para enviar email con contenido HTML directo."""
    # Arrange
    smtp_instance = mock_smtp.return_value.__enter__.return_value
    smtp_instance.sendmail.return_value = {}
    html_content = "<h1>Direct HTML Content</h1>"
    
    # Act
    successful, failed = send_email_smtp(
        sender_email=SENDER_EMAIL,
        receiver_emails=RECEIVER_EMAILS,
        subject=SUBJECT,
        html_file_path=None,
        zip_file_paths=None,
        html_content=html_content
    )
    
    # Assert
    assert successful == RECEIVER_EMAILS
    assert failed == []
    smtp_instance.starttls.assert_called_once()
    assert smtp_instance.sendmail.call_count == len(RECEIVER_EMAILS)
    mock_notify_error.assert_not_called()
    mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[0])
    mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[1])

def test_send_email_with_zip_attachments(mock_smtp, mock_notify_error, mock_env):
    """Test para enviar email con adjuntos ZIP."""
    with patch('correo_cli.open', mock_open(read_data=b"ZIPDATA")) as mock_file:
        # Arrange
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        smtp_instance.sendmail.return_value = {}
        
        # Act
        successful, failed = send_email_smtp(
            sender_email=SENDER_EMAIL,
            receiver_emails=RECEIVER_EMAILS,
            subject=SUBJECT,
            html_file_path=None,
            zip_file_paths=ZIP_FILE_PATHS,
            html_content=None
        )
        
        # Assert
        assert mock_file.call_count == len(ZIP_FILE_PATHS)
        for zip_path in ZIP_FILE_PATHS:
            mock_file.assert_any_call(zip_path, "rb")
        assert successful == RECEIVER_EMAILS
        assert failed == []
        smtp_instance.starttls.assert_called_once()
        assert smtp_instance.sendmail.call_count == len(RECEIVER_EMAILS)
        mock_notify_error.assert_not_called()
        mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[0])
        mock_logger_instance.info.assert_called_with("Email enviado a %s exitosamente!", RECEIVER_EMAILS[1])

def test_notify_error_success(mock_smtp, mock_notify_error, mock_env, mock_logger):
    """Test para el envío exitoso de la notificación de error."""
    with patch('correo_cli.open', mock_open(read_data="<h1>Error HTML Content</h1>")) as mock_file:
        # Arrange
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        smtp_instance.sendmail.return_value = {}
        particular_exception = "Test exception"
        successful_emails = ["receiver1@example.com"]
        failed_emails = ["receiver2@example.com"]
        
        # Act
        notify_error(
            sender_email=SENDER_EMAIL,
            particular_exception=particular_exception,
            successful_emails=successful_emails,
            failed_emails=failed_emails
        )
        
        # Assert
        mock_file.assert_called_with(HTML_FILE_PATH, "r", encoding="utf-8")
        smtp_instance.starttls.assert_called_once()
        smtp_instance.sendmail.assert_called_once_with(
            SENDER_EMAIL,
            "error@example.com",
            ANY  # Puedes usar regex o cadenas exactas si es necesario
        )
        mock_logger_instance.info.assert_called_with(
            "Notificación de error enviada a %s",
            {"error@example.com"}
        )
        mock_logger_instance.error.assert_not_called()

def test_notify_error_failure(mock_smtp, mock_notify_error, mock_env, mock_logger):
    """Test para fallos al enviar la notificación de error."""
    # Arrange
    mock_smtp.side_effect = ConnectionRefusedError
    
    # Act
    notify_error(
        sender_email=SENDER_EMAIL,
        particular_exception="Connection refused",
        successful_emails=[],
        failed_emails=[]
    )
    
    # Assert
    mock_smtp.assert_called_once()
    mock_notify_error.assert_not_called()
    mock_logger_instance.error.assert_called_with("Falló al enviar la notificación de error")