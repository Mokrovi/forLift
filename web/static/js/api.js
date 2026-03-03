// Взаимодействие с API сервера
class APIManager {
    constructor() {
        this.baseURL = '';
        this.cachedIps = [];
    }

    async request(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`❌ API ошибка (${endpoint}):`, error);
            this.showMessage('❌ Ошибка соединения с сервером', true);
            throw error;
        }
    }

    async refreshCameras() {
        try {
            this.showMessage('🔄 Сканирование камер...');
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage("Сканирование камер...", 50);
            }

            const response = await this.request('/api/cameras');
            const cameras = response.cameras || [];

            const select = document.getElementById('camera_name');
            if (select) {
                select.innerHTML = '';
                cameras.forEach(camera => {
                    const option = document.createElement('option');
                    option.value = camera;
                    option.textContent = camera;
                    select.appendChild(option);
                });
            }

            this.showMessage(`✅ Обнаружено: ${cameras.length} камер`);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(`Камер обнаружено: ${cameras.length}`, 50);
            }

        } catch (error) {
            this.showMessage('❌ Ошибка сканирования камер', true);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage("Ошибка сканирования камер", 50);
            }
        }
    }

    async refreshMicrophones() {
        try {
            this.showMessage('🎤 Сканирование микрофонов...');
            
            const response = await this.request('/api/microphones');
            const microphones = response.microphones || [];

            const select = document.getElementById('microphone_name');
            if (select) {
                // Сохраняем первый вариант "Без звука"
                select.innerHTML = '<option value="">🔇 Без звука (только видео)</option>';
                microphones.forEach(mic => {
                    const option = document.createElement('option');
                    option.value = mic;
                    option.textContent = mic;
                    select.appendChild(option);
                });
            }

            this.showMessage(`✅ Найдено: ${microphones.length} микрофонов`);

        } catch (error) {
            this.showMessage('❌ Ошибка сканирования микрофонов', true);
        }
    }

    async startStream() {
        const cameraSelect = document.getElementById('camera_name');
        const micSelect = document.getElementById('microphone_name');
        
        if (!cameraSelect) {
            this.showMessage('❌ Элемент выбора камеры не найден', true);
            return;
        }

        const cameraName = cameraSelect.value;
        const microphoneName = micSelect ? micSelect.value : '';
        
        if (!cameraName) {
            this.showMessage('❌ Не выбрана камера', true);
            return;
        }

        this.showMessage('🚀 Запуск стрима...');
        this.showLoadingStatus();

        try {
            // Анимация процесса в терминале
            if (window.app && window.app.terminal) {
                await this.startProcessAnimation();
            }

            const requestBody = {
                camera_name: cameraName
            };
            if (microphoneName) {
                requestBody.microphone_name = microphoneName;
            }

            const result = await this.request('/api/stream/start', {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });

            this.showMessage(result.message);

            if (window.app && window.app.terminal) {
                if (result.success) {
                    await window.app.terminal.typeMessage("Трансляция успешно запущена", 50);
                } else {
                    await window.app.terminal.typeMessage("Ошибка запуска трансляции", 50);
                }
            }

            // Обновляем статус через 3 секунды
            setTimeout(() => this.checkStatus(), 3000);

        } catch (error) {
            this.showMessage('❌ Критическая ошибка: ' + error.message, true);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage("Ошибка запуска трансляции", 50);
            }
        }
    }

    async stopStream() {
        this.showMessage('🔄 Остановка стрима...');
        if (window.app && window.app.terminal) {
            await window.app.terminal.typeMessage("Остановка трансляции...", 50);
        }

        try {
            const result = await this.request('/api/stream/stop', {
                method: 'POST'
            });

            this.showMessage(result.message);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage("Трансляция остановлена", 50);
            }

            setTimeout(() => this.checkStatus(), 1000);

        } catch (error) {
            this.showMessage('❌ Ошибка остановки: ' + error.message, true);
        }
    }

    async checkStatus() {
        try {
            const status = await this.request('/api/status');

            const mediamtxStatus = document.getElementById('mediamtxStatus');
            const ffmpegStatus = document.getElementById('ffmpegStatus');

            if (mediamtxStatus) {
                mediamtxStatus.textContent = status.mediamtx_running ? '✅ Онлайн' : '❌ Оффлайн';
                mediamtxStatus.className = status.mediamtx_running ? 'status-online' : 'status-offline';
            }

            if (ffmpegStatus) {
                ffmpegStatus.textContent = status.ffmpeg_running ? '✅ Трансляция' : '❌ Остановлен';
                ffmpegStatus.className = status.ffmpeg_running ? 'status-online' : 'status-offline';
            }

        } catch (error) {
            const mediamtxStatus = document.getElementById('mediamtxStatus');
            const ffmpegStatus = document.getElementById('ffmpegStatus');

            if (mediamtxStatus) mediamtxStatus.textContent = '❌ Ошибка';
            if (ffmpegStatus) ffmpegStatus.textContent = '❌ Ошибка';
        }
    }

    async loadNetworkInfo() {
    try {
        const network = await this.request('/api/network');

        // Обновляем внешний IP
        const externalIpElement = document.getElementById('externalIp');
        if (externalIpElement) {
            externalIpElement.textContent = network.external_ip;
        }

        // Обновляем внешний URL
        const externalUrlElement = document.getElementById('externalUrl');
        if (externalUrlElement) {
            externalUrlElement.innerHTML = `<code>rtsp://${network.external_ip}:8554/live/stream</code>`;
        }

        // Обновляем статус порта
        await this.checkPortAccess();

    } catch (error) {
        console.error('❌ Ошибка загрузки сетевой информации:', error);

        const externalIpElement = document.getElementById('externalIp');
        if (externalIpElement) {
            externalIpElement.textContent = 'Ошибка';
        }

        const externalUrlElement = document.getElementById('externalUrl');
        if (externalUrlElement) {
            externalUrlElement.innerHTML = '<code>Ошибка загрузки</code>';
        }
    }
}

    async checkPortAccess() {
    try {
        const portStatusElement = document.getElementById('portStatus');
        if (portStatusElement) {
            portStatusElement.innerHTML = '<span class="loading-dots">Проверка</span>';
        }

        const result = await this.request('/api/network/port-check');

        if (portStatusElement) {
            if (result.port_open) {
                portStatusElement.innerHTML = '<span class="status-online">✅ Открыт</span>';
                this.showMessage('✅ Порт 8554 открыт локально');
            } else {
                portStatusElement.innerHTML = '<span class="status-offline">❌ Закрыт</span>';
                this.showMessage('❌ Порт 8554 не открыт', true);
            }
        }

    } catch (error) {
        const portStatusElement = document.getElementById('portStatus');
        if (portStatusElement) {
            portStatusElement.innerHTML = '<span class="status-offline">❌ Ошибка</span>';
        }
    }
}

    async configureFirewall() {
        try {
            this.showMessage('🔧 Настройка брандмауэра...');

            const result = await this.request('/api/firewall/configure', {
                method: 'POST'
            });

            if (result.success) {
                this.showMessage('✅ ' + result.message);
                if (result.admin_required) {
                    this.showMessage('💡 Запустите программу от имени администратора');
                }
            } else {
                this.showMessage('❌ ' + result.message, true);
            }

        } catch (error) {
            this.showMessage('❌ Ошибка настройки брандмауэра', true);
        }
    }

    copyLocalUrl() {
    const urlElement = document.getElementById('localUrl');
    if (urlElement) {
        const url = urlElement.textContent;
        navigator.clipboard.writeText(url).then(() => {
            this.showMessage('✅ Локальный URL скопирован');
        });
    }
}

    copyExternalUrl() {
    const urlElement = document.getElementById('externalUrl');
    if (urlElement) {
        const url = urlElement.textContent;
        if (url && !url.includes('Определение') && !url.includes('Ошибка')) {
            navigator.clipboard.writeText(url).then(() => {
                this.showMessage('✅ Внешний URL скопирован');
            });
        } else {
            this.showMessage('❌ Нет доступного URL для копирования', true);
        }
    }
}

    async startProcessAnimation() {
        if (!window.app || !window.app.terminal) return;

        const steps = [
            "Поиск камеры в системе...",
            "Тестирование камеры...",
            "Запуск MediaMTX сервера...",
            "Запуск FFmpeg трансляции...",
            "Установка RTSP соединения...",
            "Трансляция активна"
        ];

        await window.app.terminal.typeMessage("Начало процесса запуска трансляции...", 50);

        for (const step of steps) {
            await new Promise(resolve => setTimeout(resolve, 800));
            await window.app.terminal.typeMessage(step, 40);
        }
    }

    showMessage(message, isError = false) {
        const resultDiv = document.getElementById('result');
        if (resultDiv) {
            resultDiv.innerHTML = `<div class="alert ${isError ? 'alert-error' : 'alert-success'}">${message}</div>`;
        }
    }

    showLoadingStatus() {
        const mediamtxStatus = document.getElementById('mediamtxStatus');
        const ffmpegStatus = document.getElementById('ffmpegStatus');

        if (mediamtxStatus) {
            mediamtxStatus.innerHTML = '<span class="loading-dots">Запуск</span>';
        }
        if (ffmpegStatus) {
            ffmpegStatus.innerHTML = '<span class="loading-dots">Запуск</span>';
        }
    }

    // === Android IP Management ===

    async getAndroidIps() {
        try {
            const result = await this.request('/api/android/ips');
            this.cachedIps = result.android_ips || [];
            return result;
        } catch (error) {
            console.error('Ошибка получения Android IP:', error);
            return { android_ips: [] };
        }
    }

    async addAndroidIp(ip) {
        try {
            return await this.request('/api/android/ips', {
                method: 'POST',
                body: JSON.stringify({ ip })
            });
        } catch (error) {
            throw error;
        }
    }

    async removeAndroidIp(ip) {
        try {
            return await this.request(`/api/android/ips/${encodeURIComponent(ip)}`, {
                method: 'DELETE'
            });
        } catch (error) {
            throw error;
        }
    }

    async testAndroidConnection(ip) {
        try {
            return await this.request('/api/android/test', {
                method: 'POST',
                body: JSON.stringify({ ip })
            });
        } catch (error) {
            throw error;
        }
    }

    // === Управление мультиком ===
    async getAndroidVideos(ip) {
        try {
            return await this.request('/api/android/videos?ip=' + encodeURIComponent(ip));
        } catch (error) {
            console.error('Ошибка получения видео:', error);
            return { success: false, message: error.message };
        }
    }

    async playAnimation(ip, videoName) {
        try {
            return await this.request('/api/android/play', {
                method: 'POST',
                body: JSON.stringify({ ip: ip, video_name: videoName })
            });
        } catch (error) {
            throw error;
        }
    }

    async stopAnimation(ip) {
        try {
            return await this.request('/api/android/stop', {
                method: 'POST',
                body: JSON.stringify({ ip: ip })
            });
        } catch (error) {
            throw error;
        }
    }

    async setCartoonVolume(ip, volume) {
        try {
            return await this.request('/api/android/volume', {
                method: 'POST',
                body: JSON.stringify({ ip: ip, volume: volume })
            });
        } catch (error) {
            throw error;
        }
    }

    async setWebcamVolume(ip, volume) {
        try {
            return await this.request('/api/android/webcam-volume', {
                method: 'POST',
                body: JSON.stringify({ ip: ip, volume: volume })
            });
        } catch (error) {
            throw error;
        }
    }

    async setDisplayMode(ip, mode) {
        try {
            return await this.request('/api/android/display-mode', {
                method: 'POST',
                body: JSON.stringify({ ip: ip, mode: mode })
            });
        } catch (error) {
            throw error;
        }
    }

    async setWebcamVolume(volume) {
        try {
            return await this.request('/api/webcam/volume', {
                method: 'POST',
                body: JSON.stringify({ volume: volume })
            });
        } catch (error) {
            throw error;
        }
    }

    async muteWebcam(mute) {
        try {
            return await this.request('/api/webcam/mute', {
                method: 'POST',
                body: JSON.stringify({ mute: mute })
            });
        } catch (error) {
            throw error;
        }
    }

    async setWebcamVisibility(visible) {
        try {
            return await this.request('/api/webcam/visibility', {
                method: 'POST',
                body: JSON.stringify({ visible: visible })
            });
        } catch (error) {
            throw error;
        }
    }

    async setCartoonVisibility(visible) {
        try {
            return await this.request('/api/cartoon/visibility', {
                method: 'POST',
                body: JSON.stringify({ visible: visible })
            });
        } catch (error) {
            throw error;
        }
    }
}