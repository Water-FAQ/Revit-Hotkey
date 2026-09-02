@echo off
setlocal EnableExtensions
chcp 65001 >nul
pushd "%~dp0"

set "BUILD_ROOT=%TEMP%\RevitHotkeyBuild"
set "VENV_DIR=%BUILD_ROOT%\venv"
set "APP_NAME=Revit Hotkey"
set "PYTHON_CMD=py -3.10"

echo Проверка Python 3.10...
py -3.10 -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 10))" >nul 2>&1
if not errorlevel 1 goto python_found

set "PYTHON_CMD=python"
python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 10))" >nul 2>&1
if not errorlevel 1 goto python_found

echo.
echo ОШИБКА: Python 3.10 не найден.
echo Установите Python 3.10 и повторите сборку.
goto build_error

:python_found
if not exist "%BUILD_ROOT%" mkdir "%BUILD_ROOT%"
if errorlevel 1 goto build_error
if exist "%VENV_DIR%\Scripts\python.exe" goto install_dependencies

echo Создание виртуального окружения...
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 goto build_error

:install_dependencies
echo Установка зависимостей...
"%VENV_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto build_error
"%VENV_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto build_error

echo Проверка проекта...
"%VENV_DIR%\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto build_error

echo Сборка приложения...
"%VENV_DIR%\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "%APP_NAME%" ^
    --icon "revit_hotkey\resources\icon.ico" ^
    --version-file "version_info.txt" ^
    --add-data "revit_hotkey\resources\icon.png;revit_hotkey\resources" ^
    main.py
if errorlevel 1 goto build_error

echo.
echo Сборка завершена успешно.
echo Готовый файл: %CD%\dist\%APP_NAME%.exe
explorer "%CD%\dist"
echo.
pause
popd
exit /b 0

:build_error
echo.
echo Сборка не завершена. Причина указана выше.
echo.
pause
popd
exit /b 1

