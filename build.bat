@echo off
chcp 65001 >nul
echo ========================================
echo CxKitty 打包工具
echo ========================================
echo.

echo 正在检查Python环境...
python --version
if errorlevel 1 (
    echo 错误：未找到Python环境，请先安装Python 3.11
    pause
    exit /b 1
)

echo.
echo 正在安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误：依赖包安装失败
    pause
    exit /b 1
)

echo.
echo 开始打包...
python build_exe.py
if errorlevel 1 (
    echo 错误：打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo 可执行文件位置: dist\CxKitty.exe
echo ========================================
pause 