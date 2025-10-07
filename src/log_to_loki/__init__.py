"""
Log to Loki - Python library for sending logs to Grafana Loki
"""

__version__ = "0.1.0"
__author__ = "Yunoshev Yaroslav"
__email__ = "yunoshev.dev@gmail.com"

from .loki_handler import LokiHandler, LokiLogger

__all__ = ['LokiHandler', 'LokiLogger']
