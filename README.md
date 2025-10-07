# Loki Logger

Python библиотека для отправки логов в Grafana Loki с поддержкой батчинга и автоматического определения вызывающей функции.

## Установка

```bash
pip install log-to-loki
```

## Быстрый старт

```python
from log_to_loki import LokiLogger

# Создание логгера
logger = LokiLogger(
    name='my-app',
    loki_url='http://localhost:3100',
    username='admin',
    password='admin',
    labels={'environment': 'production'}
)

# Использование
logger.info("Приложение запущено")
logger.error("Произошла ошибка")
```


## Возможности
✅ Батчинг логов для производительности
✅ Автоматическое определение вызывающей функции
✅ Поддержка консольного вывода
✅ Настраиваемые метки (labels)
✅ Многопоточная отправка логов
✅ Переиспользование HTTP соединений
