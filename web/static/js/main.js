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

function copyExternalUrl() {
    if (window.app && window.app.api) {
        window.app.api.copyExternalUrl();
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.app = new RTSPStreamApp();
});