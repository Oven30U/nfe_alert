@echo off
setlocal enabledelayedexpansion

:: CONFIGURACIÓN
set REPO=AR-BPS-TaxTech/nfe_alert
set VERSION_FILE=VERSION.txt
set ZIP_NAME=release.zip
set TMP_DIR=%TEMP%\update_tmp

:: Crear carpeta temporal
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"
echo Carpeta temporal creada en %TMP_DIR%
pause

:: Obtener última versión desde GitHub API (release más reciente)
echo Consultando ultima version (release) desde GitHub...
curl -s https://api.github.com/repos/%REPO%/releases/latest > "%TMP_DIR%\release.json"
echo Archivo release.json descargado a %TMP_DIR%\release.json
type "%TMP_DIR%\release.json" | more
pause

:: Extraer tag_name desde el JSON (formato "tag_name": "vX.X.X")
set LATEST_VERSION=
for /f "usebackq tokens=2 delims=:\" %%A in (`findstr /i "\"tag_name\"" "%TMP_DIR%\release.json"`) do (
    set LATEST_VERSION=%%A
    rem quitar espacios y comillas
    set LATEST_VERSION=!LATEST_VERSION:~1!
    set LATEST_VERSION=!LATEST_VERSION:~0,-1!
)

:: Si no se obtuvo release, intentar obtener último tag (fallback)
if "%LATEST_VERSION%"=="" (
    echo No se encontró release; consultando tags...
    curl -s https://api.github.com/repos/%REPO%/tags > "%TMP_DIR%\tags.json"
    for /f "usebackq tokens=2 delims=:\"" %%A in (`findstr /i "\"name\"" "%TMP_DIR%\tags.json" ^| findstr /v "zipball_url"`) do (
        set LATEST_VERSION=%%A
        set LATEST_VERSION=!LATEST_VERSION:~1!
        set LATEST_VERSION=!LATEST_VERSION:~0,-1!
        goto got_tag
    )
    :got_tag
)

:: Leer versión local
if exist "%VERSION_FILE%" (
    set /p LOCAL_VERSION=<"%VERSION_FILE%"
) else (
    set LOCAL_VERSION=none
)

echo Versión local: %LOCAL_VERSION%
echo Última versión: %LATEST_VERSION%
pause

:: Comparar versiones
if not "%LATEST_VERSION%"=="%LOCAL_VERSION%" (
    echo Nueva versión disponible. Actualizando...

    :: Preparar token para repositorios privados
    :: Leer token desde token.txt si existe (prioritario), sino usar GITHUB_TOKEN
    set TOKEN=
    if exist token.txt (
        rem leer primera línea y trim caracteres de retorno
        for /f "usebackq delims=" %%T in (`type token.txt ^| more +0`) do (
            set TOKEN=%%T
            goto got_token_file
        )
        :got_token_file
    ) else (
        if defined GITHUB_TOKEN set TOKEN=%GITHUB_TOKEN%
    )

    if defined TOKEN (
        echo Token de autenticación detectado (fuente: %~dp0token.txt si existe, sino variable de entorno)
    ) else (
        echo No se detectó token (ni token.txt ni variable GITHUB_TOKEN). Se intentará descarga sin autenticación y podría fallar para repositorios privados.
    )

    :: Intentar descargar asset release.zip del release (prefiere el asset)
    echo Intentando descargar asset release.zip para %LATEST_VERSION%...
    if defined TOKEN (
        curl -L -H "Authorization: token %TOKEN%" -o "%TMP_DIR%\%ZIP_NAME%" "https://github.com/%REPO%/releases/download/%LATEST_VERSION%/%ZIP_NAME%"
    ) else (
        curl -L -o "%TMP_DIR%\%ZIP_NAME%" "https://github.com/%REPO%/releases/download/%LATEST_VERSION%/%ZIP_NAME%"
    )

    :: Verificar si la descarga fue exitosa y tiene tamaño
    set FILESIZE=0
    if exist "%TMP_DIR%\%ZIP_NAME%" for %%F in ("%TMP_DIR%\%ZIP_NAME%") do set FILESIZE=%%~zF

    if "%FILESIZE%"=="0" (
        echo Asset no encontrado o vacío. Haciendo fallback a zipball del repo...
        if defined TOKEN (
            curl -L -H "Authorization: token %TOKEN%" -o "%TMP_DIR%\%ZIP_NAME%" "https://api.github.com/repos/%REPO%/zipball/%LATEST_VERSION%"
        ) else (
            curl -L -o "%TMP_DIR%\%ZIP_NAME%" "https://api.github.com/repos/%REPO%/zipball/%LATEST_VERSION%"
        )
    ) else (
        echo Asset descargado correctamente.
    )

    echo Tamaño del archivo descargado:
    if exist "%TMP_DIR%\%ZIP_NAME%" for %%F in ("%TMP_DIR%\%ZIP_NAME%") do echo %%~zF bytes
    pause

    :: Extraer y reemplazar archivos
    powershell -Command "Expand-Archive -Force '%TMP_DIR%\%ZIP_NAME%' '.'"

    echo Extracción completada. Listando archivos extraídos (primeras 200 líneas):
    dir /b | more
    pause

    :: Actualizar archivo de versión
    echo %LATEST_VERSION% > "%VERSION_FILE%"

    echo Actualización completada a la versión %LATEST_VERSION%.
) else (
    echo Ya estás en la última versión.
)

:: Limpieza
rmdir /s /q "%TMP_DIR%"
endlocal
pause
