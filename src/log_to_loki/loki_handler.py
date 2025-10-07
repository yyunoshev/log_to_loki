import logging
import json
import requests
import time
import inspect
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urljoin
import sys
import threading
from queue import Queue, Empty


class LokiHandler(logging.Handler):
    """
    Кастомный handler для отправки логов в Grafana Loki
    """

    def __init__(self, loki_url: str, username: str, password: str,
                 labels: Optional[Dict[str, str]] = None, batch_size: int = 10,
                 flush_interval: int = 5):
        super().__init__()
        self.loki_url = loki_url.rstrip('/')
        self.push_url = urljoin(self.loki_url + '/', 'loki/api/v1/push')
        self.username = username
        self.password = password
        self.labels = labels or {}
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # Очередь для батчинга логов
        self.log_queue = Queue()
        self.batch_thread = threading.Thread(target=self._batch_worker, daemon=True)
        self.batch_thread.start()

        # Сессия для переиспользования соединений
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Scope-OrgID': 'tenant1'  # Можно настроить при необходимости
        })

    def emit(self, record):
        """
        Отправка лог записи в очередь для батчинга
        """
        try:
            # Получаем информацию о реальном вызове (не из логгера)
            caller_info = self._get_real_caller()

            # Форматируем сообщение с информацией о вызывающей функции
            formatted_message = self.format(record)
            if caller_info:
                formatted_message = f"[{caller_info['function']}:{caller_info['line']}] {formatted_message}"

            # Создаем лог entry для Loki
            log_entry = {
                'timestamp': str(int(time.time() * 1_000_000_000)),  # nanoseconds
                'message': formatted_message,
                'level': record.levelname,
                'logger': record.name,
                **caller_info
            }

            # Добавляем в очередь
            self.log_queue.put(log_entry)

        except Exception as e:
            self.handleError(record)

    def _get_real_caller(self) -> Dict[str, Any]:
        """
        Получает информацию о реальном вызывающем коде (не из logging модуля)
        """
        frame = inspect.currentframe()
        try:
            # Поднимаемся по стеку вызовов, пропуская кадры logging модуля
            while frame:
                frame = frame.f_back
                if not frame:
                    break

                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                line_number = frame.f_lineno

                # Пропускаем только кадры из logging модуля и методы нашего класса
                if (not filename.endswith('logging/__init__.py') and
                    not filename.endswith('logging\\__init__.py') and
                    function_name not in ['_log', 'info', 'debug', 'warning', 'error', 'critical', 'emit',
                                         '_get_real_caller', 'format', '_batch_worker', '_send_batch'] and
                    'logging' not in filename.lower() and
                    not ('LokiHandler' in filename or 'LokiLogger' in filename)):

                    # Если это вызов на уровне модуля, используем имя файла без расширения
                    if function_name == '<module>':
                        module_name = filename.split('/')[-1].split('\\')[-1]
                        if module_name.endswith('.py'):
                            module_name = module_name[:-3]
                        function_name = f"{module_name}_module"

                    return {
                        'function': function_name,
                        'line': line_number,
                        'file': filename.split('/')[-1].split('\\')[-1]  # Только имя файла
                    }

            return {'function': 'unknown', 'line': 0, 'file': 'unknown'}

        finally:
            del frame

    def _batch_worker(self):
        """
        Фоновый поток для отправки логов батчами
        """
        batch = []
        last_flush = time.time()

        while True:
            try:
                # Получаем лог из очереди с таймаутом
                try:
                    log_entry = self.log_queue.get(timeout=1.0)
                    batch.append(log_entry)
                except Empty:
                    pass

                current_time = time.time()

                # Отправляем батч если достигли лимита или прошло время
                if (len(batch) >= self.batch_size or
                    (batch and current_time - last_flush >= self.flush_interval)):

                    if batch:
                        self._send_batch(batch)
                        batch = []
                        last_flush = current_time

            except Exception as e:
                print(f"Ошибка в batch worker: {e}", file=sys.stderr)

    def _send_batch(self, batch):
        """
        Отправляет батч логов в Loki
        """
        try:
            # Группируем логи по меткам
            streams = {}
            base_labels = {
                'job': 'python-app',
                'level': 'info',
                **self.labels
            }

            for entry in batch:
                # Создаем уникальный набор меток для каждого лога
                labels = {
                    **base_labels,
                    'level': entry['level'].lower(),
                    'function': entry['function'],
                    'file': entry['file']
                }

                # Создаем строку меток для группировки (только для внутреннего использования)
                labels_key = '|'.join([f'{k}={v}' for k, v in sorted(labels.items())])

                if labels_key not in streams:
                    streams[labels_key] = {'labels': labels, 'values': []}

                streams[labels_key]['values'].append([entry['timestamp'], entry['message']])

            # Формируем payload для Loki
            loki_streams = []
            for stream_data in streams.values():
                loki_streams.append({
                    'stream': stream_data['labels'],  # Передаем метки как dict без кавычек
                    'values': stream_data['values']
                })

            payload = {'streams': loki_streams}

            # Отправляем в Loki
            response = self.session.post(
                self.push_url,
                data=json.dumps(payload),
                timeout=10
            )

            if response.status_code not in [200, 204]:
                print(f"Ошибка отправки в Loki: {response.status_code} - {response.text}",
                      file=sys.stderr)

        except Exception as e:
            print(f"Ошибка отправки батча в Loki: {e}", file=sys.stderr)

    def close(self):
        """
        Закрытие handler с отправкой оставшихся логов
        """
        # Даем время на отправку оставшихся логов
        time.sleep(self.flush_interval + 1)
        self.session.close()
        super().close()


class LokiLogger:
    """
    Основной класс логгера с поддержкой Loki и консольного вывода
    """

    def __init__(self, name: str = 'app', loki_url: str = None,
                 username: str = None, password: str = None,
                 level: int = logging.INFO, console_output: bool = True,
                 labels: Optional[Dict[str, str]] = None):

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Очищаем существующие handlers
        self.logger.handlers.clear()

        # Настраиваем форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Консольный handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)

            # Кастомный форматтер для консоли с информацией о вызове
            console_formatter = self._create_console_formatter()
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # Loki handler
        if loki_url and username and password:
            loki_handler = LokiHandler(
                loki_url=loki_url,
                username=username,
                password=password,
                labels=labels
            )
            loki_handler.setLevel(level)
            loki_handler.setFormatter(formatter)
            self.logger.addHandler(loki_handler)

    def _create_console_formatter(self):
        """
        Создает кастомный форматтер для консоли с информацией о вызове
        """
        class ConsoleFormatter(logging.Formatter):
            def format(self, record):
                # Получаем информацию о реальном вызове
                caller_info = self._get_real_caller()

                # Добавляем информацию о вызове в начало сообщения
                if caller_info:
                    prefix = f"[{caller_info['function']}:{caller_info['line']}]"
                    record.msg = f"{prefix} {record.msg}"

                return super().format(record)

            def _get_real_caller(self):
                """Аналогично методу в LokiHandler"""
                frame = inspect.currentframe()
                try:
                    while frame:
                        frame = frame.f_back
                        if not frame:
                            break

                        filename = frame.f_code.co_filename
                        function_name = frame.f_code.co_name
                        line_number = frame.f_lineno

                        if (not filename.endswith('logging/__init__.py') and
                            not filename.endswith('logging\\__init__.py') and
                            function_name not in ['_log', 'info', 'debug', 'warning', 'error', 'critical', 'format',
                                                 '_get_real_caller', '_batch_worker', '_send_batch'] and
                            'logging' not in filename.lower() and
                            not ('LokiHandler' in filename or 'LokiLogger' in filename)):

                            # Если это вызов на уровне модуля, используем имя файла без расширения
                            if function_name == '<module>':
                                module_name = filename.split('/')[-1].split('\\')[-1]
                                if module_name.endswith('.py'):
                                    module_name = module_name[:-3]
                                function_name = f"{module_name}_module"

                            return {
                                'function': function_name,
                                'line': line_number,
                                'file': filename.split('/')[-1].split('\\')[-1]
                            }

                    return {'function': 'unknown', 'line': 0, 'file': 'unknown'}

                finally:
                    del frame

        return ConsoleFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
