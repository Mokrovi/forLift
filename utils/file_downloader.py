import urllib.request
import zipfile
import tempfile
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileDownloader:
    """Загрузка и распаковка файлов"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def download_file(self, url: str, filename: str) -> bool:
        """Загрузка файла по URL"""
        try:
            filepath = self.base_dir / filename
            logger.info(f"📥 Загрузка {filename} из {url}...")

            urllib.request.urlretrieve(url, filepath)

            if filepath.exists():
                logger.info(f"✅ Файл загружен: {filepath}")
                return True
            else:
                logger.error(f"❌ Файл не загружен: {filename}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {filename}: {e}")
            return False

    def download_and_extract_zip(self, url: str, extract_to: Path) -> bool:
        """Загрузка и распаковка ZIP архива"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                temp_path = tmp_file.name

            # Загружаем файл
            logger.info(f"📥 Загрузка ZIP из {url}...")
            urllib.request.urlretrieve(url, temp_path)

            # Распаковываем
            logger.info(f"📦 Распаковка в {extract_to}...")
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

            # Удаляем временный файл
            os.unlink(temp_path)

            logger.info(f"✅ ZIP распакован в {extract_to}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки/распаковки ZIP: {e}")
            # Пытаемся удалить временный файл
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass
            return False

    def find_file_in_directory(self, directory: Path, filename: str) -> Optional[Path]:
        """Поиск файла в директории (рекурсивно)"""
        try:
            for file_path in directory.rglob(filename):
                if file_path.is_file():
                    return file_path
            return None
        except Exception as e:
            logger.debug(f"❌ Ошибка поиска файла {filename}: {e}")
            return None

    def setup_portable_python(self) -> bool:
        """Настройка portable Python"""
        try:
            python_dir = self.base_dir / "python"
            python_dir.mkdir(exist_ok=True)

            # URL для Python embedded
            python_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"

            # Загружаем и распаковываем
            if self.download_and_extract_zip(python_url, python_dir):
                # Настраиваем python._pth для импорта site-packages
                pth_file = python_dir / "python311._pth"
                if pth_file.exists():
                    with open(pth_file, 'a', encoding='utf-8') as f:
                        f.write("\nimport site\n")

                logger.info("✅ Portable Python настроен")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка настройки portable Python: {e}")
            return False