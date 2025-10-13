@echo off
chcp 65001
title RTSP Stream - Быстрый запуск

echo ========================================
echo    RTSP Stream - Запуск
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo 💡 Запустите install_and_run.bat сначала
    pause
    exit /b 1
)

echo ✅ Python обнаружен
echo 🚀 Запуск приложения...
echo 🌐 Открой: http://localhost:5000
echo.

python main.py

echo.
pause