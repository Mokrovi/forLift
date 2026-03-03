from flask import Flask, render_template, request, jsonify
import logging
import threading
from typing import Dict
import socket

# Импорты ВСЕХ нужных классов ОДИН РАЗ в начале файла
from core.camera_finder import CameraFinder
from core.network_manager import NetworkManager
from core.firewall_manager import FirewallManager

logger = logging.getLogger(__name__)


class WebApp:
    """Веб-интерфейс для управления стримингом"""

    def __init__(self, stream_manager, config):
        self.stream_manager = stream_manager
        self.config = config
        self.app = Flask(__name__,
                         template_folder=str(config.TEMPLATES_DIR),
                         static_folder=str(config.STATIC_DIR))

        self.camera_finder = CameraFinder(str(self.config.get_ffmpeg_path()))
        self.network_manager = NetworkManager()
        self.firewall_manager = FirewallManager()
        
        # Список IP для отправки сигнала на Android
        self.android_ips = []

        self._setup_routes()

    def _setup_routes(self):
        """Настройка маршрутов Flask"""

        @self.app.route('/')
        def index():
            """Главная страница"""
            cameras = self.camera_finder.find_working_cameras()

            return render_template('index.html',
                                   cameras=cameras,
                                   local_ip=self.config.get_local_ip(),
                                   external_ip=self.config.get_external_ip(),
                                   ffmpeg_path=self.config.get_ffmpeg_path(),
                                   mediamtx_path=self.config.get_mediamtx_path())

        @self.app.route('/api/cameras')
        def get_cameras():
            """API для получения списка камер"""
            cameras = self.camera_finder.find_working_cameras()
            return jsonify({"cameras": cameras})

        @self.app.route('/api/microphones')
        def get_microphones():
            """API для получения списка микрофонов"""
            from core.camera_finder import get_available_microphones
            microphones = get_available_microphones(str(self.config.get_ffmpeg_path()))
            return jsonify({"microphones": microphones})

        @self.app.route('/api/cameras/refresh')
        def refresh_cameras():
            """API для обновления списка камер"""
            cameras = self.camera_finder.find_working_cameras()
            return jsonify(cameras)

        @self.app.route('/api/cameras/test', methods=['POST'])
        def test_camera():
            """API для тестирования конкретной камеры"""
            camera_name = request.json.get('camera_name', '')
            if not camera_name:
                return jsonify({
                    "success": False,
                    "message": "❌ Не указана камера для тестирования"
                })

            is_working, message = self.camera_finder.test_camera_directly(camera_name)

            return jsonify({
                "success": is_working,
                "message": message,
                "camera_name": camera_name
            })

        @self.app.route('/api/stream/start', methods=['POST'])
        def start_stream():
            """API для запуска стрима"""
            # Поддерживаем оба формата: form-data и json
            if request.is_json:
                data = request.json
                camera_name = data.get('camera_name', '')
                microphone_name = data.get('microphone_name', '')  # Новый параметр
            else:
                camera_name = request.form.get('camera_name', '')
                microphone_name = request.form.get('microphone_name', '')

            if not camera_name:
                return jsonify({
                    "success": False,
                    "message": "❌ Не выбрана камера"
                })

            # Сначала тестируем камеру
            is_working, test_message = self.camera_finder.test_camera_directly(camera_name)

            if not is_working:
                return jsonify({
                    "success": False,
                    "message": f"❌ Камера не работает: {test_message}"
                })

            # Если камера работает, запускаем стрим
            result = self.stream_manager.start_stream(camera_name, microphone_name if microphone_name else None)
            return jsonify(result)

        @self.app.route('/api/stream/stop', methods=['POST'])
        def stop_stream():
            """API для остановки стрима"""
            success = self.stream_manager.stop_stream()

            return jsonify({
                "success": success,
                "message": "⏹️ Стрим остановлен" if success else "❌ Ошибка остановки стрима"
            })

        @self.app.route('/api/status')
        def get_status():
            """API для получения статуса системы"""
            status = self.stream_manager.get_status()
            return jsonify(status)

        @self.app.route('/api/network')
        def get_network_info():
            """API для получения сетевой информации"""
            try:
                network_info = self.network_manager.get_network_info()

                # Добавляем базовую информацию если NetworkManager не работает
                if not network_info:
                    network_info = {
                        "local_ip": self.config.get_local_ip(),
                        "external_ip": self.config.get_external_ip(),
                        "rtsp_port": 8554,
                        "port_open": False
                    }

                return jsonify(network_info)

            except Exception as e:
                logger.error(f"❌ Ошибка получения сетевой информации: {e}")
                # Возвращаем базовую информацию при ошибке
                return jsonify({
                    "local_ip": self.config.get_local_ip(),
                    "external_ip": self.config.get_external_ip(),
                    "rtsp_port": 8554,
                    "port_open": False,
                    "error": str(e)
                })

        @self.app.route('/api/network/port-check')
        def check_port():
            """API для проверки порта"""
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex(('localhost', 8554))
                    port_open = result == 0

                return jsonify({
                    "port_open": port_open,
                    "port": 8554
                })
            except Exception as e:
                logger.error(f"❌ Ошибка проверки порта: {e}")
                return jsonify({
                    "port_open": False,
                    "port": 8554,
                    "error": str(e)
                })

        @self.app.route('/api/firewall/configure', methods=['POST'])
        def configure_firewall():
            """API для настройки брандмауэра"""
            try:
                result = self.firewall_manager.configure_firewall(8554)
                return jsonify(result)
            except Exception as e:
                logger.error(f"❌ Ошибка настройки брандмауэра: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/configure-advanced', methods=['POST'])
        def configure_firewall_advanced():
            """API для расширенной настройки брандмауэра"""
            try:
                # Получаем параметры из запроса
                data = request.get_json() or {}
                local_ips = data.get('local_ips', [])
                remote_ips = data.get('remote_ips', [])

                result = self.firewall_manager.configure_rtsp_firewall_rules()
                return jsonify(result)
            except Exception as e:
                logger.error(f"❌ Ошибка расширенной настройки брандмауэра: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/open-for-all', methods=['POST'])
        def open_firewall_for_all():
            """API для открытия порта для всех IP"""
            try:
                result = self.firewall_manager.open_port_for_all_ips(8554)
                return jsonify(result)
            except Exception as e:
                logger.error(f"❌ Ошибка открытия порта для всех IP: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/open-for-local', methods=['POST'])
        def open_firewall_for_local():
            """API для открытия порта только для локальной подсети"""
            try:
                result = self.firewall_manager.open_port_for_local_subnet(8554)
                return jsonify(result)
            except Exception as e:
                logger.error(f"❌ Ошибка открытия порта для локальной подсети: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/instructions')
        def get_firewall_instructions():
            """API для получения инструкций по брандмауэру"""
            try:
                return jsonify(self.firewall_manager.get_firewall_instructions())
            except Exception as e:
                logger.error(f"❌ Ошибка получения инструкций: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "manual_instructions": [
                        "1. Откройте Брандмауэр Защитника Windows",
                        "2. Нажмите 'Разрешить взаимодействие с приложением через брандмауэр'",
                        "3. Найдите и отметьте ваше приложение",
                        "4. Или добавьте правило для порта 8554 (TCP)"
                    ]
                })

        @self.app.route('/api/android/ips', methods=['GET'])
        def get_android_ips():
            """API для получения списка IP для Android"""
            return jsonify({"android_ips": self.android_ips})

        @self.app.route('/api/android/ips', methods=['POST'])
        def add_android_ip():
            """API для добавления IP для отправки сигнала"""
            data = request.get_json() or {}
            ip = data.get('ip', '')
            
            if not ip:
                return jsonify({"success": False, "message": "❌ Не указан IP"})
            
            # Проверка формата IP
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(:\d{1,5})?$'
            if not re.match(ip_pattern, ip):
                return jsonify({"success": False, "message": "❌ Неверный формат IP"})
            
            if ip not in self.android_ips:
                self.android_ips.append(ip)
                # Передаем IP в stream_manager
                self.stream_manager.android_ips = self.android_ips
                logger.info(f"📱 Добавлен IP для Android: {ip}")
            
            return jsonify({
                "success": True,
                "message": f"✅ IP {ip} добавлен",
                "android_ips": self.android_ips
            })

        @self.app.route('/api/android/ips/<ip>', methods=['DELETE'])
        def remove_android_ip(ip):
            """API для удаления IP из списка"""
            if ip in self.android_ips:
                self.android_ips.remove(ip)
                # Обновляем stream_manager
                self.stream_manager.android_ips = self.android_ips
                logger.info(f"📱 Удален IP для Android: {ip}")
                return jsonify({"success": True, "android_ips": self.android_ips})
            return jsonify({"success": False, "message": "❌ IP не найден"})

        @self.app.route('/api/android/test', methods=['POST'])
        def test_android_connection():
            """API для тестирования подключения к Android"""
            data = request.get_json() or {}
            ip = data.get('ip', '')

            if not ip:
                return jsonify({"success": False, "message": "❌ Не указан IP"})

            try:
                import requests
                test_url = f"http://{ip}/stream"
                response = requests.get(test_url, timeout=3)
                # NanoHTTPD может вернуть 404 на GET - это нормально
                if response.status_code in [200, 404, 405]:
                    return jsonify({
                        "success": True,
                        "message": f"✅ Android устройство доступно на {ip}"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"⚠️ Ответ: {response.status_code}"
                    })
            except requests.exceptions.Timeout:
                return jsonify({"success": False, "message": "❌ Таймаут - устройство не отвечает"})
            except requests.exceptions.ConnectionError:
                return jsonify({"success": False, "message": "❌ Устройство недоступно"})
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        # ===== API для управления мультиками на Android =====

        @self.app.route('/api/android/videos', methods=['GET'])
        def get_android_videos():
            """API для получения списка видео файлов с Android устройства"""
            ip = request.args.get('ip', '')
            if not ip:
                # Берем первый IP из списка
                if self.android_ips:
                    ip = self.android_ips[0]
                else:
                    return jsonify({"success": False, "message": "❌ Не указан IP Android устройства"})

            try:
                import requests
                response = requests.get(f"http://{ip}/videos", timeout=5)
                if response.status_code == 200:
                    videos = response.json()
                    return jsonify({
                        "success": True,
                        "videos": videos,
                        "ip": ip
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"⚠️ Ответ сервера: {response.status_code}"
                    })
            except requests.exceptions.Timeout:
                return jsonify({"success": False, "message": "❌ Таймаут - устройство не отвечает"})
            except requests.exceptions.ConnectionError:
                return jsonify({"success": False, "message": "❌ Устройство недоступно"})
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        @self.app.route('/api/android/play', methods=['POST'])
        def play_animation():
            """API для запуска видео на Android"""
            data = request.get_json() or {}
            ip = data.get('ip', '')
            video_name = data.get('video_name', '')

            if not ip:
                if self.android_ips:
                    ip = self.android_ips[0]
                else:
                    return jsonify({"success": False, "message": "❌ Не указан IP Android устройства"})

            if not video_name:
                return jsonify({"success": False, "message": "❌ Не указано название видео"})

            try:
                import requests
                response = requests.post(
                    f"http://{ip}/play-animation",
                    json={"video_name": video_name},
                    timeout=5
                )
                if response.status_code == 200:
                    return jsonify({
                        "success": True,
                        "message": f"▶️ Видео '{video_name}' запущено",
                        "ip": ip
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"⚠️ Ответ сервера: {response.status_code}"
                    })
            except requests.exceptions.Timeout:
                return jsonify({"success": False, "message": "❌ Таймаут - устройство не отвечает"})
            except requests.exceptions.ConnectionError:
                return jsonify({"success": False, "message": "❌ Устройство недоступно"})
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        @self.app.route('/api/android/stop', methods=['POST'])
        def stop_animation():
            """API для остановки видео на Android"""
            data = request.get_json() or {}
            ip = data.get('ip', '')

            if not ip:
                if self.android_ips:
                    ip = self.android_ips[0]
                else:
                    return jsonify({"success": False, "message": "❌ Не указан IP Android устройства"})

            try:
                import requests
                response = requests.post(f"http://{ip}/stop-animation", timeout=5)
                if response.status_code == 200:
                    return jsonify({
                        "success": True,
                        "message": "⏹️ Видео остановлено",
                        "ip": ip
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"⚠️ Ответ сервера: {response.status_code}"
                    })
            except requests.exceptions.Timeout:
                return jsonify({"success": False, "message": "❌ Таймаут - устройство не отвечает"})
            except requests.exceptions.ConnectionError:
                return jsonify({"success": False, "message": "❌ Устройство недоступно"})
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        @self.app.route('/api/android/volume', methods=['POST'])
        def set_animation_volume():
            """API для управления громкостью видео на Android"""
            data = request.get_json() or {}
            ip = data.get('ip', '')
            volume = data.get('volume', 1.0)

            if not ip:
                if self.android_ips:
                    ip = self.android_ips[0]
                else:
                    return jsonify({"success": False, "message": "❌ Не указан IP Android устройства"})

            try:
                import requests
                response = requests.post(
                    f"http://{ip}/animation-volume",
                    json={"volume": volume},
                    timeout=5
                )
                if response.status_code == 200:
                    return jsonify({
                        "success": True,
                        "message": f"🔊 Громкость установлена на {int(volume * 100)}%",
                        "ip": ip
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"⚠️ Ответ сервера: {response.status_code}"
                    })
            except requests.exceptions.Timeout:
                return jsonify({"success": False, "message": "❌ Таймаут - устройство не отвечает"})
            except requests.exceptions.ConnectionError:
                return jsonify({"success": False, "message": "❌ Устройство недоступно"})
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        @self.app.route('/api/android/display-mode', methods=['POST'])
        def set_display_mode():
            """API для управления режимом отображения на Android"""
            data = request.get_json() or {}
            ip = data.get('ip', '')
            mode = data.get('mode', 'both')  # 'only_webcam', 'only_cartoon', 'both'

            if not ip:
                if self.android_ips:
                    ip = self.android_ips[0]
                else:
                    return jsonify({"success": False, "message": "❌ Не указан IP Android устройства"})

            try:
                import requests
                response = requests.post(
                    f"http://{ip}/{mode.replace('_', '-')}",
                    timeout=5
                )
                if response.status_code == 200:
                    mode_names = {
                        'only_webcam': 'только веб-камера',
                        'only_cartoon': 'только мультик',
                        'both': 'оба окна'
                    }
                    return jsonify({
                        "success": True,
                        "message": f"📺 Режим: {mode_names.get(mode, mode)}",
                        "ip": ip
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"⚠️ Ответ сервера: {response.status_code}"
                    })
            except requests.exceptions.Timeout:
                return jsonify({"success": False, "message": "❌ Таймаут - устройство не отвечает"})
            except requests.exceptions.ConnectionError:
                return jsonify({"success": False, "message": "❌ Устройство недоступно"})
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        # ===== API для управления громкостью и видимостью =====

        @self.app.route('/api/webcam/volume', methods=['POST'])
        def set_webcam_volume():
            """API для управления громкостью вебкамеры"""
            data = request.get_json() or {}
            volume = data.get('volume', 1.0)
            muted = data.get('muted', False)

            try:
                if muted:
                    self.stream_manager.mute_webcam(True)
                else:
                    self.stream_manager.set_webcam_volume(volume)
                
                return jsonify({
                    "success": True,
                    "message": f"🔊 Громкость вебкамеры: {int(self.stream_manager.webcam_volume * 100)}%",
                    "volume": self.stream_manager.webcam_volume,
                    "muted": self.stream_manager.webcam_muted
                })
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        @self.app.route('/api/webcam/mute', methods=['POST'])
        def toggle_webcam_mute():
            """API для вкл/выкл звука вебкамеры"""
            data = request.get_json() or {}
            mute = data.get('mute', True)

            try:
                self.stream_manager.mute_webcam(mute)
                return jsonify({
                    "success": True,
                    "message": "🔇 Звук выключен" if mute else "🔊 Звук включен",
                    "muted": self.stream_manager.webcam_muted
                })
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        @self.app.route('/api/webcam/visibility', methods=['POST'])
        def set_webcam_visibility():
            """API для скрытия/показа вебкамеры"""
            data = request.get_json() or {}
            visible = data.get('visible', True)

            try:
                self.stream_manager.set_webcam_visibility(visible)
                return jsonify({
                    "success": True,
                    "message": "📷 Вебкамера показана" if visible else "🙈 Вебкамера скрыта",
                    "hidden": self.stream_manager.webcam_hidden
                })
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        @self.app.route('/api/cartoon/visibility', methods=['POST'])
        def set_cartoon_visibility():
            """API для скрытия/показа мультика"""
            data = request.get_json() or {}
            visible = data.get('visible', True)

            try:
                self.stream_manager.set_cartoon_visibility(visible)
                return jsonify({
                    "success": True,
                    "message": "🎬 Мультик показан" if visible else "🙈 Мультик скрыт",
                    "hidden": self.stream_manager.cartoon_hidden
                })
            except Exception as e:
                return jsonify({"success": False, "message": f"❌ Ошибка: {e}"})

        # Обработчик ошибок
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "success": False,
                "message": "❌ Маршрут не найден"
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            logger.error(f"❌ Внутренняя ошибка сервера: {error}")
            return jsonify({
                "success": False,
                "message": "❌ Внутренняя ошибка сервера"
            }), 500

    def start(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """Запуск веб-сервера"""

        def run_flask():
            try:
                logger.info(f"🌐 Запуск веб-сервера на {host}:{port}")
                self.app.run(host=host, port=port, debug=debug, use_reloader=False)
            except Exception as e:
                logger.error(f"❌ Ошибка веб-сервера: {e}")

        # Запускаем Flask в отдельном потоке
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        logger.info("✅ Веб-интерфейс запущен")
        return True