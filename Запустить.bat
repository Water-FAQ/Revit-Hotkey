@echo off
setlocal EnableExtensions
chcp 65001 >nul
pushd "%~dp0"

set "VENV_DIR=%TEMP%\RevitHotkeyBuild\venv"

if exist "%VENV_DIR%\Scripts\python.exe" goto run_app

echo Виртуальное окружение не найдено.
echo Сначала запустите файл "Собрать_EXE.bat".
echo.
pause
popd
exit /b 1

:run_app
"%VENV_DIR%\Scripts\python.exe" main.py
set "APP_EXIT_CODE=%ERRORLEVEL%"
if "%APP_EXIT_CODE%"=="0" goto finish

echo.
echo ОШИБКА: программа завершилась с кодом %APP_EXIT_CODE%.
pause

:finish
popd
exit /b %APP_EXIT_CODE%

