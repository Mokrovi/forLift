import os
import sys
import subprocess
import importlib
import platform
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class SystemChecker:
    """Проверка системных требований и установка компонентов"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.is_windows = platform.system() == "Windows"
        self.requirements = {
            'python': {'version': (3, 7), 'optional': False},
            'ffmpeg': {'optional': False},
            'mediamtx': {'optional': False},
            'flask': {'optional': False},
            'requests': {'optional': False}
        }

    def check_all_requirements(self) -> Dict[str, bool]:
        """Проверка всех системных требований"""
        results = {}

        # Проверяем Python
        python_ok = self.check_python_version()
        results['python'] = python_ok

        # Проверяем исполняемые файлы
        ffmpeg_ok = self.check_ffmpeg()
        results['ffmpeg'] = ffmpeg_ok

        mediamtx_ok = self.check_mediamtx()
        results['mediamtx'] = mediamtx_ok

        # Проверяем Python библиотеки
        flask_ok = self.check_python_library('flask')
        results['flask'] = flask_ok

        requests_ok = self.check_python_library('requests')
        results['requests'] = requests_ok

        # Логируем результаты
        for req, status in results.items():
            icon = "✅" if status else "❌"
            logger.info(f"{icon} {req}: {'Доступен' if status else 'Не доступен'}")

        return results

    def check_critical_requirements(self) -> bool:
        """Проверка только критически важных требований"""
        critical_ok = True

        if not self.check_python_version():
            logger.error("❌ Несовместимая версия Python")
            critical_ok = False

        if not self.check_ffmpeg():
            logger.error("❌ FFmpeg не найден")
            critical_ok = False

        if not self.check_mediamtx():
            logger.error("❌ MediaMTX не найден")
            critical_ok = False

        return critical_ok

    def check_python_version(self) -> bool:
        """Проверка версии Python"""
        try:
            version = sys.version_info
            required = self.requirements['python']['version']
            meets_requirement = (version.major, version.minor) >= required

            if meets_requirement:
                logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro}")
            else:
                logger.error(
                    f"❌ Требуется Python {required[0]}.{required[1]}+, установлен {version.major}.{version.minor}")

            return meets_requirement
        except Exception as e:
            logger.error(f"❌ Ошибка проверки Python: {e}")
            return False

    def check_ffmpeg(self) -> bool:
        """Проверка наличия FFmpeg"""
        try:
            # Проверяем в текущей директории
            ffmpeg_paths = [
                self.base_dir / "ffmpeg.exe",
                self.base_dir / "ffmpeg",
                Path("ffmpeg.exe"),
                Path("ffmpeg")
            ]

            for path in ffmpeg_paths:
                if path.exists():
                    logger.info(f"✅ FFmpeg найден: {path}")
                    return True

            # Проверяем в PATH
            result = subprocess.run(['ffmpeg', '-version'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("✅ FFmpeg найден в PATH")
                return True

            logger.error("❌ FFmpeg не найден")
            return False

        except Exception as e:
            logger.debug(f"❌ FFmpeg проверка: {e}")
            return False

    def check_mediamtx(self) -> bool:
        """Проверка наличия MediaMTX"""
        try:
            mediamtx_paths = [
                self.base_dir / "mediamtx.exe",
                self.base_dir / "mediamtx",
                Path("mediamtx.exe"),
                Path("mediamtx")
            ]

            for path in mediamtx_paths:
                if path.exists():
                    logger.info(f"✅ MediaMTX найден: {path}")
                    return True

            logger.error("❌ MediaMTX не найден")
            return False

        except Exception as e:
            logger.debug(f"❌ MediaMTX проверка: {e}")
            return False

    def check_python_library(self, library_name: str) -> bool:
        """Проверка наличия Python библиотеки"""
        try:
            importlib.import_module(library_name)
            logger.info(f"✅ Библиотека {library_name} доступна")
            return True
        except ImportError:
            logger.warning(f"⚠️ Библиотека {library_name} не установлена")
            return False

    def install_missing_components(self):
        """Установка отсутствующих компонентов"""
        logger.info("🔧 Установка отсутствующих компонентов...")

        # Устанавливаем Python библиотеки
        self.install_python_libraries()

        # Предлагаем скачать исполняемые файлы
        self.suggest_executable_downloads()

    def install_python_libraries(self):
        """Установка необходимых Python библиотек"""
        libraries = ['flask', 'requests']

        for lib in libraries:
            if not self.check_python_library(lib):
                logger.info(f"📦 Установка {lib}...")
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', lib],
                                   capture_output=True, timeout=60)
                    logger.info(f"✅ {lib} установлен")
                except Exception as e:
                    logger.error(f"❌ Ошибка установки {lib}: {e}")

    def suggest_executable_downloads(self):
        """Предложение скачать исполняемые файлы"""
        if not self.check_ffmpeg():
            logger.info("💡 Скачайте FFmpeg: https://www.gyan.dev/ffmpeg/builds/")
            logger.info("   Поместите ffmpeg.exe в текущую папку")

        if not self.check_mediamtx():
            logger.info("💡 Скачайте MediaMTX: https://github.com/mediamtx/mediamtx/releases")
            logger.info("   Поместите mediamtx.exe в текущую папку")

    def get_system_info(self) -> Dict:
        """Получение информации о системе"""
        return {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'architecture': platform.architecture()[0],
            'current_directory': str(self.base_dir),
            'is_admin': self._check_admin_privileges()
        }

    def _check_admin_privileges(self) -> bool:
        """Проверка прав администратора (Windows)"""
        if not self.is_windows:
            return False

        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False