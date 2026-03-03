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

function refreshMicrophones() {
    if (window.app && window.app.api) {
        window.app.api.refreshMicrophones();
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

// === Android IP Management ===
async function loadAndroidIps() {
    if (!window.app || !window.app.api) return;
    
    try {
        const result = await window.app.api.getAndroidIps();
        renderAndroidIpList(result.android_ips || []);
    } catch (error) {
        console.error('Ошибка загрузки Android IP:', error);
    }
}

function renderAndroidIpList(ips) {
    const listElement = document.getElementById('androidIpList');
    if (!listElement) return;
    
    if (ips.length === 0) {
        listElement.innerHTML = '<p style="color: #888; font-size: 0.9em">Список пуст</p>';
        return;
    }
    
    listElement.innerHTML = ips.map(ip => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: rgba(255,255,255,0.05); margin-bottom: 4px; border-radius: 4px;">
            <span style="font-family: monospace; color: #0ff">${ip}</span>
            <button onclick="removeAndroidIp('${ip}')" style="background: #dc3545; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer;">✕</button>
        </div>
    `).join('');
}

async function addAndroidIp() {
    const input = document.getElementById('androidIpInput');
    const ip = input.value.trim();
    
    if (!ip) {
        alert('❌ Введите IP адрес');
        return;
    }
    
    try {
        const result = await window.app.api.addAndroidIp(ip);
        if (result.success) {
            input.value = '';
            renderAndroidIpList(result.android_ips);
            alert(result.message);
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function removeAndroidIp(ip) {
    try {
        const result = await window.app.api.removeAndroidIp(ip);
        if (result.success) {
            renderAndroidIpList(result.android_ips);
        }
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function testAndroidConnection() {
    const input = document.getElementById('androidIpInput');
    const ip = input.value.trim();
    
    if (!ip) {
        alert('❌ Введите IP адрес для теста');
        return;
    }
    
    try {
        const result = await window.app.api.testAndroidConnection(ip);
        alert(result.message);
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.app = new RTSPStreamApp();
    // Загружаем список Android IP
    loadAndroidIps();
    // Загружаем список микрофонов
    refreshMicrophones();
});