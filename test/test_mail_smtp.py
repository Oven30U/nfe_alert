import os
import pytest
from unittest.mock import patch, MagicMock
from mail_smtp import send_email_smtp

@pytest.fixture
def email_data():
    return {
        "sender_email": os.getenv("SENDER_EMAIL"),
        "receiver_emails": [os.getenv("CORREO_RECEPTOR_TEST_MAIL")],
        "subject": "Test send_email_smtp",
        "html_content": "<h1>Test Email</h1>",
        "html_file_path": None,
        "zip_file_paths": None
    }

@patch("mail_smtp.smtplib.SMTP_SSL")
def test_send_email_with_html_content(mock_smtp_ssl, email_data):
    mock_server = MagicMock()
    mock_smtp_ssl.return_value = mock_server

    successful_emails, failed_emails = send_email_smtp(
        email_data["sender_email"],
        email_data["receiver_emails"],
        email_data["subject"],
        email_data["html_file_path"],
        email_data["zip_file_paths"],
        email_data["html_content"]
    )

    mock_server.sendmail.assert_called_once()
    assert successful_emails == email_data["receiver_emails"]
    assert failed_emails == []

@patch("mail_smtp.smtplib.SMTP_SSL")
def test_send_email_with_html_file(mock_smtp_ssl, email_data, tmp_path):
    mock_server = MagicMock()
    mock_smtp_ssl.return_value = mock_server

    html_file = tmp_path / "test_email.html"
    html_file.write_text(email_data["html_content"])
    email_data["html_file_path"] = str(html_file)
    email_data["html_content"] = None

    successful_emails, failed_emails = send_email_smtp(
        email_data["sender_email"],
        email_data["receiver_emails"],
        email_data["subject"],
        email_data["html_file_path"],
        email_data["zip_file_paths"],
        email_data["html_content"]
    )

    mock_server.sendmail.assert_called_once()
    assert successful_emails == email_data["receiver_emails"]
    assert failed_emails == []

@patch("mail_smtp.smtplib.SMTP_SSL")
def test_send_email_with_attachments(mock_smtp_ssl, email_data, tmp_path):
    mock_server = MagicMock()
    mock_smtp_ssl.return_value = mock_server

    zip_file = tmp_path / "test_attachment.zip"
    zip_file.write_text("This is a test attachment.")
    email_data["zip_file_paths"] = [str(zip_file)]

    successful_emails, failed_emails = send_email_smtp(
        email_data["sender_email"],
        email_data["receiver_emails"],
        email_data["subject"],
        email_data["html_file_path"],
        email_data["zip_file_paths"],
        email_data["html_content"]
    )

    mock_server.sendmail.assert_called_once()
    assert successful_emails == email_data["receiver_emails"]
    assert failed_emails == []

@patch("mail_smtp.smtplib.SMTP_SSL", side_effect=Exception("Connection error"))
def test_send_email_connection_error(mock_smtp_ssl, email_data):
    successful_emails, failed_emails = send_email_smtp(
        email_data["sender_email"],
        email_data["receiver_emails"],
        email_data["subject"],
        email_data["html_file_path"],
        email_data["zip_file_paths"],
        email_data["html_content"]
    )

    assert successful_emails == []
    assert failed_emails == []
    mock_smtp_ssl.assert_called_once()

@patch("mail_smtp.smtplib.SMTP_SSL")
def test_send_email_sending_error(mock_smtp_ssl, email_data):
    mock_server = MagicMock()
    mock_server.sendmail.side_effect = Exception("Sending error")
    mock_smtp_ssl.return_value = mock_server

    successful_emails, failed_emails = send_email_smtp(
        email_data["sender_email"],
        email_data["receiver_emails"],
        email_data["subject"],
        email_data["html_file_path"],
        email_data["zip_file_paths"],
        email_data["html_content"]
    )

    assert successful_emails == []
    assert failed_emails == email_data["receiver_emails"]
    mock_server.sendmail.assert_called_once()