// Управление UI компонентами
class UIManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.injectModalStyles();
    }

    setupEventListeners() {
        // Добавляем обработчики для сворачиваемых секций
        document.addEventListener('click', (e) => {
            if (e.target.closest('.collapse-header')) {
                this.toggleCollapse(e.target.closest('.collapse-header'));
            }
        });

        // Обработчик для модальных окон
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-close') || e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });
    }

    toggleCollapse(headerElement) {
        const content = headerElement.nextElementSibling;
        const icon = headerElement.querySelector('.collapse-icon');
        const status = headerElement.querySelector('.collapse-status');

        if (content && content.classList.contains('collapse-content')) {
            content.classList.toggle('show');

            if (icon) {
                icon.textContent = content.classList.contains('show') ? '▼' : '▶';
            }
            if (status) {
                status.textContent = content.classList.contains('show') ? 'Открыто' : 'Скрыто';
            }
        }
    }

    toggleSystemInfo() {
        const header = document.querySelector('.collapse-section .collapse-header');
        if (header) {
            this.toggleCollapse(header);
        }
    }

    showModal(title, content, options = {}) {
        const modalId = 'modal-' + Date.now();
        const sizeClass = options.size ? `modal-${options.size}` : '';

        const modalHTML = `
            <div class="modal" id="${modalId}">
                <div class="modal-content ${sizeClass}">
                    <div class="modal-header">
                        <h3 class="modal-title">${title}</h3>
                        <span class="modal-close">&times;</span>
                    </div>
                    <div class="modal-body">
                        ${content}
                    </div>
                    ${options.footer ? `
                    <div class="modal-footer">
                        ${options.footer}
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Анимация появления
        setTimeout(() => {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('show');
            }
        }, 10);

        return modalId;
    }

    closeModal(modalElement) {
        const modal = modalElement.classList.contains('modal') ?
            modalElement : modalElement.closest('.modal');

        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.remove();
            }, 300);
        }
    }

    showNotification(message, type = 'info', duration = 3000) {
        const notificationId = 'notification-' + Date.now();

        const notificationHTML = `
            <div class="notification notification-${type}" id="${notificationId}">
                <div class="notification-content">
                    ${message}
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', notificationHTML);

        // Анимация появления
        setTimeout(() => {
            const notification = document.getElementById(notificationId);
            if (notification) {
                notification.classList.add('show');
            }
        }, 10);

        // Автоматическое закрытие
        if (duration > 0) {
            setTimeout(() => {
                this.hideNotification(notificationId);
            }, duration);
        }

        return notificationId;
    }

    hideNotification(notificationId) {
        const notification = document.getElementById(notificationId);
        if (notification) {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }

    showLoading(message = 'Загрузка...') {
        return this.showModal('', `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <div class="loading-text">${message}</div>
            </div>
        `, {
            size: 'sm'
        });
    }

    hideLoading(modalId) {
        this.closeModal(document.getElementById(modalId));
    }

    updateButtonState(buttonElement, state) {
        const states = {
            loading: {
                text: 'Загрузка...',
                disabled: true,
                className: 'btn-loading'
            },
            success: {
                text: 'Успешно!',
                disabled: true,
                className: 'btn-success'
            },
            error: {
                text: 'Ошибка',
                disabled: false,
                className: 'btn-danger'
            },
            normal: {
                text: buttonElement.dataset.originalText || buttonElement.textContent,
                disabled: false,
                className: ''
            }
        };

        const config = states[state] || states.normal;

        // Сохраняем оригинальный текст при первом изменении
        if (!buttonElement.dataset.originalText && state !== 'normal') {
            buttonElement.dataset.originalText = buttonElement.textContent;
        }

        buttonElement.textContent = config.text;
        buttonElement.disabled = config.disabled;

        // Удаляем предыдущие классы состояний
        buttonElement.classList.remove('btn-loading', 'btn-success', 'btn-danger');
        if (config.className) {
            buttonElement.classList.add(config.className);
        }
    }

    injectModalStyles() {
        if (document.getElementById('ui-styles')) return;

        const styles = `
            .modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }

            .modal.show {
                opacity: 1;
                visibility: visible;
            }

            .modal-content {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: var(--radius-lg);
                padding: 0;
                max-width: 90vw;
                width: 500px;
                max-height: 80vh;
                overflow: hidden;
                transform: scale(0.9);
                transition: transform 0.3s ease;
                box-shadow: var(--shadow-lg);
            }

            .modal.show .modal-content {
                transform: scale(1);
            }

            .modal-sm {
                width: 400px;
            }

            .modal-lg {
                width: 600px;
            }

            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid var(--border);
                background: var(--surface-dark);
            }

            .modal-title {
                font-weight: 600;
                color: var(--text);
                margin: 0;
                font-size: 18px;
            }

            .modal-close {
                cursor: pointer;
                font-size: 24px;
                line-height: 1;
                color: var(--text-secondary);
                transition: color 0.3s ease;
                background: none;
                border: none;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .modal-close:hover {
                color: var(--danger);
            }

            .modal-body {
                padding: 20px;
                max-height: 60vh;
                overflow-y: auto;
            }

            .modal-footer {
                padding: 16px 20px;
                border-top: 1px solid var(--border);
                background: var(--surface-dark);
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            }

            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 16px 20px;
                border-radius: var(--radius);
                color: white;
                z-index: 10001;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                max-width: 400px;
                box-shadow: var(--shadow-lg);
            }

            .notification.show {
                transform: translateX(0);
            }

            .notification-info {
                background: var(--info);
                border-left: 4px solid var(--info);
            }
            .notification-success {
                background: var(--success);
                border-left: 4px solid var(--success);
            }
            .notification-error {
                background: var(--danger);
                border-left: 4px solid var(--danger);
            }
            .notification-warning {
                background: var(--warning);
                color: black;
                border-left: 4px solid var(--warning);
            }

            .loading-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 16px;
                padding: 20px;
            }

            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 4px solid var(--border);
                border-top: 4px solid var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            .loading-text {
                color: var(--text);
                font-weight: 500;
            }

            .btn-loading {
                position: relative;
                color: transparent !important;
            }

            .btn-loading::after {
                content: '';
                position: absolute;
                width: 16px;
                height: 16px;
                border: 2px solid transparent;
                border-top: 2px solid currentColor;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                left: 50%;
                top: 50%;
                margin-left: -8px;
                margin-top: -8px;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            @media (max-width: 768px) {
                .modal-content {
                    width: 95vw;
                    max-width: 95vw;
                    margin: 10px;
                }

                .modal-sm,
                .modal-lg {
                    width: 95vw;
                }

                .notification {
                    right: 10px;
                    left: 10px;
                    max-width: none;
                }
            }
        `;

        const styleSheet = document.createElement('style');
        styleSheet.id = 'ui-styles';
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
}

// Создаем глобальный экземпляр
window.uiManager = new UIManager();