class APIManager {
    constructor() {
        this.baseURL = '';
        this.currentAndroidVolume = 1.0;
        this.androidIp = '';
        this.localIp = '';
        this.externalIp = '';
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
            console.error(`API ошибка (${endpoint}):`, error);
            this.showMessage('Ошибка соединения с сервером', true);
            throw error;
        }
    }

    async refreshCameras() {
        try {
            this.showMessage('Сканирование камер...');
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

            this.showMessage(`Обнаружено: ${cameras.length} камер`);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(`Камер обнаружено: ${cameras.length}`, 50);
            }

        } catch (error) {
            this.showMessage('Ошибка сканирования камер', true);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage("Ошибка сканирования камер", 50);
            }
        }
    }

    async startStream() {
        const cameraSelect = document.getElementById('camera_name');
        if (!cameraSelect) {
            this.showMessage('Элемент выбора камеры не найден', true);
            return;
        }

        const cameraName = cameraSelect.value;
        if (!cameraName) {
            this.showMessage('Не выбрана камера', true);
            return;
        }

        this.showMessage('Запуск стрима...');
        this.showLoadingStatus();

        try {
            if (window.app && window.app.terminal) {
                await this.startProcessAnimation();
            }

            const result = await this.request('/api/stream/start', {
                method: 'POST',
                body: JSON.stringify({ camera_name: cameraName })
            });

            this.showMessage(result.message);

            if (window.app && window.app.terminal) {
                if (result.success) {
                    await window.app.terminal.typeMessage("Трансляция успешно запущена", 50);
                } else {
                    await window.app.terminal.typeMessage("Ошибка запуска трансляции", 50);
                }
            }

            setTimeout(() => this.checkStatus(), 3000);

        } catch (error) {
            this.showMessage('Критическая ошибка: ' + error.message, true);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage("Ошибка запуска трансляции", 50);
            }
        }
    }

    async stopStream() {
        this.showMessage('Остановка стрима...');
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
            this.showMessage('Ошибка остановки: ' + error.message, true);
        }
    }

    async loadNetworkInfo() {
        try {
            const network = await this.request('/api/network');

            this.localIp = network.local_ip;
            this.externalIp = network.external_ip;

            const externalIpElement = document.getElementById('externalIp');
            if (externalIpElement) {
                externalIpElement.textContent = network.external_ip;
            }

            const externalUrlElement = document.getElementById('externalUrl');
            if (externalUrlElement) {
                externalUrlElement.innerHTML = `<code>rtsp://${network.external_ip}:8554/live/stream</code>`;
            }

            await this.checkPortAccess();

        } catch (error) {
            console.error('Ошибка загрузки сетевой информации:', error);
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
                    portStatusElement.innerHTML = '<span class="status-online">Открыт</span>';
                    this.showMessage('Порт 8554 открыт локально');
                } else {
                    portStatusElement.innerHTML = '<span class="status-offline">Закрыт</span>';
                    this.showMessage('Порт 8554 не открыт', true);
                }
            }

        } catch (error) {
            const portStatusElement = document.getElementById('portStatus');
            if (portStatusElement) {
                portStatusElement.innerHTML = '<span class="status-offline">Ошибка</span>';
            }
        }
    }

    async checkStatus() {
        try {
            const status = await this.request('/api/status');

            const mediamtxStatus = document.getElementById('mediamtxStatus');
            const ffmpegStatus = document.getElementById('ffmpegStatus');

            if (mediamtxStatus) {
                mediamtxStatus.textContent = status.mediamtx_running ? 'Онлайн' : 'Оффлайн';
                mediamtxStatus.className = status.mediamtx_running ? 'status-online' : 'status-offline';
            }

            if (ffmpegStatus) {
                ffmpegStatus.textContent = status.ffmpeg_running ? 'Трансляция' : 'Остановлен';
                ffmpegStatus.className = status.ffmpeg_running ? 'status-online' : 'status-offline';
            }

        } catch (error) {
            const mediamtxStatus = document.getElementById('mediamtxStatus');
            const ffmpegStatus = document.getElementById('ffmpegStatus');
            if (mediamtxStatus) mediamtxStatus.textContent = 'Ошибка';
            if (ffmpegStatus) ffmpegStatus.textContent = 'Ошибка';
        }
    }

    async loadAndroidVideos() {
        console.log('Загрузка видео - начало');

        const androidIp = this.validateAndroidIp();
        if (!androidIp) {
            return;
        }

        console.log('IP Android получен:', androidIp);

        try {
            this.showMessage('Загрузка списка видео с Android...');

            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(`Загрузка видео с Android ${androidIp}...`, 50);
            }

            const videosResponse = await this.request('/api/android/videos/list', {
                method: 'POST',
                body: JSON.stringify({
                    android_ip: androidIp
                })
            });

            console.log('Ответ от сервера:', videosResponse);

            if (!videosResponse.success) {
                const errorMsg = videosResponse.message || 'Не удалось загрузить список видео';
                this.showMessage(errorMsg, true);
                if (window.app && window.app.terminal) {
                    await window.app.terminal.typeMessage(errorMsg, 50);
                }
                this.enableAndroidControls(false);
                return [];
            }

            const videos = videosResponse.videos || [];

            const select = document.getElementById('androidVideoSelect');
            if (select) {
                select.innerHTML = '';
                if (videos.length > 0) {
                    videos.forEach(video => {
                        const option = document.createElement('option');
                        option.value = video;
                        option.textContent = video;
                        select.appendChild(option);
                    });
                    select.disabled = false;

                    this.enableAndroidControls(true);

                    const successMsg = `Загружено ${videos.length} видеофайлов`;
                    this.showMessage(successMsg);
                    if (window.app && window.app.terminal) {
                        await window.app.terminal.typeMessage(successMsg, 50);
                    }
                } else {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'Нет видеофайлов';
                    select.appendChild(option);
                    select.disabled = false;

                    const errorMsg = 'На Android нет видеофайлов';
                    this.showMessage(errorMsg, true);
                    if (window.app && window.app.terminal) {
                        await window.app.terminal.typeMessage(errorMsg, 50);
                    }
                }
            }

            return videos;

        } catch (error) {
            console.error('Ошибка загрузки видео:', error);
            const errorMsg = 'Ошибка загрузки видео: ' + error.message;
            this.showMessage(errorMsg, true);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(errorMsg, 50);
            }
            this.enableAndroidControls(false);
            return [];
        }
    }

    async playAndroidVideo() {
        const androidIp = this.validateAndroidIp();
        if (!androidIp) {
            return;
        }

        const videoSelect = document.getElementById('androidVideoSelect');
        if (!videoSelect || videoSelect.disabled) {
            this.showMessage('Сначала загрузите список видео', true);
            return;
        }

        const videoName = videoSelect.value;
        if (!videoName) {
            this.showMessage('Не выбрано видео', true);
            return;
        }

        try {
            this.showMessage('Отправка команды воспроизведения...');

            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(`Отправка команды воспроизведения: ${videoName}`, 50);
            }

            const result = await this.request('/api/android/video/play', {
                method: 'POST',
                body: JSON.stringify({
                    android_ip: androidIp,
                    video_name: videoName
                })
            });

            this.showMessage(result.message);

            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(result.message, 50);
                if (result.android_response) {
                    await window.app.terminal.typeMessage(`Ответ: ${result.android_response}`, 50);
                }
            }

        } catch (error) {
            const errorMsg = 'Ошибка отправки команды: ' + error.message;
            this.showMessage(errorMsg, true);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(errorMsg, 50);
            }
        }
    }

    async stopAndroidVideo() {
        const androidIp = this.validateAndroidIp();
        if (!androidIp) {
            return;
        }

        try {
            this.showMessage('Отправка команды остановки...');

            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage("Отправка команды остановки видео", 50);
            }

            const result = await this.request('/api/android/video/stop', {
                method: 'POST',
                body: JSON.stringify({
                    android_ip: androidIp
                })
            });

            this.showMessage(result.message);

            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(result.message, 50);
                if (result.android_response) {
                    await window.app.terminal.typeMessage(`Ответ: ${result.android_response}`, 50);
                }
            }

        } catch (error) {
            const errorMsg = 'Ошибка отправки команды остановки: ' + error.message;
            this.showMessage(errorMsg, true);
            if (window.app && window.app.terminal) {
                await window.app.terminal.typeMessage(errorMsg, 50);
            }
        }
    }

    async setAndroidVolume(volume) {
        const androidIp = this.validateAndroidIp();
        if (!androidIp) {
            return;
        }

        try {
            await this.request('/api/android/video/volume', {
                method: 'POST',
                body: JSON.stringify({
                    android_ip: androidIp,
                    volume: volume
                })
            });
        } catch (error) {
            console.error('Ошибка установки громкости:', error);
        }
    }

    async checkAndroidConnection() {
        const androidIp = this.validateAndroidIp();
        if (!androidIp) {
            return;
        }

        try {
            this.showMessage('Проверка подключения к Android...');

            const result = await this.request('/api/android/video/status', {
                method: 'POST',
                body: JSON.stringify({
                    android_ip: androidIp
                })
            });

            const statusElement = document.getElementById('androidStatus');
            if (statusElement) {
                if (result.online) {
                    statusElement.innerHTML = '<span class="status-online">Подключено</span>';
                    this.showMessage('Android устройство доступно');
                } else {
                    statusElement.innerHTML = '<span class="status-offline">Не доступно</span>';
                    this.showMessage('Android устройство не доступно', true);
                }
            }

            return result;

        } catch (error) {
            const statusElement = document.getElementById('androidStatus');
            if (statusElement) {
                statusElement.innerHTML = '<span class="status-offline">Ошибка проверки</span>';
            }
            this.showMessage('Ошибка проверки подключения: ' + error.message, true);
            return { online: false };
        }
    }

    validateAndroidIp() {
        const androidIp = this.getAndroidIp();
        if (!androidIp) {
            this.showMessage('Введите корректный IP адрес Android устройства', true);
            return null;
        }
        return androidIp;
    }

    getAndroidIp() {
        const input = document.getElementById('androidIp');
        console.log('Поле androidIp:', input);
        console.log('Значение поля:', input?.value);

        if (input && this.isValidIP(input.value.trim())) {
            this.androidIp = input.value.trim();
            return input.value.trim();
        }
        return '';
    }

    isValidIP(ip) {
        const ipRegex = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/;
        if (!ipRegex.test(ip)) return false;

        const parts = ip.split('.');
        return parts.every(part => {
            const num = parseInt(part, 10);
            return num >= 0 && num <= 255;
        });
    }

    enableAndroidControls(enable) {
        const videoSelect = document.getElementById('androidVideoSelect');
        const playBtn = document.querySelector('button[onclick="playAndroidVideo()"]');
        const stopBtn = document.querySelector('button[onclick="stopAndroidVideo()"]');

        if (videoSelect) videoSelect.disabled = !enable;
        if (playBtn) playBtn.disabled = !enable;
        if (stopBtn) stopBtn.disabled = !enable;
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

    copyLocalUrl() {
        const urlElement = document.getElementById('localUrl');
        if (urlElement) {
            const url = urlElement.textContent;
            navigator.clipboard.writeText(url).then(() => {
                this.showMessage('Локальный URL скопирован');
            });
        }
    }

    copyExternalUrl() {
        const urlElement = document.getElementById('externalUrl');
        if (urlElement) {
            const url = urlElement.textContent;
            if (url && !url.includes('Определение') && !url.includes('Ошибка')) {
                navigator.clipboard.writeText(url).then(() => {
                    this.showMessage('Внешний URL скопирован');
                });
            } else {
                this.showMessage('Нет доступного URL для копирования', true);
            }
        }
    }

    async configureFirewall() {
        try {
            this.showMessage('Настройка брандмауэра...');
            const result = await this.request('/api/firewall/configure', { method: 'POST' });

            if (result.success) {
                this.showMessage(result.message);
                if (result.admin_required) {
                    this.showMessage('Запустите программу от имени администратора');
                }
            } else {
                this.showMessage(result.message, true);
            }
        } catch (error) {
            this.showMessage('Ошибка настройки брандмауэра', true);
        }
    }
}