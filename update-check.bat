@echo off
REM update-check.bat - Verifica e invoca update.ps1 para mantener la aplicación sincronizada con el Release tag
REM Ajusta OWNER y REPO según corresponda. Diseñado para ejecutarse desde Programador de Tareas.

setlocal enabledelayedexpansion

:: Configuración por defecto - cámbialas si lo necesitas
set OWNER=AR-BPS-TaxTech
set REPO=nfe_alert
set CHANNEL=latest

:: Ruta al script PowerShell (relativa a este .bat)
set SCRIPT=%~dp0update.ps1

:: Target por defecto (usuario actual) - se puede forzar aquí si se desea
set TARGET=%USERPROFILE%\NFE_Alert_UY

:: Opcional: pasar GITHUB_PAT_NFE_UY si está disponible en variables de entorno del sistema
if defined GITHUB_PAT_NFE_UY (
    echo Using GITHUB_PAT_NFE_UY from environment.
) else (
    echo No GITHUB_PAT_NFE_UY in environment
)

:: Preparar logging para capturar toda la salida (stdout + stderr) aunque la consola se cierre
set LOGDIR=%~dp0logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

:: Obtener timestamp fiable desde PowerShell (yyyyMMdd-HHmmss)
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd-HHmmss'"`) do set TIMESTAMP=%%i
set LOGFILE=%LOGDIR%\update-%TIMESTAMP%.log

echo Running update.ps1, logging to %LOGFILE%

:: Ejecutar el PowerShell script y redirigir stdout/stderr al logfile
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -Owner "%OWNER%" -Repo "%REPO%" -ChannelTag "%CHANNEL%" -Target "%TARGET%" -Verbose > "%LOGFILE%" 2>&1
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% EQU 0 (
  echo Update check completed successfully. >> "%LOGFILE%"
) else (
  echo Update script returned error code %EXITCODE%. >> "%LOGFILE%"
)

:: Si se pasa el argumento "pause", mostramos el log en pantalla y esperamos tecla antes de salir
if "%1"=="pause" (
  echo --- Showing log: %LOGFILE% ---
  type "%LOGFILE%"
  echo.
  pause
)

echo Log saved to %LOGFILE%
pause

endlocal
exit /b %EXITCODE%
