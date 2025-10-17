// Управление WireGuard VPN
class VPNManager {
    constructor() {
        this.baseURL = '';
    }

    async checkVPNStatus() {
        try {
            const response = await fetch('/api/vpn/status');
            const status = await response.json();

            const vpnStatusElement = document.getElementById('vpnStatus');
            if (vpnStatusElement) {
                if (status.vpn_active) {
                    vpnStatusElement.innerHTML = '<span class="status-online">✅ Активен (' + status.mode + ')</span>';
                } else {
                    vpnStatusElement.innerHTML = '<span class="status-offline">❌ Неактивен</span>';
                }
            }

            return status;
        } catch (error) {
            console.error('❌ Ошибка проверки статуса VPN:', error);
            const vpnStatusElement = document.getElementById('vpnStatus');
            if (vpnStatusElement) {
                vpnStatusElement.innerHTML = '<span class="status-offline">❌ Ошибка</span>';
            }
            return { vpn_active: false };
        }
    }

    async startVPNServer() {
        try {
            showMessage('🛡️ Запуск VPN сервера...', false);

            const response = await fetch('/api/vpn/start-server', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const result = await response.json();

            if (result.success) {
                showMessage('✅ ' + result.message, false);

                // Показываем информацию о сервере
                const vpnInfo = document.getElementById('vpnInfo');
                if (vpnInfo) {
                    vpnInfo.innerHTML = `
                        <div class="vpn-server-info">
                            <h4>🔐 Информация сервера:</h4>
                            <p><strong>Публичный ключ:</strong> <code>${result.server_public_key}</code></p>
                            <p><strong>VPN сеть:</strong> ${result.vpn_subnet}</p>
                            <p><strong>IP сервера:</strong> ${result.server_ip}</p>
                            <p><strong>Порт:</strong> 51820</p>
                            <button onclick="addVPNClientPrompt('${result.server_public_key}')" class="btn btn-primary btn-sm">
                                ➕ Добавить клиента
                            </button>
                        </div>
                    `;
                }

                // Обновляем статус
                setTimeout(() => this.checkVPNStatus(), 2000);

            } else {
                showMessage('❌ ' + result.message, true);
            }

        } catch (error) {
            console.error('❌ Ошибка запуска VPN сервера:', error);
            showMessage('❌ Ошибка запуска VPN сервера: ' + error.message, true);
        }
    }

    async startVPNClient() {
        const serverPublicKey = document.getElementById('serverPublicKey').value;
        const serverEndpoint = document.getElementById('serverEndpoint').value;
        const clientIP = document.getElementById('clientIP').value || '10.0.0.2';

        if (!serverPublicKey || !serverEndpoint) {
            showMessage('❌ Заполните все поля для подключения', true);
            return;
        }

        try {
            showMessage('🔗 Подключение к VPN серверу...', false);

            const response = await fetch('/api/vpn/start-client', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    server_public_key: serverPublicKey,
                    server_endpoint: serverEndpoint,
                    client_ip: clientIP
                })
            });

            const result = await response.json();

            if (result.success) {
                showMessage('✅ ' + result.message, false);

                // Показываем информацию о клиенте
                const vpnInfo = document.getElementById('vpnInfo');
                if (vpnInfo) {
                    vpnInfo.innerHTML = `
                        <div class="vpn-client-info">
                            <h4>🔗 Подключение установлено:</h4>
                            <p><strong>Ваш VPN IP:</strong> ${result.client_ip}</p>
                            <p><strong>Публичный ключ клиента:</strong> <code>${result.client_public_key}</code></p>
                            <p><strong>RTSP через VPN:</strong> rtsp://10.0.0.1:8554/live/stream</p>
                        </div>
                    `;
                }

                // Обновляем статус
                setTimeout(() => this.checkVPNStatus(), 2000);

            } else {
                showMessage('❌ ' + result.message, true);
            }

        } catch (error) {
            console.error('❌ Ошибка подключения VPN клиента:', error);
            showMessage('❌ Ошибка подключения: ' + error.message, true);
        }
    }

    async stopVPN() {
        try {
            showMessage('⏹️ Остановка VPN...', false);

            const response = await fetch('/api/vpn/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const result = await response.json();

            if (result.success) {
                showMessage('✅ ' + result.message, false);

                // Очищаем информацию
                const vpnInfo = document.getElementById('vpnInfo');
                if (vpnInfo) {
                    vpnInfo.innerHTML = '';
                }

                // Обновляем статус
                setTimeout(() => this.checkVPNStatus(), 1000);

            } else {
                showMessage('❌ ' + result.message, true);
            }

        } catch (error) {
            console.error('❌ Ошибка остановки VPN:', error);
            showMessage('❌ Ошибка остановки VPN: ' + error.message, true);
        }
    }

    async generateVPNKeys() {
        try {
            showMessage('🔑 Генерация ключей...', false);

            const response = await fetch('/api/vpn/generate-keys', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const result = await response.json();

            if (result.success) {
                // Показываем модальное окно с ключами
                showKeysModal(result.private_key, result.public_key);
                showMessage('✅ Ключи сгенерированы', false);
            } else {
                showMessage('❌ ' + result.message, true);
            }

        } catch (error) {
            console.error('❌ Ошибка генерации ключей:', error);
            showMessage('❌ Ошибка генерации ключей: ' + error.message, true);
        }
    }
}

// Глобальные функции для HTML
function showServerSetup() {
    document.getElementById('serverSetup').style.display = 'block';
    document.getElementById('clientSetup').style.display = 'none';
}

function showClientSetup() {
    document.getElementById('serverSetup').style.display = 'none';
    document.getElementById('clientSetup').style.display = 'block';
}

function startVPNServer() {
    window.vpnManager.startVPNServer();
}

function startVPNClient() {
    window.vpnManager.startVPNClient();
}

function stopVPN() {
    window.vpnManager.stopVPN();
}

function generateVPNKeys() {
    window.vpnManager.generateVPNKeys();
}

function showKeysModal(privateKey, publicKey) {
    document.getElementById('privateKey').value = privateKey;
    document.getElementById('publicKey').value = publicKey;
    document.getElementById('keysModal').style.display = 'block';
}

function closeKeysModal() {
    document.getElementById('keysModal').style.display = 'none';
}

function copyPrivateKey() {
    const privateKey = document.getElementById('privateKey').value;
    navigator.clipboard.writeText(privateKey).then(() => {
        showMessage('✅ Приватный ключ скопирован', false);
    });
}

function copyPublicKey() {
    const publicKey = document.getElementById('publicKey').value;
    navigator.clipboard.writeText(publicKey).then(() => {
        showMessage('✅ Публичный ключ скопирован', false);
    });
}

function copyVPNUrl() {
    const vpnUrl = 'rtsp://10.0.0.1:8554/live/stream';
    navigator.clipboard.writeText(vpnUrl).then(() => {
        showMessage('✅ VPN URL скопирован', false);
    });
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    window.vpnManager = new VPNManager();

    // Проверяем статус VPN каждые 5 секунд
    setInterval(() => {
        window.vpnManager.checkVPNStatus();
    }, 5000);

    // Первая проверка
    setTimeout(() => {
        window.vpnManager.checkVPNStatus();
    }, 1000);
});