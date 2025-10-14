@echo off
chcp 65001
title Отладка RTSP Stream

echo.
echo 🔍 ОТЛАДКА RTSP STREAM
echo.

echo 1. Проверка Python...
python --version
if errorlevel 1 echo ❌ Python не найден

echo.
echo 2. Проверка модулей...
python -c "import flask; print('✅ Flask')"
python -c "import requests; print('✅ Requests')"

echo.
echo 3. Проверка файлов...
if exist main.py (echo ✅ main.py) else (echo ❌ main.py)
if exist ffmpeg.exe (echo ✅ ffmpeg.exe) else (echo ❌ ffmpeg.exe)
if exist mediamtx.exe (echo ✅ mediamtx.exe) else (echo ❌ mediamtx.exe)

echo.
echo 4. Запуск приложения...
python main.py

echo.
echo Приложение завершило работу
pause