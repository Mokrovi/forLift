import PyInstaller.__main__
import os
import shutil

# Очищаем предыдущую сборку
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--name=forLift',
    '--icon=icon.ico' if os.path.exists('icon.ico') else '--console',
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--add-data=config;config',
    '--add-data=core;core',
    '--add-data=utils;utils',
    '--add-data=web;web',
    '--add-data=ffmpeg.exe;.',
    '--add-data=mediamtx.exe;.',
    '--add-data=mediamtx.yml;.',
    '--hidden-import=flask',
    '--hidden-import=requests',
    '--hidden-import=waitress',
    '--noconfirm',
])
