import os
import sys
import ctypes
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class FirewallPrompt:
    """Управление запросами разрешения брандмауэра Windows"""

    def __init__(self):
        self.is_windows = os.name == 'nt'
        try:
            self.is_admin = ctypes.windll.shell32.IsUserAnAdmin() if self.is_windows else False
        except:
            self.is_admin = False

    def add_app_to_firewall(self, app_name: str = "RTSP Stream Application") -> bool:
        """
        Добавляет приложение в список разрешенных программ брандмауэра Windows
        Это может вызвать стандартное окно запроса разрешения у пользователя
        """
        if not self.is_windows:
            logger.info("⚠️ Запросы брандмауэра доступны только в Windows")
            return False

        try:
            # Получаем путь к текущему исполняемому файлу Python
            if getattr(sys, 'frozen', False):
                # Если приложение собрано в exe
                app_path = sys.executable
            else:
                # Если запуск из Python скрипта - используем python.exe
                app_path = sys.executable

            logger.info(f"📁 Путь к приложению: {app_path}")

            # Проверяем существует ли правило
            if self._check_firewall_rule_exists(app_name):
                logger.info("ℹ️ Правило для приложения уже существует в брандмауэре")
                return True

            # Команда для добавления приложения в брандмауэр
            # Эта команда может вызвать окно запроса разрешения
            cmd = (
                f'netsh advfirewall firewall add rule '
                f'name="{app_name}" '
                f'dir=in action=allow program="{app_path}" '
                f'enable=yes profile=any'
            )

            logger.info("🛡️ Пытаемся добавить приложение в брандмауэр...")
            logger.info("💡 Может появиться запрос от Защитника Windows")

            # Запускаем команду
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ Приложение успешно добавлено в брандмауэр")
                return True
            else:
                error_msg = result.stderr.strip()
                if "already exists" in error_msg.lower():
                    logger.info("ℹ️ Правило для приложения уже существует")
                    return True
                else:
                    logger.warning(f"⚠️ Не удалось добавить в брандмауэр: {error_msg}")
                    logger.info("💡 Это нормально, если у вас нет прав администратора")
                    return False

        except Exception as e:
            logger.error(f"❌ Исключение при настройке брандмауэра: {e}")
            return False

    def _check_firewall_rule_exists(self, rule_name: str) -> bool:
        """Проверяет, есть ли правило в брандмауэре"""
        try:
            cmd = f'netsh advfirewall firewall show rule name="{rule_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def remove_app_from_firewall(self, app_name: str = "RTSP Stream Application") -> bool:
        """Удаляет приложение из списка разрешенных программ"""
        if not self.is_windows:
            return False

        try:
            cmd = f'netsh advfirewall firewall delete rule name="{app_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"❌ Ошибка удаления из брандмауэра: {e}")
            return False

    def check_app_in_firewall(self, app_name: str = "RTSP Stream Application") -> bool:
        """Проверяет, есть ли приложение в списке разрешенных"""
        return self._check_firewall_rule_exists(app_name)