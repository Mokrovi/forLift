from flask import Flask, render_template, request, jsonify
import logging
import threading
from typing import Dict
import socket
import requests
import json

from core.camera_finder import CameraFinder
from core.network_manager import NetworkManager
from core.firewall_manager import FirewallManager

logger = logging.getLogger(__name__)


class WebApp:
    def __init__(self, stream_manager, config):
        self.stream_manager = stream_manager
        self.config = config
        self.app = Flask(__name__,
                         template_folder=str(config.TEMPLATES_DIR),
                         static_folder=str(config.STATIC_DIR))

        self.camera_finder = CameraFinder(str(self.config.get_ffmpeg_path()))
        self.network_manager = NetworkManager()
        self.firewall_manager = FirewallManager()

        self._setup_routes()

    def _send_to_android(self, android_ip, endpoint, data):
        try:
            url = f"http://{android_ip}:8080{endpoint}"

            logger.info(f"Отправка на Android {android_ip}: {endpoint} - {data}")

            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Команда отправлена на Android",
                    "android_response": response.text
                }
            else:
                return {
                    "success": False,
                    "message": f"Ошибка Android: {response.status_code}",
                    "android_response": response.text
                }

        except requests.exceptions.ConnectTimeout:
            return {
                "success": False,
                "message": "Таймаут подключения к Android устройству"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": "Не удалось подключиться к Android устройству"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка отправки: {str(e)}"
            }

    def _check_android_status(self, android_ip):
        try:
            url = f"http://{android_ip}:8080/videos"

            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                return {
                    "success": True,
                    "online": True,
                    "message": "Android устройство доступно"
                }
            else:
                return {
                    "success": False,
                    "online": False,
                    "message": f"Android устройство не отвечает: {response.status_code}"
                }

        except requests.exceptions.ConnectTimeout:
            return {
                "success": False,
                "online": False,
                "message": "Таймаут подключения к Android"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "online": False,
                "message": "Не удалось подключиться к Android"
            }
        except Exception as e:
            return {
                "success": False,
                "online": False,
                "message": f"Ошибка проверки: {str(e)}"
            }

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            cameras = self.camera_finder.find_working_cameras()

            return render_template('index.html',
                                   cameras=cameras,
                                   local_ip=self.config.get_local_ip(),
                                   external_ip=self.config.get_external_ip(),
                                   ffmpeg_path=self.config.get_ffmpeg_path(),
                                   mediamtx_path=self.config.get_mediamtx_path())

        @self.app.route('/api/cameras')
        def get_cameras():
            cameras = self.camera_finder.find_working_cameras()
            return jsonify({"cameras": cameras})

        @self.app.route('/api/cameras/refresh')
        def refresh_cameras():
            cameras = self.camera_finder.find_working_cameras()
            return jsonify(cameras)

        @self.app.route('/api/cameras/test', methods=['POST'])
        def test_camera():
            camera_name = request.json.get('camera_name', '')
            if not camera_name:
                return jsonify({
                    "success": False,
                    "message": "Не указана камера для тестирования"
                })

            is_working, message = self.camera_finder.test_camera_directly(camera_name)

            return jsonify({
                "success": is_working,
                "message": message,
                "camera_name": camera_name
            })

        @self.app.route('/api/stream/start', methods=['POST'])
        def start_stream():
            if request.is_json:
                camera_name = request.json.get('camera_name', '')
            else:
                camera_name = request.form.get('camera_name', '')

            if not camera_name:
                return jsonify({
                    "success": False,
                    "message": "Не выбрана камера"
                })

            is_working, test_message = self.camera_finder.test_camera_directly(camera_name)

            if not is_working:
                return jsonify({
                    "success": False,
                    "message": f"Камера не работает: {test_message}"
                })

            result = self.stream_manager.start_stream(camera_name)
            return jsonify(result)

        @self.app.route('/api/stream/stop', methods=['POST'])
        def stop_stream():
            success = self.stream_manager.stop_stream()

            return jsonify({
                "success": success,
                "message": "Стрим остановлен" if success else "Ошибка остановки стрима"
            })

        @self.app.route('/api/android/videos/list', methods=['POST'])
        def get_android_videos_list():
            try:
                data = request.get_json() or {}
                android_ip = data.get('android_ip', '')

                if not android_ip:
                    return jsonify({
                        "success": False,
                        "message": "Не указан IP адрес Android устройства"
                    })

                logger.info(f"Запрос списка видео с Android {android_ip}")

                try:
                    url = f"http://{android_ip}:8080/videos"
                    response = requests.get(url, timeout=5)

                    if response.status_code == 200:
                        try:
                            videos_data = response.json()
                            logger.info(f"Получены данные с Android: {videos_data}")

                            videos = []
                            if isinstance(videos_data, list):
                                for item in videos_data:
                                    if isinstance(item, dict) and 'name' in item:
                                        videos.append(item['name'])
                                    elif isinstance(item, str):
                                        videos.append(item)
                            elif isinstance(videos_data, dict) and 'videos' in videos_data:
                                videos = videos_data['videos']

                            if videos:
                                return jsonify({
                                    "success": True,
                                    "videos": videos,
                                    "message": f"Получено {len(videos)} видеофайлов с Android",
                                    "source": "android"
                                })
                            else:
                                return jsonify({
                                    "success": False,
                                    "videos": [],
                                    "message": "На Android нет видеофайлов или формат ответа не поддерживается"
                                })

                        except json.JSONDecodeError:
                            logger.warning("Android вернул не JSON ответ")
                            return jsonify({
                                "success": False,
                                "videos": [],
                                "message": "Android вернул некорректный ответ (не JSON)"
                            })

                    else:
                        return jsonify({
                            "success": False,
                            "videos": [],
                            "message": f"Android устройство не отвечает: {response.status_code}"
                        })

                except requests.exceptions.ConnectTimeout:
                    return jsonify({
                        "success": False,
                        "videos": [],
                        "message": "Таймаут подключения к Android устройству"
                    })
                except requests.exceptions.ConnectionError:
                    return jsonify({
                        "success": False,
                        "videos": [],
                        "message": "Не удалось подключиться к Android устройству"
                    })
                except Exception as e:
                    logger.warning(f"Ошибка подключения к Android: {e}")
                    return jsonify({
                        "success": False,
                        "videos": [],
                        "message": f"Ошибка подключения: {str(e)}"
                    })

            except Exception as e:
                logger.error(f"Ошибка получения списка видео с Android: {e}")
                return jsonify({
                    "success": False,
                    "videos": [],
                    "message": f"Внутренняя ошибка сервера: {str(e)}"
                })

        @self.app.route('/api/android/video/play', methods=['POST'])
        def play_android_video():
            try:
                data = request.get_json() or {}
                video_name = data.get('video_name', '')
                android_ip = data.get('android_ip', '')

                if not video_name:
                    return jsonify({
                        "success": False,
                        "message": "Не указано название видео"
                    })

                if not android_ip:
                    return jsonify({
                        "success": False,
                        "message": "Не указан IP адрес Android устройства"
                    })

                result = self._send_to_android(android_ip, '/play-animation', {
                    'video_name': video_name
                })

                return jsonify(result)

            except Exception as e:
                logger.error(f"Ошибка отправки команды на Android: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}"
                })

        @self.app.route('/api/android/video/stop', methods=['POST'])
        def stop_android_video():
            try:
                data = request.get_json() or {}
                android_ip = data.get('android_ip', '')

                if not android_ip:
                    return jsonify({
                        "success": False,
                        "message": "Не указан IP адрес Android устройства"
                    })

                result = self._send_to_android(android_ip, '/stop-animation', {})

                return jsonify(result)

            except Exception as e:
                logger.error(f"Ошибка отправки команды остановки: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}"
                })

        @self.app.route('/api/android/video/volume', methods=['POST'])
        def set_android_video_volume():
            try:
                data = request.get_json() or {}
                volume = float(data.get('volume', 1.0))
                android_ip = data.get('android_ip', '')

                if not android_ip:
                    return jsonify({
                        "success": False,
                        "message": "Не указан IP адрес Android устройства"
                    })

                volume = max(0.0, min(1.0, volume))

                result = self._send_to_android(android_ip, '/animation-volume', {
                    'volume': volume
                })

                return jsonify(result)

            except Exception as e:
                logger.error(f"Ошибка отправки команды громкости: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}"
                })

        @self.app.route('/api/android/video/status', methods=['POST'])
        def get_android_video_status():
            try:
                data = request.get_json() or {}
                android_ip = data.get('android_ip', '')

                if not android_ip:
                    return jsonify({
                        "success": False,
                        "message": "Не указан IP адрес Android устройства"
                    })

                result = self._check_android_status(android_ip)

                return jsonify(result)

            except Exception as e:
                logger.error(f"Ошибка проверки статуса Android: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "online": False
                })

        @self.app.route('/api/status')
        def get_status():
            status = self.stream_manager.get_status()
            return jsonify(status)

        @self.app.route('/api/network')
        def get_network_info():
            try:
                network_info = self.network_manager.get_network_info()

                if not network_info:
                    network_info = {
                        "local_ip": self.config.get_local_ip(),
                        "external_ip": self.config.get_external_ip(),
                        "rtsp_port": 8554,
                        "port_open": False
                    }

                return jsonify(network_info)

            except Exception as e:
                logger.error(f"Ошибка получения сетевой информации: {e}")
                return jsonify({
                    "local_ip": self.config.get_local_ip(),
                    "external_ip": self.config.get_external_ip(),
                    "rtsp_port": 8554,
                    "port_open": False,
                    "error": str(e)
                })

        @self.app.route('/api/network/port-check')
        def check_port():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex(('localhost', 8554))
                    port_open = result == 0

                return jsonify({
                    "port_open": port_open,
                    "port": 8554
                })
            except Exception as e:
                logger.error(f"Ошибка проверки порта: {e}")
                return jsonify({
                    "port_open": False,
                    "port": 8554,
                    "error": str(e)
                })

        @self.app.route('/api/firewall/configure', methods=['POST'])
        def configure_firewall():
            try:
                result = self.firewall_manager.configure_firewall(8554)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Ошибка настройки брандмауэра: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/configure-advanced', methods=['POST'])
        def configure_firewall_advanced():
            try:
                data = request.get_json() or {}
                local_ips = data.get('local_ips', [])
                remote_ips = data.get('remote_ips', [])

                result = self.firewall_manager.configure_rtsp_firewall_rules()
                return jsonify(result)
            except Exception as e:
                logger.error(f"Ошибка расширенной настройки брандмауэра: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/open-for-all', methods=['POST'])
        def open_firewall_for_all():
            try:
                result = self.firewall_manager.open_port_for_all_ips(8554)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Ошибка открытия порта для всех IP: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/open-for-local', methods=['POST'])
        def open_firewall_for_local():
            try:
                result = self.firewall_manager.open_port_for_local_subnet(8554)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Ошибка открытия порта для локальной подсети: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Ошибка: {str(e)}",
                    "admin_required": True
                })

        @self.app.route('/api/firewall/instructions')
        def get_firewall_instructions():
            try:
                return jsonify(self.firewall_manager.get_firewall_instructions())
            except Exception as e:
                logger.error(f"Ошибка получения инструкций: {e}")
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

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "success": False,
                "message": "Маршрут не найден"
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            logger.error(f"Внутренняя ошибка сервера: {error}")
            return jsonify({
                "success": False,
                "message": "Внутренняя ошибка сервера"
            }), 500

    def start(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        def run_flask():
            try:
                logger.info(f"Запуск веб-сервера на {host}:{port}")
                self.app.run(host=host, port=port, debug=debug, use_reloader=False)
            except Exception as e:
                logger.error(f"Ошибка веб-сервера: {e}")

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        logger.info("Веб-интерфейс запущен")
        return True