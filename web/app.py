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

        # Инициализируем менеджеры ОДИН РАЗ
        self.camera_finder = CameraFinder(str(self.config.get_ffmpeg_path()))
        self.network_manager = NetworkManager()
        self.firewall_manager = FirewallManager()

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
                camera_name = request.json.get('camera_name', '')
            else:
                camera_name = request.form.get('camera_name', '')

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
            result = self.stream_manager.start_stream(camera_name)
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