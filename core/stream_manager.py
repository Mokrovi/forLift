import subprocess
import threading
import time
import logging
import socket
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class StreamManager:
    """Управление стриминговыми процессами (FFmpeg и MediaMTX)"""

    def __init__(self, config):
        self.config = config
        self.mediamtx_process: Optional[subprocess.Popen] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.current_camera: Optional[str] = None

    def kill_process_on_port(self, port: int):
        """Убить процесс на указанном порту"""
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f':{port}' in line:
                        parts = line.split()
                        pid = parts[-1]
                        logger.info(f"🔄 Завершаем процесс {pid} на порту {port}")
                        subprocess.run(f'taskkill /PID {pid} /F', shell=True)
                        time.sleep(1)
        except Exception as e:
            logger.error(f"❌ Ошибка завершения процесса на порту {port}: {e}")

    def is_port_available(self, port: int) -> bool:
        """Проверка доступности порта"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def start_mediamtx(self) -> bool:
        """Запуск MediaMTX сервера"""
        try:
            # Сначала убиваем все процессы на портах 8000 и 8554
            self.kill_process_on_port(8000)
            self.kill_process_on_port(8554)
            time.sleep(2)

            if self.mediamtx_process and self.mediamtx_process.poll() is None:
                logger.info("ℹ️ MediaMTX уже запущен")
                return True

            mediamtx_path = self.config.get_mediamtx_path()
            if not mediamtx_path.exists():
                logger.error(f"❌ MediaMTX не найден: {mediamtx_path}")
                return False

            # Удаляем старый конфиг если он существует
            if self.config.MEDIAMTX_CONFIG_PATH.exists():
                self.config.MEDIAMTX_CONFIG_PATH.unlink()
                logger.info("🗑️ Удален старый конфигурационный файл")

            # Проверяем доступность портов
            if not self.is_port_available(8554):
                logger.error("❌ Порт 8554 все еще занят")
                return False

            # Создаем конфигурационный файл
            self._create_mediamtx_config()

            logger.info("🔄 Запуск MediaMTX...")
            logger.info(f"📁 Путь к MediaMTX: {mediamtx_path}")

            # Запускаем процесс
            self.mediamtx_process = subprocess.Popen(
                [str(mediamtx_path), str(self.config.MEDIAMTX_CONFIG_PATH)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=str(self.config.BASE_DIR)
            )

            # Запускаем мониторинг вывода
            threading.Thread(target=self._log_mediamtx_output, daemon=True).start()
            threading.Thread(target=self._log_mediamtx_errors, daemon=True).start()

            # Ждем запуска и проверяем статус
            time.sleep(3)

            return_code = self.mediamtx_process.poll()
            if return_code is not None:
                logger.error(f"❌ MediaMTX завершился с кодом: {return_code}")
                # Читаем все ошибки
                try:
                    stdout, stderr = self.mediamtx_process.communicate(timeout=2)
                    if stdout:
                        for line in stdout.split('\n'):
                            if line.strip():
                                logger.error(f"MediaMTX stdout: {line}")
                    if stderr:
                        for line in stderr.split('\n'):
                            if line.strip():
                                logger.error(f"MediaMTX stderr: {line}")
                except:
                    pass
                return False

            logger.info("✅ MediaMTX успешно запущен")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска MediaMTX: {e}")
            return False

    def _create_mediamtx_config(self):
        """Создание конфигурационного файла MediaMTX с внешним доступом"""
        config_content = """# MediaMTX Configuration
    logLevel: info
    readTimeout: 20s
    writeTimeout: 20s

    # RTSP settings - слушаем на всех интерфейсах
    rtspAddress: :8554

    # RTP settings - для видео данных
    rtpAddress: :8000
    rtcpAddress: :8001

    # HTTP API для мониторинга
    api: yes
    apiAddress: :9997

    # Настройки для внешнего доступа
    paths:
      live/stream:
        source: publisher
        # Разрешаем всем читать поток
        readUser: ""
        readPass: ""
        # Разрешаем всем публиковать  
        publishUser: ""
        publishPass: ""
    """
        self.config.MEDIAMTX_CONFIG_PATH.write_text(config_content, encoding='utf-8')
        logger.info("✅ Конфигурационный файл MediaMTX создан")
        
    def _log_mediamtx_errors(self):
        """Логирование ошибок MediaMTX из stderr"""
        while self.mediamtx_process and self.mediamtx_process.poll() is None:
            try:
                error_output = self.mediamtx_process.stderr.readline()
                if error_output:
                    logger.error(f"MediaMTX ERROR: {error_output.strip()}")
            except:
                break

    def _log_mediamtx_output(self):
        """Логирование вывода MediaMTX"""
        while self.mediamtx_process and self.mediamtx_process.poll() is None:
            try:
                output = self.mediamtx_process.stdout.readline()
                if output:
                    logger.info(f"MediaMTX: {output.strip()}")
            except:
                break

    def start_stream(self, camera_name: str) -> Dict:
        """Запуск стрима с указанной камеры"""
        try:
            if not self.mediamtx_process or self.mediamtx_process.poll() is not None:
                return {"success": False, "message": "MediaMTX не запущен"}

            ffmpeg_path = self.config.get_ffmpeg_path()
            if not ffmpeg_path.exists():
                return {"success": False, "message": "FFmpeg не найден"}

            # Останавливаем предыдущий стрим
            self.stop_stream()

            # ПРОБУЕМ РАЗНЫЕ КОМАНДЫ ДЛЯ КАМЕРЫ
            commands_to_try = [
                # Попытка 1: Без указания параметров + авторизация
                [
                    str(ffmpeg_path),
                    '-f', 'dshow',
                    '-i', f'video={camera_name}',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-tune', 'zerolatency',
                    '-g', '15',
                    '-keyint_min', '15',
                    '-crf', '25',
                    '-profile:v', 'baseline',
                    '-level', '3.1',  # Повышаем уровень для 1280x720
                    '-pix_fmt', 'yuv420p',
                    '-f', 'rtsp',
                    '-rtsp_transport', 'tcp',
                    f'rtsp://localhost:8554/live/stream'  # Без авторизации
                ],
                # Попытка 2: С авторизацией (пустые логин/пароль)
                [
                    str(ffmpeg_path),
                    '-f', 'dshow',
                    '-i', f'video={camera_name}',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-tune', 'zerolatency',
                    '-g', '15',
                    '-keyint_min', '15',
                    '-crf', '25',
                    '-profile:v', 'baseline',
                    '-level', '3.1',
                    '-pix_fmt', 'yuv420p',
                    '-f', 'rtsp',
                    '-rtsp_transport', 'tcp',
                    f'rtsp://:@{self.config.get_local_ip()}:8554/live/stream'  # Пустая авторизация
                ],
                # Попытка 3: С понижением разрешения
                [
                    str(ffmpeg_path),
                    '-f', 'dshow',
                    '-video_size', '640x480',  # Понижаем разрешение
                    '-framerate', '15',
                    '-i', f'video={camera_name}',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-tune', 'zerolatency',
                    '-g', '15',
                    '-keyint_min', '15',
                    '-crf', '25',
                    '-profile:v', 'baseline',
                    '-level', '3.0',
                    '-pix_fmt', 'yuv420p',
                    '-f', 'rtsp',
                    '-rtsp_transport', 'tcp',
                    f'rtsp://localhost:8554/live/stream'
                ],
                # Попытка 4: Минимальные настройки
                [
                    str(ffmpeg_path),
                    '-f', 'dshow',
                    '-i', f'video={camera_name}',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-f', 'rtsp',
                    '-rtsp_transport', 'tcp',
                    f'rtsp://localhost:8554/live/stream'
                ]
            ]

            last_error = ""

            for i, command in enumerate(commands_to_try, 1):
                logger.info(f"🎬 Попытка {i} запуска стрима с камеры: {camera_name}")
                logger.info(f"🔧 Команда: {' '.join(command)}")

                self.ffmpeg_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd=str(self.config.BASE_DIR)
                )

                self.current_camera = camera_name
                threading.Thread(target=self._log_ffmpeg_output, daemon=True).start()
                threading.Thread(target=self._log_ffmpeg_errors, daemon=True).start()

                # Ждем стабилизации
                time.sleep(3)

                if self.ffmpeg_process.poll() is not None:
                    # FFmpeg завершился с ошибкой, пробуем следующую команду
                    stderr_output = self.ffmpeg_process.stderr.read()
                    last_error = stderr_output
                    logger.error(f"❌ Попытка {i} не удалась: FFmpeg завершился с ошибкой")
                    self.ffmpeg_process = None
                    continue
                else:
                    # FFmpeg работает!
                    logger.info(f"✅ Стрим успешно запущен (попытка {i})")
                    stream_url = f"rtsp://{self.config.get_local_ip()}:8554/live/stream"

                    return {
                        "success": True,
                        "message": f"Стрим успешно запущен (использована команда {i})",
                        "camera": camera_name,
                        "stream_url": stream_url
                    }

            # Если все попытки не удались
            return {
                "success": False,
                "message": f"Не удалось запустить стрим. Последняя ошибка: {last_error[:200]}..."
            }

        except Exception as e:
            logger.error(f"❌ Ошибка запуска стрима: {e}")
            return {"success": False, "message": f"Ошибка: {str(e)}"}

    def _log_ffmpeg_errors(self):
        """Логирование ошибок FFmpeg из stderr"""
        while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                error_output = self.ffmpeg_process.stderr.readline()
                if error_output:
                    clean_output = error_output.strip()
                    if clean_output and not clean_output.startswith('frame='):
                        logger.error(f"FFmpeg ERROR: {clean_output}")
            except:
                break

    def _log_ffmpeg_output(self):
        """Логирование вывода FFmpeg"""
        while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                output = self.ffmpeg_process.stderr.readline()
                if output:
                    clean_output = output.strip()
                    if clean_output and not clean_output.startswith('frame='):
                        logger.info(f"FFmpeg: {clean_output}")
            except:
                break

    def stop_stream(self) -> bool:
        """Остановка текущего стрима"""
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
                self.ffmpeg_process = None
                self.current_camera = None
                logger.info("⏹️ Стрим остановлен")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка остановки стрима: {e}")
                return False
        return True

    def stop_all(self):
        """Остановка всех процессов"""
        self.stop_stream()

        if self.mediamtx_process:
            try:
                self.mediamtx_process.terminate()
                self.mediamtx_process.wait(timeout=3)
                logger.info("⏹️ MediaMTX остановлен")
            except Exception as e:
                logger.error(f"❌ Ошибка остановки MediaMTX: {e}")

        # Дополнительно убиваем процессы на портах
        self.kill_process_on_port(8000)
        self.kill_process_on_port(8001)
        self.kill_process_on_port(8554)

    def get_status(self) -> Dict:
        """Получение статуса всех сервисов"""
        stream_url = f"rtsp://{self.config.get_local_ip()}:8554/live/stream" if self.mediamtx_process else None

        return {
            "mediamtx_running": self.mediamtx_process and self.mediamtx_process.poll() is None,
            "ffmpeg_running": self.ffmpeg_process and self.ffmpeg_process.poll() is None,
            "current_camera": self.current_camera,
            "stream_url": stream_url
        }

    def get_available_cameras(self) -> list:
        """Получение списка доступных камер"""
        try:
            ffmpeg_path = self.config.get_ffmpeg_path()
            if not ffmpeg_path.exists():
                return []

            result = subprocess.run([
                str(ffmpeg_path),
                '-list_devices', 'true',
                '-f', 'dshow',
                '-i', 'dummy'
            ], capture_output=True, text=True, timeout=10)

            cameras = []
            lines = result.stderr.split('\n')

            for line in lines:
                if ']  "video=' in line:
                    camera_name = line.split('"video=')[1].replace('"', '')
                    cameras.append(camera_name)

            return cameras

        except Exception as e:
            logger.error(f"❌ Ошибка получения списка камер: {e}")
            return []