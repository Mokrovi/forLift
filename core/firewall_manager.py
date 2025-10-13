import subprocess
import platform
import ctypes
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class FirewallManager:
    """Управление настройками брандмауэра Windows"""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_admin = self._check_admin_privileges()

    def configure_firewall(self, port: int = 8554, rule_name: str = "RTSP Stream") -> Dict:
        """Настройка брандмауэра для указанного порта"""
        if not self.is_windows:
            return {
                "success": False,
                "message": "Автоматическая настройка брандмауэра доступна только в Windows",
                "admin_required": False
            }

        if not self.is_admin:
            return {
                "success": False,
                "message": "Требуются права администратора для настройки брандмауэра",
                "admin_required": True
            }

        try:
            # Проверяем существование правила
            if self._firewall_rule_exists(rule_name, port):
                logger.info(f"ℹ️ Правило брандмауэра для порта {port} уже существует")
                return {
                    "success": True,
                    "message": f"Порт {port} уже открыт в брандмауэре",
                    "admin_required": False
                }

            # Создаем правило
            cmd = (
                f'netsh advfirewall firewall add rule '
                f'name="{rule_name} {port}" '
                f'dir=in action=allow protocol=TCP localport={port}'
            )

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Порт {port} открыт в брандмауэре")
                return {
                    "success": True,
                    "message": f"Порт {port} успешно открыт в брандмауэре",
                    "admin_required": False
                }
            else:
                error_msg = result.stderr.strip()
                logger.error(f"❌ Ошибка настройки брандмауэра: {error_msg}")

                # Проверяем, если правило уже существует
                if "already exists" in error_msg.lower():
                    return {
                        "success": True,
                        "message": f"Порт {port} уже открыт в брандмауэре",
                        "admin_required": False
                    }

                return {
                    "success": False,
                    "message": f"Ошибка настройки брандмауэра: {error_msg}",
                    "admin_required": True
                }

        except Exception as e:
            logger.error(f"❌ Исключение при настройке брандмауэра: {e}")
            return {
                "success": False,
                "message": f"Исключение: {str(e)}",
                "admin_required": True
            }

    def get_firewall_instructions(self) -> Dict:
        """Получение инструкций по ручной настройке брандмауэра"""
        instructions = {
            "title": "📋 Инструкция по ручной настройке брандмауэра",
            "steps": [
                "1. Нажмите Win + R, введите 'wf.msc' и нажмите Enter",
                "2. Выберите 'Правила для входящих подключений' в левой панели",
                "3. Нажмите 'Создать правило...' в правой панели",
                "4. Выберите 'Для порта', нажмите 'Далее'",
                "5. Выберите 'TCP' и укажите порт: 8554",
                "6. Выберите 'Разрешить подключение', нажмите 'Далее'",
                "7. Отметьте все профили (Домен, Частная, Публичная), нажмите 'Далее'",
                "8. Введите имя: 'RTSP Stream', нажмите 'Готово'"
            ],
            "alternative": "Или запустите эту программу от имени администратора для автоматической настройки"
        }

        return instructions

    def _check_admin_privileges(self) -> bool:
        """Проверка прав администратора"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def _firewall_rule_exists(self, rule_name: str, port: int) -> bool:
        """Проверка существования правила брандмауэра"""
        try:
            cmd = f'netsh advfirewall firewall show rule name="{rule_name} {port}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0 and rule_name in result.stdout
        except:
            return False