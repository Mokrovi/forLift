from pathlib import Path
from typing import Optional
import socket
import logging

logger = logging.getLogger(__name__)


class AppConfig:
    """Конфигурация приложения"""

    def __init__(self):
        self.BASE_DIR = Path(__file__).parent.parent
        self.TEMPLATES_DIR = self.BASE_DIR / "web" / "templates"
        self.STATIC_DIR = self.BASE_DIR / "web" / "static"
        self.MEDIAMTX_CONFIG_PATH = self.BASE_DIR / "mediamtx.yml"

        # Порт для RTSP стрима
        self.RTSP_PORT = 8554

        # Порт для веб-интерфейса
        self.WEB_PORT = 5000

        # Настройки по умолчанию
        self.DEFAULT_VIDEO_SIZE = "640x480"
        self.DEFAULT_FRAMERATE = 15
        self.DEFAULT_CRF = 25

    def get_ffmpeg_path(self) -> Path:
        """Получение пути к FFmpeg"""
        paths = [
            self.BASE_DIR / "ffmpeg.exe",
            self.BASE_DIR / "ffmpeg",
            Path("ffmpeg.exe"),
            Path("ffmpeg")
        ]

        for path in paths:
            if path.exists():
                logger.info(f"✅ FFmpeg найден: {path}")
                return path

        logger.warning("⚠️ FFmpeg не найден в стандартных путях, будет использован: ffmpeg")
        return Path("ffmpeg")

    def get_mediamtx_path(self) -> Path:
        """Получение пути к MediaMTX"""
        paths = [
            self.BASE_DIR / "mediamtx.exe",
            self.BASE_DIR / "mediamtx",
            Path("mediamtx.exe"),
            Path("mediamtx")
        ]

        for path in paths:
            if path.exists():
                logger.info(f"✅ MediaMTX найден: {path}")
                return path

        logger.warning("⚠️ MediaMTX не найден в стандартных путях, будет использован: mediamtx")
        return Path("mediamtx")

    def get_local_ip(self) -> str:
        """Получение локального IP адреса"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                logger.info(f"📡 Локальный IP: {ip}")
                return ip
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить локальный IP: {e}")
            return "127.0.0.1"  # Возвращаем localhost как запасной вариант

    def get_external_ip(self) -> str:
        """Получение внешнего IP адреса"""
        try:
            import requests
            response = requests.get('https://api.ipify.org', timeout=5)
            ip = response.text
            logger.info(f"🌐 Внешний IP: {ip}")
            return ip
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить внешний IP: {e}")
            return "Не определен"

    def validate_paths(self) -> bool:
        """Проверка существования необходимых путей"""
        required_dirs = [self.TEMPLATES_DIR, self.STATIC_DIR]

        for directory in required_dirs:
            if not directory.exists():
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                    logger.info(f"📁 Создана директория: {directory}")
                except Exception as e:
                    logger.error(f"❌ Ошибка создания директории {directory}: {e}")
                    return False

        # Проверяем наличие исполняемых файлов
        ffmpeg_path = self.get_ffmpeg_path()
        mediamtx_path = self.get_mediamtx_path()

        if not ffmpeg_path.exists():
            logger.error(f"❌ FFmpeg не найден: {ffmpeg_path}")
            return False

        if not mediamtx_path.exists():
            logger.error(f"❌ MediaMTX не найден: {mediamtx_path}")
            return False

        logger.info("✅ Все пути проверены успешно")
        return True

    def get_stream_urls(self) -> dict:
        """Получение URL для стрима"""
        local_ip = self.get_local_ip()

        return {
            "local_rtsp": f"rtsp://{local_ip}:{self.RTSP_PORT}/live/stream",
            "localhost_rtsp": f"rtsp://localhost:{self.RTSP_PORT}/live/stream",
            "web_interface": f"http://{local_ip}:{self.WEB_PORT}"
        }