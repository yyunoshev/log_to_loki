import pytest
import unittest.mock as mock
from log_to_loki import LokiLogger, LokiHandler

def test_loki_logger_creation():
    """Тест создания логгера"""
    logger = LokiLogger(name='test')
    assert logger is not None

def test_loki_handler_creation():
    """Тест создания Loki handler"""
    handler = LokiHandler(
        loki_url='http://localhost:3100',
        username='test',
        password='test'
    )
    assert handler is not None

@mock.patch('requests.Session.post')
def test_log_sending(mock_post):
    """Тест отправки логов"""
    mock_post.return_value.status_code = 200

    logger = LokiLogger(
        name='test',
        loki_url='http://localhost:3100',
        username='test',
        password='test',
        console_output=False
    )

    logger.info("Test message")
    # Даем время на обработку батча
    import time
    time.sleep(2)

    # Проверяем, что POST запрос был сделан
    assert mock_post.called
