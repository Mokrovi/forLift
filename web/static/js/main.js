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
let selectedAndroidIp = null;

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
        listElement.innerHTML = '<div class="ip-item" style="color:#666;justify-content:center">Список пуст</div>';
        return;
    }

    listElement.innerHTML = ips.map(ip => `
        <div class="ip-item" style="background:${selectedAndroidIp === ip ? 'rgba(0,255,255,0.15)' : 'transparent'};border-left:${selectedAndroidIp === ip ? '3px solid #0ff' : '3px solid transparent'}">
            <span style="flex:1;cursor:pointer" onclick="selectAndroidIp('${ip}')">${ip}${selectedAndroidIp === ip ? ' ✓' : ''}</span>
            <button class="ip-remove" onclick="removeAndroidIp('${ip}')">✕</button>
        </div>
    `).join('');
}

function selectAndroidIp(ip) {
    selectedAndroidIp = ip;
    renderAndroidIpList((window.app.api.cachedIps || []));
    console.log('Выбрано устройство:', ip);
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
            window.app.api.cachedIps = result.android_ips;
            renderAndroidIpList(result.android_ips);
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
            if (selectedAndroidIp === ip) {
                selectedAndroidIp = null;
            }
            window.app.api.cachedIps = result.android_ips;
            renderAndroidIpList(result.android_ips);
        }
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function testAndroidConnection() {
    const ip = selectedAndroidIp || document.getElementById('androidIpInput').value.trim();

    if (!ip) {
        alert('❌ Введите IP адрес или выберите устройство из списка');
        return;
    }

    try {
        const result = await window.app.api.testAndroidConnection(ip);
        if (result.success && !selectedAndroidIp) {
            selectAndroidIp(ip);
        }
        alert(result.message);
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function sendStreamSignal() {
    if (!selectedAndroidIp) {
        alert('❌ Сначала выберите устройство из списка');
        return;
    }

    const localIp = document.getElementById('localIp');
    const localUrl = localIp ? localIp.textContent : '';
    
    if (!localUrl) {
        alert('❌ Не получен локальный IP');
        return;
    }

    // Добавляем порт 8080 если не указан
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }

    const streamUrl = `rtsp://${localUrl}:8554/live/stream`;
    
    try {
        // Отправляем JSON с правильным Content-Type
        const response = await fetch(`http://${targetIp}/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                local_url: streamUrl,
                external_url: null
            })
        });
        
        const text = await response.text();
        console.log('Response:', response.status, text);
        
        if (response.ok || response.status === 200) {
            alert(`✅ Сигнал отправлен на ${targetIp}\nСтрим должен открыться на устройстве`);
        } else {
            alert(`⚠️ Ответ устройства: ${response.status}\n${text}`);
        }
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function disconnectAndroid() {
    if (!selectedAndroidIp) {
        alert('❌ Нет выбранного устройства');
        return;
    }
    
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }
    
    try {
        // Отправляем сигнал закрыть стрим
        const response = await fetch(`http://${targetIp}/close-stream`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert(`✅ Устройство ${targetIp} отключено\nТрансляция остановлена`);
        } else {
            alert(`⚠️ Устройство не ответило: ${response.status}`);
        }
    } catch (error) {
        alert('❌ Ошибка отключения: ' + error.message);
    }
    
    // Очищаем выбор
    selectedAndroidIp = null;
    
    // Обновляем список
    if (window.app && window.app.api) {
        window.app.api.cachedIps = window.app.api.cachedIps.filter(i => i !== targetIp.replace(':8080', ''));
    }
    renderAndroidIpList(window.app.api.cachedIps || []);
}

async function testStreamConnection() {
    if (!selectedAndroidIp) {
        alert('❌ Сначала выберите устройство из списка');
        return;
    }

    // Добавляем порт 8080 если не указан
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }

    try {
        const response = await fetch(`http://${targetIp}/`, {
            method: 'GET',
            mode: 'no-cors'
        });
        
        alert(`✅ Устройство ${targetIp} доступно\n\nЕсли стрим не открывается - проверь что Android приложение запущено`);
    } catch (error) {
        alert('❌ Устройство недоступно: ' + error.message);
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

// === Управление мультиком на Android ===

// Аккордеон
function toggleAccordion(id) {
    const item = document.getElementById('acc-' + id);
    if (item) {
        item.classList.toggle('open');
    }
}

async function loadAndroidVideos() {
    if (!selectedAndroidIp) {
        alert('❌ Сначала выберите устройство из списка');
        return;
    }
    
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }
    
    const videoList = document.getElementById('videoList');
    if (!videoList) return;

    try {
        videoList.innerHTML = '<div class="video-item">Загрузка...</div>';
        const result = await window.app.api.getAndroidVideos(targetIp);
        
        if (result.success && result.videos && result.videos.length > 0) {
            videoList.innerHTML = '';
            result.videos.forEach(video => {
                const item = document.createElement('div');
                item.className = 'video-item';
                item.textContent = video.name;
                item.onclick = () => selectVideo(item, video.name);
                videoList.appendChild(item);
            });
        } else {
            videoList.innerHTML = '<div class="video-item">❌ ' + (result.message || 'Список пуст') + '</div>';
        }
    } catch (error) {
        videoList.innerHTML = '<div class="video-item">❌ Ошибка загрузки</div>';
        console.error('Ошибка загрузки видео:', error);
    }
}

let selectedVideoName = null;

function selectVideo(element, videoName) {
    // Снимаем выделение со всех
    document.querySelectorAll('.video-item').forEach(item => {
        item.classList.remove('selected');
    });
    // Выделяем текущий
    element.classList.add('selected');
    selectedVideoName = videoName;
}

async function playSelectedVideo() {
    if (!selectedVideoName) {
        alert('❌ Выберите видео из списка');
        return;
    }
    await playVideo();
}

async function playVideo() {
    if (!selectedAndroidIp) {
        alert('❌ Сначала выберите устройство');
        return;
    }
    if (!selectedVideoName) {
        alert('❌ Выберите видео из списка');
        return;
    }

    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }

    try {
        const result = await window.app.api.playAnimation(targetIp, selectedVideoName);
        console.log(result.message);
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function stopVideo() {
    if (!selectedAndroidIp) {
        alert('❌ Сначала выберите устройство');
        return;
    }
    
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }
    
    try {
        const result = await window.app.api.stopAnimation(targetIp);
        console.log(result.message);
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function updateCartoonVolume(value) {
    if (!selectedAndroidIp) return;
    
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }

    const display = document.getElementById('cartoonVolumeValue');
    if (display) display.textContent = `${value}%`;

    try {
        await window.app.api.setCartoonVolume(targetIp, value / 100);
    } catch (error) {
        console.error('Ошибка установки громкости:', error);
    }
}

async function muteCartoon(mute) {
    if (!selectedAndroidIp) return;
    
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }

    try {
        const volume = mute ? 0 : 100;
        await window.app.api.setCartoonVolume(targetIp, volume / 100);
        const display = document.getElementById('cartoonVolumeValue');
        const slider = document.getElementById('cartoonVolume');
        
        if (display) display.textContent = `${volume}%`;
        if (slider) slider.value = volume;
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

async function toggleMicrophone(mute) {
    const micStatus = document.getElementById('micStatusValue');
    
    if (micStatus) {
        micStatus.textContent = mute ? 'Выкл' : 'Вкл';
    }
    
    // Если стрим запущен - перезапускаем его с новыми настройками
    const streamForm = document.getElementById('streamForm');
    if (streamForm) {
        // Просто обновляем UI - пользователь должен сам перезапустить стрим
        console.log('Микрофон:', mute ? 'выключен' : 'включен');
        console.log('⚠️ Перезапустите стрим чтобы изменения вступили в силу');
    }
}

async function setDisplayMode(mode) {
    if (!selectedAndroidIp) {
        alert('❌ Сначала выберите устройство');
        return;
    }

    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }

    try {
        const result = await window.app.api.setDisplayMode(targetIp, mode);

        document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById('mode-' + mode);
        if (activeBtn) activeBtn.classList.add('active');

        console.log(result.message);
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}

async function toggleWebcamVisibility(visible) {
    if (!selectedAndroidIp) {
        alert('❌ Сначала выберите устройство');
        return;
    }
    
    let targetIp = selectedAndroidIp;
    if (!targetIp.includes(':')) {
        targetIp = targetIp + ':8080';
    }

    try {
        const result = await window.app.api.setWebcamVisibility(targetIp, visible);
        console.log(result.message);
    } catch (error) {
        alert('❌ Ошибка: ' + error.message);
    }
}