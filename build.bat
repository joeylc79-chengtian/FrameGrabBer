@echo off
chcp 65001 >nul
title 视频逐帧抽图工具 v0.8 - 打包

echo ============================================
echo   视频逐帧抽图工具 v0.8 - PyInstaller 打包
echo ============================================
echo.

cd /d "%~dp0"

set PYTHON=python
where %PYTHON% >nul 2>nul
if errorlevel 1 (
    echo 未找到 Python，请先安装 Python 或把 Python 加入系统 PATH
    pause
    exit /b 1
)

echo [1/4] 检查并安装依赖...
"%PYTHON%" -m pip install pyinstaller imageio-ffmpeg tkinterdnd2 -i https://pypi.tuna.tsinghua.edu.cn/simple -q
if errorlevel 1 (
    echo 依赖安装失败
    pause
    exit /b 1
)
echo       依赖安装完成

echo [2/4] 获取 FFmpeg 二进制路径...
for /f "delims=" %%i in ('"%PYTHON%" -c "import imageio_ffmpeg; import os; print(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()))"') do set FFMPEG_BIN_DIR=%%i
echo       FFmpeg 目录: %FFMPEG_BIN_DIR%

echo [3/4] 开始打包 exe，可能需要几分钟...
"%PYTHON%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "视频逐帧抽图工具v0.8" ^
    --icon=app.ico ^
    --add-data "app.ico;." ^
    --collect-binaries imageio_ffmpeg ^
    --collect-binaries tkinterdnd2 ^
    --hidden-import imageio_ffmpeg ^
    --hidden-import tkinterdnd2 ^
    --clean ^
    main.py

if errorlevel 1 (
    echo.
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo [4/4] 打包完成
echo ============================================
echo.
echo exe 位置: %~dp0dist\视频逐帧抽图工具v0.8.exe
echo.
echo 说明:
echo   - FFmpeg 已内置在 exe 中，无需安装外部 FFmpeg
echo   - 支持拖拽视频文件到窗口
echo   - 完全离线可用
echo.
pause
