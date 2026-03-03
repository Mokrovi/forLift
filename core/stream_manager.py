import subprocess
import threading
import time
import logging
import socket
import requests
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
        self.current_microphone: Optional[str] = None  # Выбранный микрофон
        self.android_ips: list = []  # Список IP для отправки сигнала
        
        # Настройки громкости и видимости
        self.webcam_volume: float = 1.0  # Громкость вебкамеры (0.0 - 1.0)
        self.webcam_muted: bool = False  # Мут вебкамеры
        self.webcam_hidden: bool = False  # Скрыта ли вебкамера
        self.cartoon_hidden: bool = False  # Скрыт ли мультик

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
        config_content = """# MediaMTX Configuration - Low Latency Mode
logLevel: info
readTimeout: 10s
writeTimeout: 10s

# RTSP settings - слушаем на всех интерфейсах
rtspAddress: :8554

# RTP settings - для видео данных
rtpAddress: :8000
rtcpAddress: :8001

# HTTP API для мониторинга
api: yes
apiAddress: :9997

# HLS settings - отключаем для низкой задержки
hls: no

# WebRTC settings
webrtc: yes
webrtcAddress: :8889

# Буферы - минимальные для низкой задержки
udpMaxPayloadSize: 1472

# Настройки путей
paths:
  live/stream:
    # Разрешаем всем читать и публиковать поток (без авторизации для локального использования)
    readUser: ""
    readPass: ""
    publishUser: ""
    publishPass: ""
    # Настройки для низкой задержки
    overridePublisher: no
    record: no
    sourceOnDemand: no
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

    def start_stream(self, camera_name: str, microphone_name: str = None) -> Dict:
        """Запуск стрима с указанной камеры"""
        try:
            if not self.mediamtx_process or self.mediamtx_process.poll() is not None:
                return {"success": False, "message": "MediaMTX не запущен"}

            ffmpeg_path = self.config.get_ffmpeg_path()
            if not ffmpeg_path.exists():
                return {"success": False, "message": "FFmpeg не найден"}

            # Останавливаем предыдущий стрим
            self.stop_stream()

            # Если микрофон не указан, пробуем найти автоматически
            audio_device = microphone_name or self._get_audio_device_for_camera(camera_name)
            self.current_microphone = audio_device

            # КОМАНДЫ С ОПТИМИЗАЦИЕЙ ЗАДЕРЖКИ И ЗВУКОМ
            commands_to_try = [
                # Попытка 1: С звуком и минимальной задержкой
                self._build_ffmpeg_command(camera_name, audio_device, ffmpeg_path, use_audio=True),
                
                # Попытка 2: Только видео с минимальной задержкой
                self._build_ffmpeg_command(camera_name, None, ffmpeg_path, use_audio=False),
                
                # Попытка 3: С низким разрешением для скорости
                self._build_ffmpeg_command_low_res(camera_name, audio_device, ffmpeg_path),
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
                    local_url = f"rtsp://{self.config.get_local_ip()}:8554/live/stream"
                    external_url = f"rtsp://{self.config.get_external_ip()}:8554/live/stream"

                    # НЕ отправляем сигнал автоматически - пользователь нажмёт кнопку сам

                    return {
                        "success": True,
                        "message": f"Стрим успешно запущен (использована команда {i})",
                        "camera": camera_name,
                        "stream_url": local_url,
                        "audio_enabled": audio_device is not None
                    }

            # Если все попытки не удались
            return {
                "success": False,
                "message": f"Не удалось запустить стрим. Последняя ошибка: {last_error[:200]}..."
            }

        except Exception as e:
            logger.error(f"❌ Ошибка запуска стрима: {e}")
            return {"success": False, "message": f"Ошибка: {str(e)}"}

    def _build_ffmpeg_command(self, camera_name: str, audio_device: str, ffmpeg_path, use_audio: bool = True) -> list:
        """Построение команды FFmpeg с минимальной задержкой"""
        cmd = [
            str(ffmpeg_path),
            '-f', 'dshow',
            '-rtbufsize', '32M',  # Минимальный буфер
        ]

        # Добавляем видео и аудио входы
        if use_audio and audio_device:
            cmd.extend([
                '-i', f'video={camera_name}:audio={audio_device}'
            ])
        else:
            cmd.extend([
                '-i', f'video={camera_name}'
            ])

        # Видео настройки для минимальной задержки
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-g', '15',  # Keyframe каждые 0.5 секунды (при 30fps)
            '-keyint_min', '15',
            '-sc_threshold', '0',
            '-crf', '25',  # Чуть ниже качество для скорости
            '-profile:v', 'baseline',
            '-level', '3.1',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=-1:720',
            '-bf', '0',  # Без B-фреймов
        ])

        # Аудио настройки
        if use_audio and audio_device:
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '64k',
                '-ar', '44100',
                '-ac', '1',  # Моно для меньшей задержки
            ])

        # Вывод с минимальной задержкой
        cmd.extend([
            '-f', 'rtsp',
            '-rtsp_transport', 'udp',  # UDP вместо TCP для меньшей задержки
            '-fflags', '+nobuffer',
            '-flags', '+low_delay',
            '-muxdelay', '0',  # Нулевая задержка mux
            '-muxpreload', '0',
            f'rtsp://:@127.0.0.1:8554/live/stream'
        ])

        return cmd

    def _build_ffmpeg_command_low_res(self, camera_name: str, audio_device: str, ffmpeg_path) -> list:
        """Команда с низким разрешением для максимальной скорости"""
        cmd = [
            str(ffmpeg_path),
            '-f', 'dshow',
            '-video_size', '640x480',
            '-framerate', '30',
            '-rtbufsize', '32M',
        ]

        if audio_device:
            cmd.extend(['-i', f'video={camera_name}:audio={audio_device}'])
        else:
            cmd.extend(['-i', f'video={camera_name}'])

        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-g', '30',
            '-keyint_min', '30',
            '-crf', '25',
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-pix_fmt', 'yuv420p',
        ])

        if audio_device:
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '96k',
                '-ar', '44100',
                '-ac', '1',
            ])

        cmd.extend([
            '-f', 'rtsp',
            '-rtsp_transport', 'tcp',
            '-fflags', '+nobuffer',
            '-flags', '+low_delay',
            f'rtsp://localhost:8554/live/stream'
        ])

        return cmd

    def _get_audio_device_for_camera(self, camera_name: str) -> str:
        """Получение имени аудиоустройства для камеры"""
        try:
            result = subprocess.run([
                str(self.config.get_ffmpeg_path()),
                '-list_devices', 'true',
                '-f', 'dshow',
                '-i', 'dummy'
            ], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore')

            output = result.stderr
            lines = output.split('\n')

            # Ищем микрофон с похожим именем
            for line in lines:
                if 'audio' in line.lower() and '"' in line:
                    # Извлекаем имя устройства
                    start = line.find('"') + 1
                    end = line.find('"', start)
                    if end > start:
                        device_name = line[start:end]
                        # Проверяем если это микрофон камеры или просто Microphone
                        if camera_name.split()[0] in device_name or 'Microphone' in device_name:
                            logger.info(f"🎤 Найдено аудиоустройство: {device_name}")
                            return device_name

            # Если не нашли, пробуем первый доступный микрофон
            for line in lines:
                if 'audio' in line.lower() and '"' in line:
                    start = line.find('"') + 1
                    end = line.find('"', start)
                    if end > start:
                        device_name = line[start:end]
                        if 'Microphone' in device_name or 'Микрофон' in device_name:
                            logger.info(f"🎤 Используем микрофон: {device_name}")
                            return device_name

            logger.warning("⚠️ Аудиоустройство не найдено, стрим без звука")
            return None

        except Exception as e:
            logger.debug(f"ℹ️ Ошибка поиска аудиоустройства: {e}")
            return None

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
            "stream_url": stream_url,
            "webcam_volume": self.webcam_volume,
            "webcam_muted": self.webcam_muted,
            "webcam_hidden": self.webcam_hidden,
            "cartoon_hidden": self.cartoon_hidden
        }

    def set_webcam_volume(self, volume: float) -> None:
        """Установка громкости вебкамеры"""
        self.webcam_volume = max(0.0, min(1.0, volume))
        self.webcam_muted = self.webcam_volume == 0.0

    def mute_webcam(self, mute: bool) -> None:
        """Вкл/выкл звук вебкамеры"""
        self.webcam_muted = mute
        if mute:
            self.webcam_volume = 0.0
        elif self.webcam_volume == 0.0:
            self.webcam_volume = 1.0

    def set_webcam_visibility(self, visible: bool) -> None:
        """Показать/скрыть вебкамеру"""
        self.webcam_hidden = not visible

    def set_cartoon_visibility(self, visible: bool) -> None:
        """Показать/скрыть мультик"""
        self.cartoon_hidden = not visible

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

    def _send_signal_to_android(self, local_url: str, external_url: str):
        """Отправка сигнала на Android устройство о готовности трансляции"""
        try:
            payload = {
                "local_url": local_url,
                "external_url": external_url
            }

            logger.info(f"📡 Отправка сигнала на Android устройства: {payload}")

            # Если есть заданные IP - отправляем только на них
            if self.android_ips:
                for ip in self.android_ips:
                    # Добавляем порт если не указан
                    if ':' not in ip:
                        ip = f"{ip}:8080"
                    android_url = f"http://{ip}/stream"
                    try:
                        response = requests.post(android_url, json=payload, timeout=3)
                        if response.status_code == 200:
                            logger.info(f"✅ Сигнал отправлен на {ip}")
                        else:
                            logger.warning(f"⚠️ Ответ от {ip}: {response.status_code}")
                    except requests.exceptions.Timeout:
                        logger.warning(f"⚠️ Таймаут при отправке на {ip}")
                    except requests.exceptions.ConnectionError:
                        logger.warning(f"⚠️ Устройство недоступно на {ip}")
                    except Exception as e:
                        logger.debug(f"ℹ️ Ошибка отправки на {ip}: {e}")
            else:
                logger.info("ℹ️ Список IP пуст - отправка сигнала пропущена")

        except Exception as e:
            logger.debug(f"ℹ️ Ошибка отправки сигнала Android: {e}")