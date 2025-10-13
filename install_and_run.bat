@echo off
chcp 65001
title RTSP Stream - Установка

echo УСТАНОВКА НАЧАТА > log.txt
echo Время: %DATE% %TIME% >> log.txt
echo. >> log.txt

echo ШАГ 1: Проверка Python >> log.txt
python --version >> log.txt 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден >> log.txt
    echo ❌ Python не найден!
    echo Проверьте что Python установлен и добавлен в PATH
    pause
    exit /b 1
)
echo ✅ Python найден >> log.txt

echo. >> log.txt
echo ШАГ 2: Установка Flask >> log.txt
echo 📦 Устанавливаю Flask... >> log.txt
pip install --force-reinstall flask >> log.txt 2>&1
echo ✅ Flask установлен >> log.txt

echo. >> log.txt
echo ШАГ 3: Установка requests >> log.txt
echo 📦 Устанавливаю requests... >> log.txt
pip install --force-reinstall requests >> log.txt 2>&1
echo ✅ requests установлен >> log.txt

echo. >> log.txt
echo ШАГ 4: Проверка установки Flask >> log.txt
echo 🔧 Проверяю что Flask доступен... >> log.txt
python -c "import flask; print('SUCCESS: Flask импортирован')" >> log.txt 2>&1
if errorlevel 1 (
    echo ❌ КРИТИЧЕСКАЯ ОШИБКА: Flask не может быть импортирован! >> log.txt
    echo ❌ КРИТИЧЕСКАЯ ОШИБКА: Flask не может быть импортирован!
    echo.
    echo Возможные причины:
    echo 1. Несколько версий Python конфликтуют
    echo 2. Проблемы с путями установки
    echo 3. Виртуальное окружение активно
    echo.
    echo Решения:
    echo - Запустите: python -m pip install flask
    echo - Или используйте: py -3 -m pip install flask
    echo - Или запустите fix_flask.bat
    pause
    exit /b 1
)
echo ✅ Flask успешно импортирован >> log.txt

echo. >> log.txt
echo ШАГ 5: Распаковка FFmpeg из 7z архива >> log.txt
if exist ffmpeg.exe (
    echo ✅ ffmpeg.exe уже есть >> log.txt
) else (
    echo 🔍 Ищу архив FFmpeg... >> log.txt
    if exist ffmpeg.7z (
        echo 📦 Нашел ffmpeg.7z >> log.txt
        echo 💡 РАСПАКУЙТЕ ffmpeg.7z ВРУЧНУЮ через WinRAR/7-Zip >> log.txt
        echo 💡 И скопируйте ffmpeg.exe в эту папку >> log.txt
        echo.
        echo ❗ ВАЖНО: Распакуйте ffmpeg.7z вручную!
        echo Путь к ffmpeg.exe в архиве:
        echo ffmpeg.7z\ffmpeg-8.0-full_build\bin\ffmpeg.exe
        echo.
        pause
    ) else (
        echo ⚠️ Архив ffmpeg.7z не найден >> log.txt
    )
)

echo. >> log.txt
echo ШАГ 6: Распаковка MediaMTX >> log.txt
if exist mediamtx.exe (
    echo ✅ mediamtx.exe уже есть >> log.txt
) else (
    echo 🔍 Ищу архив MediaMTX... >> log.txt
    if exist mediamtx.zip (
        echo 📦 Нашел mediamtx.zip, распаковываю... >> log.txt
        powershell -Command "Expand-Archive -Path 'mediamtx.zip' -DestinationPath 'mediamtx_temp' -Force" >> log.txt 2>&1

        echo 🔍 Ищу mediamtx.exe... >> log.txt
        if exist mediamtx_temp\mediamtx.exe (
            copy mediamtx_temp\mediamtx.exe . >> log.txt 2>&1
            echo ✅ mediamtx.exe скопирован >> log.txt
        )

        :: Копируем mediamtx.yml если есть
        if exist mediamtx_temp\mediamtx.yml (
            copy mediamtx_temp\mediamtx.yml . >> log.txt 2>&1
            echo ✅ mediamtx.yml скопирован >> log.txt
        )

        rmdir /s /q mediamtx_temp >> log.txt 2>&1
    ) else (
        echo ⚠️ Архив mediamtx.zip не найден >> log.txt
    )
)

echo. >> log.txt
echo ШАГ 7: Проверка файлов >> log.txt
if exist main.py (
    echo ✅ main.py найден >> log.txt
) else (
    echo ОШИБКА: main.py не найден >> log.txt
    echo ❌ main.py не найден
    pause
    exit /b 1
)

echo Проверка инструментов: >> log.txt
if exist ffmpeg.exe (
    echo ✅ ffmpeg.exe найден >> log.txt
) else (
    echo ⚠️ ffmpeg.exe не найден >> log.txt
)

if exist mediamtx.exe (
    echo ✅ mediamtx.exe найден >> log.txt
) else (
    echo ⚠️ mediamtx.exe не найден >> log.txt
)

echo. >> log.txt
echo УСТАНОВКА ЗАВЕРШЕНА >> log.txt

echo.
echo ========================================
echo   Установка завершена!
echo   Проверка файлов:
echo.

if exist ffmpeg.exe (
    echo ✅ ffmpeg.exe - готов
) else (
    echo ❌ ffmpeg.exe - отсутствует
)

if exist mediamtx.exe (
    echo ✅ mediamtx.exe - готов
) else (
    echo ❌ mediamtx.exe - отсутствует
)

echo.
echo 🔧 ФИНАЛЬНАЯ ПРОВЕРКА FLASK...
python -c "import flask; print('✅ Flask РАБОТАЕТ!')"
if errorlevel 1 (
    echo.
    echo ❌ КРИТИЧЕСКАЯ ОШИБКА: Flask не работает!
    echo.
    echo ЗАПУСТИТЕ КОМАНДУ ВРУЧНУЮ:
    echo python -m pip install flask
    echo.
    pause
    exit /b 1
)

echo.
echo 🚀 Запускаю приложение...
echo.

python main.py

echo.
echo Приложение завершило работу
pause