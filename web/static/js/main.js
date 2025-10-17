// Основная логика приложения
class RTSPStreamApp {
    constructor() {
        this.terminal = new TerminalManager();
        this.api = new APIManager();
        this.ui = window.uiManager;
        this.init();
    }

    init() {
        console.log('🚀 Инициализация RTSP Stream App');

        // Загружаем сохраненную тему
        this.loadTheme();

        // Инициализируем терминал
        this.terminal.initialize();

        // Загружаем начальные данные
        this.loadInitialData();

        // Настраиваем обработчики
        this.setupEventListeners();

        // Запускаем периодические проверки
        this.startPeriodicChecks();
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('app-theme') || 'cyber';
        document.body.className = `${savedTheme}-theme`;

        // Обновляем активную кнопку темы
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.toggle('active',
                btn.textContent.includes(savedTheme === 'cyber' ? 'Тёмная' : 'Светлая')
            );
        });
    }

    switchTheme(theme) {
        document.body.className = `${theme}-theme`;
        localStorage.setItem('app-theme', theme);

        // Обновляем кнопки
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.remove('active');
            if ((theme === 'cyber' && btn.textContent.includes('Тёмная')) ||
                (theme === 'official' && btn.textContent.includes('Светлая'))) {
                btn.classList.add('active');
            }
        });
    }

    async loadInitialData() {
        await this.api.checkStatus();
        await this.api.loadNetworkInfo();
        await this.terminal.typeMessage('Система готова к работе', 50);
    }

    setupEventListeners() {
        console.log('📝 Настройка обработчиков событий');

        // Добавляем обработчики для кнопок темы
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const theme = e.target.textContent.includes('Тёмная') ? 'cyber' : 'official';
                this.switchTheme(theme);
            });
        });
    }

    startPeriodicChecks() {
        // Проверка статуса каждые 10 секунд
        setInterval(() => {
            this.api.checkStatus();
        }, 10000);

        // Случайные системные сообщения каждые 30 секунд
        setInterval(() => {
            this.terminal.randomSystemMessage();
        }, 30000);
    }
}

// Глобальные функции для HTML onclick
function switchTheme(theme) {
    if (window.app) {
        window.app.switchTheme(theme);
    }
}

function toggleSystemInfo() {
    const content = document.getElementById('systemInfo');
    const icon = document.querySelector('.collapse-section .collapse-icon');
    const status = document.getElementById('systemStatus');

    if (content && icon && status) {
        content.classList.toggle('show');
        if (content.classList.contains('show')) {
            icon.textContent = '▼';
            status.textContent = 'Открыто';
        } else {
            icon.textContent = '▶';
            status.textContent = 'Скрыто';
        }
    }
}

function refreshCameras() {
    if (window.app && window.app.api) {
        window.app.api.refreshCameras();
    }
}

function startStream() {
    if (window.app && window.app.api) {
        window.app.api.startStream();
    }
}

function stopStream() {
    if (window.app && window.app.api) {
        window.app.api.stopStream();
    }
}

function checkStatus() {
    if (window.app && window.app.api) {
        window.app.api.checkStatus();
    }
}

function checkPortAccess() {
    if (window.app && window.app.api) {
        window.app.api.checkPortAccess();
    }
}

function configureFirewall() {
    if (window.app && window.app.api) {
        window.app.api.configureFirewall();
    }
}

function sendToAndroid() {
    const ipInput = document.getElementById('androidIp');
    if (!ipInput) return;

    const androidIp = ipInput.value.trim();
    if (!androidIp) {
        alert('Пожалуйста, введите IP адрес Android устройства');
        return;
    }

    if (window.app && window.app.api) {
        window.app.api.sendToAndroid(androidIp);
    }
}

function copyLocalUrl() {
    if (window.app && window.app.api) {
        window.app.api.copyLocalUrl();
    }
}

function copyExternalUrl() {
    if (window.app && window.app.api) {
        window.app.api.copyExternalUrl();
    }
}

async function sendToAndroid() {
    const ipInput = document.getElementById('androidIp');
    if (!ipInput) {
        console.error('❌ Поле ввода Android IP не найдено');
        return;
    }

    const androidIp = ipInput.value.trim();
    if (!androidIp) {
        alert('Пожалуйста, введите IP адрес Android устройства');
        return;
    }

    console.log('🚀 Отправка запроса на Android:', androidIp);

    // Показываем сообщение о начале процесса
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
        resultDiv.innerHTML = '<div class="alert alert-success">🚀 Отправка данных на Android...</div>';
    }

    // Показываем статус отправки
    const androidStatus = document.getElementById('androidStatus');
    if (androidStatus) {
        androidStatus.innerHTML = '<span class="status-sending">🔄 Отправка запроса...</span>';
    }

    // Логируем в терминал
    if (window.app && window.app.terminal) {
        await window.app.terminal.typeMessage(`Начало отправки на Android ${androidIp}...`, 50);
    }

    try {
        // Получаем IP адреса через API
        const networkResponse = await fetch('/api/network');
        const networkData = await networkResponse.json();

        const localUrl = `rtsp://${networkData.local_ip}:8554/live/stream`;
        const externalUrl = `rtsp://${networkData.external_ip}:8554/live/stream`;

        const payload = {
            local_url: localUrl,
            external_url: externalUrl,
            timestamp: new Date().toISOString(),
            source: "rtsp_stream_app"
        };

        // Логируем что отправляем
        if (window.app && window.app.terminal) {
            await window.app.terminal.typeMessage(`Отправка на ${androidIp}:8080/stream`, 50);
            await window.app.terminal.typeMessage(`Локальный URL: ${localUrl}`, 50);
            await window.app.terminal.typeMessage(`Внешний URL: ${externalUrl}`, 50);
        }

        // Отправляем запрос
        const response = await fetch(`http://${androidIp}:8080/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        const responseText = await response.text();

        // Обновляем статус
        if (androidStatus) {
            androidStatus.innerHTML = '<span class="status-success">✅ Запрос отправлен</span>';
        }

        // Показываем ответ
        const responseElement = document.getElementById('androidResponse');
        const responseContent = document.getElementById('androidResponseContent');
        if (responseElement && responseContent) {
            responseContent.textContent = responseText;
            responseElement.style.display = 'block';
        }

        // Логируем успех
        if (window.app && window.app.terminal) {
            await window.app.terminal.typeMessage(`✅ Android ответил: ${responseText}`, 50);
        }

    } catch (error) {
        console.error('❌ Ошибка отправки на Android:', error);

        // Показываем ошибку
        if (androidStatus) {
            androidStatus.innerHTML = '<span class="status-error">❌ Ошибка отправки</span>';
        }

        if (resultDiv) {
            resultDiv.innerHTML = '<div class="alert alert-error">❌ Ошибка отправки на Android</div>';
        }

        // Логируем ошибку
        if (window.app && window.app.terminal) {
            await window.app.terminal.typeMessage(`❌ Ошибка: ${error.message}`, 50);
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.app = new RTSPStreamApp();
});