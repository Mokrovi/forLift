#!/usr/bin/env python3
"""
RTSP Stream Application - Main Entry Point
Автоматическая установка и запуск системы стриминга
"""

import os
import sys
import logging
import time  # ИМЕННО ЭТОТ ИМПОРТ НУЖЕН!
from pathlib import Path

# Добавляем корневую директорию в путь Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from core.stream_manager import StreamManager
from web.app import WebApp
from utils.system_checker import SystemChecker
from config.settings import AppConfig

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

        return self.system_checker.check_critical_requirements()

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
            logger.info("⏹️  Для остановки нажмите Ctrl+C")

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