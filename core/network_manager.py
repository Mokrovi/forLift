import socket
import requests
import logging
from typing import Dict, Optional
from urllib.error import URLError

logger = logging.getLogger(__name__)


class NetworkManager:
    """Управление сетевыми настройками и доступностью"""

    def __init__(self):
        self.local_ip = self._get_local_ip()
        self.external_ip = self._get_external_ip()

    def get_network_info(self) -> Dict:
        """Получение полной сетевой информации"""
        return {
            'local_ip': self.local_ip,
            'external_ip': self.external_ip,
            'rtsp_port': 8554,
            'rtsp_url_local': f"rtsp://{self.local_ip}:8554/live/stream",
            'rtsp_url_external': f"rtsp://{self.external_ip}:8554/live/stream",
            'web_url_local': f"http://{self.local_ip}:5000",
            'status': 'ready'
        }

    def check_port_access(self, port: int = 8554, host: str = '127.0.0.1') -> bool:
        """Проверка доступности порта"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"❌ Ошибка проверки порта {port}: {e}")
            return False

    def check_external_access(self) -> Dict:
        """Проверка внешней доступности"""
        port_open = self.check_port_access(8554)

        return {
            'port_open': port_open,
            'local_ip': self.local_ip,
            'external_ip': self.external_ip,
            'message': 'Порт открыт локально' if port_open else 'Порт закрыт',
            'suggestions': self._get_access_suggestions(port_open)
        }

    def _get_local_ip(self) -> str:
        """Получение локального IP адреса"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "192.168.1.100"

    def _get_external_ip(self) -> str:
        """Получение внешнего IP адреса"""
        services = [
            'https://api.ipify.org',
            'https://ident.me',
            'https://checkip.amazonaws.com'
        ]

        for service in services:
            try:
                response = requests.get(service, timeout=10)
                if response.status_code == 200:
                    ip = response.text.strip()
                    logger.info(f"🌐 Внешний IP: {ip}")
                    return ip
            except Exception as e:
                logger.debug(f"❌ Не удалось получить IP от {service}: {e}")
                continue

        return "Не удалось определить"

    def _get_access_suggestions(self, port_open: bool) -> list:
        """Получение рекомендаций по настройке доступа"""
        suggestions = []

        if not port_open:
            suggestions.extend([
                "Запустите программу от имени администратора для автоматической настройки брандмауэра",
                "Или откройте порт 8554 в брандмауэре вручную"
            ])

        suggestions.extend([
            "Для внешнего доступа настройте проброс порта 8554 в роутере",
            f"Локальный URL: rtsp://{self.local_ip}:8554/live/stream",
            f"Внешний URL: rtsp://{self.external_ip}:8554/live/stream"
        ])

        return suggestions