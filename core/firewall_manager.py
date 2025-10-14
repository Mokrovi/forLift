import subprocess
import platform
import ctypes
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FirewallManager:
    """Управление настройками брандмауэра Windows с поддержкой IP-фильтрации"""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_admin = self._check_admin_privileges()

    def configure_firewall(
            self,
            port: int = 8554,
            rule_name: str = "RTSP Stream",
            local_ips: Optional[List[str]] = None,
            remote_ips: Optional[List[str]] = None
    ) -> Dict:
        """Настройка брандмауэра для указанного порта с поддержкой IP-фильтрации"""
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
            # Формируем параметры для localip и remoteip
            localip_param = self._format_ip_parameter(local_ips)
            remoteip_param = self._format_ip_parameter(remote_ips)

            # Проверяем существование правила
            if self._firewall_rule_exists(rule_name, port):
                logger.info(f"ℹ️ Правило брандмауэра для порта {port} уже существует")
                return {
                    "success": True,
                    "message": f"Порт {port} уже открыт в брандмауэре",
                    "admin_required": False
                }

            # Создаем правило с поддержкой IP-фильтрации
            cmd_parts = [
                'netsh advfirewall firewall add rule',
                f'name="{rule_name} {port}"',
                'dir=in',
                'action=allow',
                'protocol=TCP',
                f'localport={port}'
            ]

            # Добавляем параметры IP, если указаны
            if localip_param:
                cmd_parts.append(f'localip={localip_param}')
            if remoteip_param:
                cmd_parts.append(f'remoteip={remoteip_param}')

            cmd = ' '.join(cmd_parts)
            logger.debug(f"Выполняемая команда: {cmd}")

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                ip_info = self._get_ip_info_message(local_ips, remote_ips)
                logger.info(f"✅ Порт {port} открыт в брандмауэре{ip_info}")
                return {
                    "success": True,
                    "message": f"Порт {port} успешно открыт в брандмауэре{ip_info}",
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

    def configure_rtsp_firewall_rules(self) -> Dict:
        """Настройка брандмауэра для всех портов RTSP с внешним доступом"""
        if not self.is_windows:
            return {
                "success": False,
                "message": "Автоматическая настройка брандмауэра доступна только в Windows"
            }

        if not self.is_admin:
            return {
                "success": False,
                "message": "Требуются права администратора для настройки брандмауэра",
                "admin_required": True
            }

        try:
            ports = [8554, 8000, 8001, 9997]  # Основные порты MediaMTX
            results = []

            for port in ports:
                # Правило для входящих подключений - разрешаем ВСЕМ
                result_in = self.configure_firewall(
                    port=port,
                    rule_name=f"RTSP Stream IN",
                    remote_ips=["any"]  # Разрешаем всем внешним IP
                )

                # Правило для исходящих подключений
                result_out = self.configure_firewall(
                    port=port,
                    rule_name=f"RTSP Stream OUT",
                    remote_ips=["any"]
                )

                results.append((port, result_in, result_out))

            # Создаем дополнительное правило для UDP (если нужно)
            udp_result = self._configure_udp_rules()

            success_count = sum(1 for _, result_in, result_out in results
                                if result_in.get('success') and result_out.get('success'))

            return {
                "success": success_count > 0,
                "message": f"Настроено {success_count}/{len(ports) * 2} правил брандмауэра",
                "details": results,
                "admin_required": False
            }

        except Exception as e:
            logger.error(f"❌ Ошибка настройки правил брандмауэра: {e}")
            return {
                "success": False,
                "message": f"Ошибка: {str(e)}",
                "admin_required": True
            }

    def _configure_udp_rules(self) -> Dict:
        """Настройка правил для UDP трафика"""
        try:
            # Правило для RTP/UDP трафика
            cmd = (
                'netsh advfirewall firewall add rule '
                'name="RTSP UDP Stream" '
                'dir=in action=allow protocol=UDP localport=8000-8001'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {"success": result.returncode == 0}
        except Exception as e:
            logger.error(f"❌ Ошибка настройки UDP правил: {e}")
            return {"success": False}

    def open_port_for_all_ips(self, port: int = 8554, rule_name: str = "RTSP Stream") -> Dict:
        """Открыть порт для всех IP-адресов (аналогично исходной версии)"""
        return self.configure_firewall(
            port=port,
            rule_name=rule_name,
            remote_ips=["any"]
        )

    def open_port_for_local_subnet(self, port: int = 8554, rule_name: str = "RTSP Stream") -> Dict:
        """Открыть порт только для локальной подсети"""
        return self.configure_firewall(
            port=port,
            rule_name=rule_name,
            remote_ips=["localsubnet"]
        )

    def open_port_for_specific_ips(
            self,
            port: int = 8554,
            rule_name: str = "RTSP Stream",
            allowed_ips: List[str] = None
    ) -> Dict:
        """Открыть порт только для конкретных IP-адресов или подсетей"""
        if not allowed_ips:
            allowed_ips = ["localsubnet"]  # По умолчанию только локальная подсеть

        return self.configure_firewall(
            port=port,
            rule_name=rule_name,
            remote_ips=allowed_ips
        )

    def get_firewall_instructions(self) -> Dict:
        """Получение инструкций по ручной настройке брандмауэра"""
        instructions = {
            "title": "📋 Инструкция по ручной настройке брандмауэра",
            "steps": [
                "1. Нажмите Win + R, введите 'wf.msc' и нажмите Enter",
                "2. Выберите 'Правила для входящих подключений' в левой панели",
                "3. Нажмите 'Создать правило...' в правой панели",
                "4. Выберите 'Для порта', нажмите 'Далее'",
                "5. Выберите 'TCP' и укажите порты: 8554, 8000, 8001, 9997",
                "6. Выберите 'Разрешить подключение', нажмите 'Далее'",
                "7. Отметьте все профили (Домен, Частная, Публичная), нажмите 'Далее'",
                "8. Введите имя: 'RTSP Stream', нажмите 'Готово'",
                "",
                "💡 Для внешнего доступа убедитесь, что:",
                "- В правилах указаны порты: 8554 (RTSP), 8000-8001 (RTP/RTCP), 9997 (API)",
                "- Правила применяются ко всем профилям сети",
                "- В настройках правила разрешены все удаленные IP-адреса"
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

    def _format_ip_parameter(self, ip_list: Optional[List[str]]) -> str:
        """Форматирование списка IP-адресов в параметр для netsh"""
        if not ip_list:
            return ""

        # Объединяем адреса через запятую
        return ",".join(ip_list)

    def _get_ip_info_message(self, local_ips: Optional[List[str]], remote_ips: Optional[List[str]]) -> str:
        """Формирование информационного сообщения о настройках IP"""
        messages = []

        if local_ips:
            messages.append(f"localip: {', '.join(local_ips)}")
        if remote_ips:
            messages.append(f"remoteip: {', '.join(remote_ips)}")

        if messages:
            return f" ({'; '.join(messages)})"
        return ""