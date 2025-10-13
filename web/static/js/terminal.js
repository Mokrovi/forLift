// Управление терминалом и анимациями
class TerminalManager {
    constructor() {
        this.terminalContent = null;
        this.logLinesContainer = null;
        this.isTyping = false;
        this.MAX_LINES = 15;
    }

    initialize() {
        this.terminalContent = document.getElementById('terminalContent');
        if (!this.terminalContent) {
            console.error('❌ Terminal content element not found');
            return;
        }

        // Создаем контейнер для строк лога
        this.logLinesContainer = document.createElement('div');
        this.logLinesContainer.className = 'log-lines-container';
        this.terminalContent.appendChild(this.logLinesContainer);

        // Начальные сообщения
        setTimeout(() => this.typeMessage('Инициализация системы...', 60), 500);
        setTimeout(() => this.typeMessage('Проверка компонентов...', 60), 1500);
        setTimeout(() => this.typeMessage('Готов к работе', 60), 2500);
    }

    async typeMessage(message, speed = 90) {
        return new Promise((resolve) => {
            if (!this.logLinesContainer) {
                resolve();
                return;
            }

            if (this.isTyping) {
                setTimeout(() => this.typeMessage(message, speed).then(resolve), 200);
                return;
            }

            this.isTyping = true;

            const line = document.createElement('div');
            line.className = 'log-line typing';
            line.innerHTML = '> ';
            this.logLinesContainer.appendChild(line);

            this.limitLines();
            this.scrollToBottom();

            let i = 0;
            const timer = setInterval(() => {
                if (i < message.length) {
                    line.innerHTML = '> ' + message.substring(0, i + 1);
                    i++;
                    this.scrollToBottom();
                } else {
                    clearInterval(timer);
                    line.classList.remove('typing');
                    this.isTyping = false;
                    resolve();
                }
            }, speed);
        });
    }

    addQuickMessage(message) {
        if (!this.logLinesContainer) return;

        const line = document.createElement('div');
        line.className = 'log-line';
        line.innerHTML = '> ' + message;
        this.logLinesContainer.appendChild(line);

        this.limitLines();
        this.scrollToBottom();
    }

    limitLines() {
        if (!this.logLinesContainer) return;

        const lines = this.logLinesContainer.querySelectorAll('.log-line');
        if (lines.length > this.MAX_LINES) {
            lines[0].remove();
        }
    }

    scrollToBottom() {
        if (this.terminalContent) {
            this.terminalContent.scrollTop = this.terminalContent.scrollHeight;
        }
    }

    async randomSystemMessage() {
        const messages = [
            "Мониторинг системы...",
            "Проверка сетевого соединения...",
            "Анализ производительности...",
            "Все системы в норме",
            "Готов к работе",
            "Ожидание команд...",
            "Память: стабильно",
            "CPU: нормальная нагрузка"
        ];

        const randomMessage = messages[Math.floor(Math.random() * messages.length)];
        await this.typeMessage(randomMessage, 70);
    }

    clear() {
        if (this.logLinesContainer) {
            this.logLinesContainer.innerHTML = '';
        }
    }
}