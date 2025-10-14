@echo off
chcp 65001
title RTSP Stream - Установка и Запуск

echo.
echo ========================================
echo   🚀 RTSP STREAM APPLICATION
echo ========================================
echo.

echo 📝 Начинаю установку...
echo.

echo 🔍 Проверка Python...
python --version
if errorlevel 1 (
    echo.
    echo ❌ Python не найден!
    echo.
    echo 💡 Решение:
    echo 1. Скачайте Python с python.org
    echo 2. Установите, отметив "Add Python to PATH"
    echo 3. Запустите этот файл снова
    echo.
    pause
    exit /b 1
)

echo.
echo 📦 Проверка зависимостей...
python -c "import flask" 2>nul
if errorlevel 1 (
    echo ❌ Flask не установлен, устанавливаю...
    pip install flask requests waitress
    echo ✅ Зависимости установлены
) else (
    echo ✅ Flask установлен
)

python -c "import requests" 2>nul
if errorlevel 1 (
    echo ❌ Requests не установлен, устанавливаю...
    pip install requests
)

echo.
echo 🔧 Проверка файлов...
if exist main.py (echo ✅ main.py) else (echo ❌ main.py - ОШИБКА! && pause && exit /b 1)
if exist ffmpeg.exe (echo ✅ ffmpeg.exe) else (echo ⚠️ ffmpeg.exe отсутствует)
if exist mediamtx.exe (echo ✅ mediamtx.exe) else (echo ⚠️ mediamtx.exe отсутствует)
if exist mediamtx.yml (echo ✅ mediamtx.yml) else (echo ⚠️ mediamtx.yml отсутствует)

echo.
echo 🛡️ Проверка прав доступа...
net session >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Запущено без прав администратора
    echo 💡 Для настройки брандмауэра запустите от имени администратора
) else (
    echo ✅ Запущено с правами администратора
    echo 💡 Настраиваю брандмауэр...
    netsh advfirewall firewall add rule name="RTSP Port 8554" dir=in action=allow protocol=TCP localport=8554 remoteip=any
    netsh advfirewall firewall add rule name="RTSP Port 8000" dir=in action=allow protocol=TCP localport=8000 remoteip=any
    netsh advfirewall firewall add rule name="RTSP Port 8001" dir=in action=allow protocol=TCP localport=8001 remoteip=any
    echo ✅ Брандмауэр настроен
)

echo.
echo ========================================
echo   🚀 ЗАПУСК ПРИЛОЖЕНИЯ
echo ========================================
echo.

echo 📍 Информация для доступа:
python -c "
try:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    local_ip = s.getsockname()[0]
    s.close()
    print(f'📍 Локальный IP: {local_ip}')
    print(f'📹 RTSP поток: rtsp://{local_ip}:8554/live/stream')
    print(f'🌐 Веб-интерфейс: http://{local_ip}:5000')
except:
    print('📍 Локальный RTSP: rtsp://localhost:8554/live/stream')
    print('🌐 Веб-интерфейс: http://localhost:5000')
"

echo.
echo ⏹️  Для остановки нажмите Ctrl+C
echo 📄 Логи будут в rtsp_stream.log
echo.

echo 🚀 ЗАПУСКАЮ ОСНОВНОЕ ПРИЛОЖЕНИЕ...
echo ========================================
python main.py

echo.
echo ========================================
echo   📋 ПРИЛОЖЕНИЕ ЗАВЕРШИЛО РАБОТУ
echo ========================================
echo.
pause