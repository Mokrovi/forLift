import os
import subprocess
import time
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class CameraFinder:
    def __init__(self, ffmpeg_path: str = None):
        self.ffmpeg_path = ffmpeg_path or self.get_ffmpeg_path()

    def get_ffmpeg_path(self):
        """Возвращает полный путь к ffmpeg.exe"""
        # Сначала проверяем в корне проекта
        if os.path.exists('ffmpeg.exe'):
            return 'ffmpeg.exe'

        # Затем проверяем в папке ffmpeg/bin/
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ffmpeg_path = os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')

        if os.path.exists(ffmpeg_path):
            logger.info(f"✅ FFmpeg найден: {ffmpeg_path}")
            return ffmpeg_path
        else:
            logger.error("❌ FFmpeg не найден")
            return None

    def _get_cameras_method1(self):
        """Первый метод получения камер"""
        if not self.ffmpeg_path:
            return []

        try:
            result = subprocess.run([
                self.ffmpeg_path,
                '-list_devices', 'true',
                '-f', 'dshow',
                '-i', 'dummy'
            ], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore')

            output = result.stderr
            cameras = []
            lines = output.split('\n')

            for line in lines:
                if 'video' in line.lower() and '"' in line:
                    start = line.find('"') + 1
                    end = line.find('"', start)
                    if end > start:
                        camera_name = line[start:end]
                        if camera_name and not camera_name.startswith('@'):
                            cameras.append(camera_name)

            if cameras:
                logger.info(f"✅ Метод 1: найдено {len(cameras)} камер")
            else:
                logger.warning("❌ Метод 1: камеры не найдены")

            return cameras

        except Exception as e:
            logger.error(f"❌ Метод 1 ошибка: {e}")
            return []

    def _get_cameras_method2(self):
        """Второй метод получения камер"""
        if not self.ffmpeg_path:
            return []

        try:
            result = subprocess.run([
                self.ffmpeg_path,
                '-sources', 'dshow'
            ], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore')

            output = result.stderr + result.stdout
            cameras = []
            lines = output.split('\n')

            for line in lines:
                if 'video' in line.lower() and '[' in line and ']' in line:
                    start = line.find(']') + 1
                    camera_name = line[start:].strip()
                    if camera_name and not camera_name.startswith('@'):
                        cameras.append(camera_name)

            if cameras:
                logger.info(f"✅ Метод 2: найдено {len(cameras)} камер")
            else:
                logger.warning("❌ Метод 2: камеры не найдены")

            return cameras

        except Exception as e:
            logger.error(f"❌ Метод 2 ошибка: {e}")
            return []

    def test_camera_directly(self, camera_name: str) -> Tuple[bool, str]:
        """Прямая проверка камеры с разными настройками"""
        if not self.ffmpeg_path:
            return False, "FFmpeg не найден"

        try:
            logger.info(f"🔍 Тестируем камеру: {camera_name}")

            # ПРОБУЕМ РАЗНЫЕ НАСТРОЙКИ
            test_commands = [
                # Базовая попытка
                [
                    self.ffmpeg_path,
                    '-f', 'dshow',
                    '-video_size', '640x480',
                    '-framerate', '30',
                    '-t', '00:00:03',
                    '-i', f'video={camera_name}',
                    '-f', 'null', '-'
                ],
                # Упрощенная попытка
                [
                    self.ffmpeg_path,
                    '-f', 'dshow',
                    '-i', f'video={camera_name}',
                    '-t', '00:00:02',
                    '-f', 'null', '-'
                ],
                # С другим кодеком
                [
                    self.ffmpeg_path,
                    '-f', 'dshow',
                    '-video_size', '320x240',
                    '-framerate', '15',
                    '-i', f'video={camera_name}',
                    '-c:v', 'mpeg4',
                    '-t', '00:00:02',
                    '-f', 'null', '-'
                ]
            ]

            for i, command in enumerate(test_commands, 1):
                logger.info(f"🔄 Попытка {i} для камеры {camera_name}")
                try:
                    test_result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        encoding='utf-8',
                        errors='ignore'
                    )

                    stderr_output = test_result.stderr.lower()

                    if "frame=" in stderr_output and "fps=" in stderr_output:
                        logger.info(f"✅ Камера '{camera_name}' - РАБОТАЕТ (попытка {i})")
                        return True, "Камера доступна и передает видео"

                    elif "could not run graph" in stderr_output:
                        return False, "Камера занята другим приложением"

                    elif "i/o error" in stderr_output:
                        if i < len(test_commands):
                            continue  # Пробуем следующую команду
                        else:
                            return False, "Ошибка ввода-вывода (проверьте доступ к камере)"

                except subprocess.TimeoutExpired:
                    if i < len(test_commands):
                        continue
                    else:
                        return False, "Таймаут при проверке камеры"

            return False, "Все попытки подключения не удались"

        except Exception as e:
            logger.error(f"❌ Ошибка тестирования камеры {camera_name}: {e}")
            return False, f"Ошибка: {str(e)}"

    def find_available_cameras(self) -> List[str]:
        """Находит все доступные камеры (без тестирования)"""
        logger.info("🔍 Поиск доступных камер...")

        # Получаем все потенциальные камеры
        all_cameras = []
        all_cameras.extend(self._get_cameras_method1())
        all_cameras.extend(self._get_cameras_method2())

        # Убираем дубликаты
        unique_cameras = list(set(all_cameras))

        if not unique_cameras:
            logger.warning("⚠️ Камеры не найдены в системе, используем тестовый список")
            return self._get_fallback_cameras()

        logger.info(f"📹 Найдено потенциальных камер: {len(unique_cameras)}")
        for cam in unique_cameras:
            logger.info(f"   - {cam}")

        return unique_cameras

    def find_working_cameras(self) -> List[str]:
        """Находит и тестирует все камеры, возвращает только рабочие"""
        logger.info("🔍 Поиск и тестирование камер...")

        # Получаем все потенциальные камеры
        all_cameras = self.find_available_cameras()

        if not all_cameras:
            logger.error("❌ Камеры не найдены в системе")
            return []

        # Тестируем каждую камеру
        working_cameras = []
        for camera in all_cameras:
            is_working, message = self.test_camera_directly(camera)
            if is_working:
                working_cameras.append(camera)
                logger.info(f"✅ {camera} - рабочая")
            else:
                logger.info(f"❌ {camera} - нерабочая: {message}")

        logger.info(f"🎯 Рабочие камеры: {len(working_cameras)} из {len(all_cameras)}")

        if working_cameras:
            for cam in working_cameras:
                logger.info(f"   ✅ {cam}")
        else:
            logger.warning("⚠️ Рабочие камеры не найдены, возвращаем все камеры для тестирования")
            return all_cameras

        return working_cameras

    def _get_fallback_cameras(self) -> List[str]:
        """Резервный список камер для тестирования"""
        fallback_cameras = [
            "Integrated Camera",
            "Webcam",
            "USB Camera",
            "HD Webcam",
            "Microsoft Camera",
            "Lenovo Camera"
        ]
        logger.info(f"🔄 Используем резервный список: {len(fallback_cameras)} камер")
        return fallback_cameras


# Функция для обратной совместимости
def find_available_cameras(ffmpeg_path: str = None) -> List[str]:
    """Функция для обратной совместимости с текущим кодом"""
    finder = CameraFinder(ffmpeg_path)
    return finder.find_available_cameras()


def check_camera_permissions(self, camera_name: str) -> Tuple[bool, str]:
    """Проверка прав доступа к камере"""
    try:
        # Пробуем просто получить информацию о камере без захвата видео
        result = subprocess.run([
            self.ffmpeg_path,
            '-f', 'dshow',
            '-list_options', 'true',
            '-i', f'video={camera_name}'
        ], capture_output=True, text=True, timeout=5, encoding='utf-8', errors='ignore')

        if "pixel_format" in result.stderr.lower():
            return True, "Доступ к камере разрешен"
        elif "access denied" in result.stderr.lower():
            return False, "Доступ к камере запрещен"
        else:
            return False, "Не удалось получить информацию о камере"

    except Exception as e:
        return False, f"Ошибка проверки прав: {str(e)}"


def find_working_cameras(ffmpeg_path: str = None) -> List[str]:
    """Функция для обратной совместимости с текущим кодом"""
    finder = CameraFinder(ffmpeg_path)
    return finder.find_working_cameras()


def get_available_microphones(ffmpeg_path: str = None) -> List[str]:
    """Получение списка доступных микрофонов"""
    if ffmpeg_path is None:
        if os.path.exists('ffmpeg.exe'):
            ffmpeg_path = 'ffmpeg.exe'
        else:
            return []
    
    try:
        result = subprocess.run([
            ffmpeg_path,
            '-list_devices', 'true',
            '-f', 'dshow',
            '-i', 'dummy'
        ], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore')
        
        output = result.stderr
        microphones = []
        lines = output.split('\n')
        
        for line in lines:
            if 'audio' in line.lower() and '"' in line:
                start = line.find('"') + 1
                end = line.find('"', start)
                if end > start:
                    mic_name = line[start:end]
                    if mic_name and not mic_name.startswith('@'):
                        microphones.append(mic_name)
        
        if microphones:
            logger.info(f"🎤 Найдено {len(microphones)} микрофонов")
        else:
            logger.warning("⚠️ Микрофоны не найдены")
        
        return microphones
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка микрофонов: {e}")
        return []


if __name__ == "__main__":
    # Настройка логирования для теста
    logging.basicConfig(level=logging.INFO)

    finder = CameraFinder()
    working_cameras = finder.find_working_cameras()
    microphones = get_available_microphones()
    
    print(f"\n📹 Камеры: {working_cameras}")
    print(f"🎤 Микрофоны: {microphones}")

    if working_cameras:
        print(f"\n🎉 Найдены рабочие камеры:")
        for i, cam in enumerate(working_cameras, 1):
            print(f"{i}. {cam}")
    else:
        print("\n😞 Рабочие камеры не найдены")