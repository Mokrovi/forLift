import os
import sys
import logging
import time
from pathlib import Path

# Включаем UTF-8 для Windows консоли
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Добавляем корневую директорию в путь Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from core.stream_manager import StreamManager
from web.app import WebApp
from utils.system_checker import SystemChecker
from config.settings import AppConfig
from core.firewall_manager import FirewallManager
from core.firewall_prompt import FirewallPrompt

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rtsp_stream.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class RTSPStreamApp:
    """Основной класс приложения RTSP стриминга"""

    def __init__(self):
        self.config = AppConfig()
        self.system_checker = SystemChecker()
        self.stream_manager = StreamManager(self.config)
        self.web_app = WebApp(self.stream_manager, self.config)
        self.firewall_manager = FirewallManager()
        self.firewall_prompt = FirewallPrompt()

    def setup_environment(self):
        """Настройка окружения и проверка зависимостей"""
        logger.info("🔧 Настройка окружения...")

        # Создаем необходимые директории
        for directory in ['templates', 'static', 'logs']:
            Path(directory).mkdir(exist_ok=True)

        # Проверяем системные требования
        requirements_met = self.system_checker.check_all_requirements()

        if not requirements_met:
            logger.warning("⚠️ Не все требования выполнены. Попытка установки...")
            self.system_checker.install_missing_components()

        # НАСТРОЙКА БРАНДМАУЭРА С ЗАПРОСОМ РАЗРЕШЕНИЯ
        self._configure_firewall_with_prompt()

        return self.system_checker.check_critical_requirements()

    def _configure_firewall_with_prompt(self):
        """Настройка брандмауэра с запросом разрешения пользователя"""
        logger.info("🛡️ Настройка доступа через брандмауэр Windows...")

        # 1. Показываем инструкцию ДО попытки настройки
        self._show_firewall_welcome_message()

        # 2. Добавляем приложение в разрешенные программы брандмауэра
        logger.info("🛡️ Добавляем приложение в разрешенные программы брандмауэра...")
        app_result = self.firewall_prompt.add_app_to_firewall("RTSP Stream Application")

        if app_result:
            logger.info("✅ Приложение добавлено в разрешенные программы брандмауэра")
            logger.info("📋 Если появится запрос от Защитника Windows, нажмите 'Разрешить доступ'")
        else:
            logger.warning("⚠️ Не удалось добавить приложение в разрешенные программы")
            logger.info("💡 Это нормально, если приложение уже было добавлено ранее")

        # 3. Настраиваем правила для портов (требует админ прав)
        logger.info("🔧 Настраиваем правила для портов...")
        if self.firewall_prompt.is_admin:
            firewall_result = self.firewall_manager.configure_rtsp_firewall_rules()
            if firewall_result.get('success'):
                logger.info(f"✅ {firewall_result.get('message')}")
            else:
                logger.error(f"❌ Ошибка настройки правил портов: {firewall_result.get('message')}")
        else:
            logger.info("ℹ️ Для автоматической настройки правил портов запустите программу от имени администратора")
            logger.info("📋 Вы можете настроить брандмауэр вручную через веб-интерфейс")

        # 4. Даем время для появления запроса брандмауэра
        time.sleep(2)

    def _show_firewall_welcome_message(self):
        """Показ приветственного сообщения о настройке брандмауэра"""
        welcome_msg = """
        🔒 НАСТРОЙКА ДОСТУПА ЧЕРЕЗ БРАНДМАУЭР

        Сейчас программа попытается настроить брандмауэр Windows.
        Это необходимо для работы RTSP стриминга.

        ВАЖНО:
        • Если появится окно Защитника Windows - нажмите "РАЗРЕШИТЬ"
        • Выберите оба типа сетей (Частные и Публичные)
        • Это безопасно - программа работает только локально

        Если окно не появилось автоматически, не беспокойтесь - 
        вы сможете настроить доступ через веб-интерфейс.
        """

        print("=" * 60)
        for line in welcome_msg.split('\n'):
            print(line.strip())
        print("=" * 60)
        print()

    def start_services(self):
        """Запуск всех сервисов"""
        logger.info("🚀 Запуск сервисов...")

        # Запускаем MediaMTX сервер
        if not self.stream_manager.start_mediamtx():
            logger.error("❌ Не удалось запустить MediaMTX")
            return False

        # Запускаем веб-сервер
        try:
            self.web_app.start()

            # ЖДЕМ пока пользователь не остановит приложение
            logger.info("🌐 Веб-интерфейс доступен по адресу: http://localhost:5000")
            logger.info("📹 RTSP поток будет доступен по адресу: rtsp://ваш-ip:8554/live/stream")
            logger.info("⏹️  Для остановки нажмите Ctrl+C")
            logger.info("")

            # Бесконечный цикл ожидания
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("📋 Получен сигнал прерывания от пользователя")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска веб-сервера: {e}")
            return False

    def stop_services(self):
        """Остановка всех сервисов"""
        logger.info("🛑 Остановка сервисов...")
        self.stream_manager.stop_all()
        logger.info("✅ Все сервисы остановлены")

    def run(self):
        """Основной метод запуска приложения"""
        try:
            print("=" * 50)
            print("🚀 RTSP Stream Application")
            print("=" * 50)
            print()

            # Настройка окружения
            if not self.setup_environment():
                logger.error("❌ Критические требования не выполнены")
                return False

            # Запуск сервисов
            if not self.start_services():
                logger.error("❌ Не удалось запустить сервисы")
                return False

            return True

        except KeyboardInterrupt:
            logger.info("📋 Получен сигнал прерывания")
            self.stop_services()
            return True
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            self.stop_services()
            return False


def main():
    """Точка входа в приложение"""
    app = RTSPStreamApp()
    success = app.run()

    if success:
        logger.info("✅ Приложение завершило работу успешно")
        sys.exit(0)
    else:
        logger.error("❌ Приложение завершило работу с ошибкой")
        sys.exit(1)


if __name__ == "__main__":
    main()