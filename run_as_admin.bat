@echo off
chcp 65001
title RTSP Stream - Запуск с правами администратора

echo ========================================
echo    RTSP Stream - Запуск с правами админа
echo ========================================
echo.

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден
    echo 💡 Установите Python или запустите install_and_run.bat
    pause
    exit /b 1
)

echo ✅ Python найден

:: Проверяем зависимости
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo 📦 Устанавливаем зависимости...
    pip install flask requests
)

:: Запускаем с правами админа
echo.
echo 🔒 Запуск с правами администратора...
echo 💡 Это нужно для автоматической настройки брандмауэра
echo.

powershell -Command "Start-Process python -ArgumentList 'main.py' -Verb RunAs"

echo.
echo ✅ Приложение запущено с правами администратора
echo 💡 Веб-интерфейс: http://localhost:5000
echo.
pause