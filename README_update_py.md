# Script de Actualización en Python (update.py)

Este script replica la funcionalidad del `update.ps1` en Python, permitiendo descargar e instalar automáticamente la última versión de NFE Alert desde GitHub releases.

## Características

- ✅ Utiliza `GITHUB_TOKEN` para autenticación con GitHub
- ✅ Verifica si hay nuevos releases disponibles
- ✅ Descarga archivos ZIP desde releases
- ✅ Verifica checksums SHA256 (si están disponibles)
- ✅ Extrae archivos reemplazando los existentes
- ✅ Mantiene registro de versión instalada
- ✅ Genera logs detallados con fecha y hora
- ✅ Soporte para repositorios públicos y privados
- ✅ Manejo de errores robusto

## Requisitos

- Python 3.7+
- Biblioteca `requests` (ya incluida en requirements.txt)
- Token de GitHub para repositorios privados

## Configuración

### Token de GitHub

El script necesita un token de GitHub para acceder a repositorios privados. Puedes configurarlo de dos maneras:

1. **Variable de entorno:**
   ```bash
   export GITHUB_TOKEN=tu_token_aqui
   ```

2. **Archivo .env:**
   ```
   GITHUB_TOKEN=tu_token_aqui
   ```

### Crear un token de GitHub

1. Ve a GitHub → Settings → Developer settings → Personal access tokens
2. Genera un nuevo token con permisos de lectura en repositorios
3. Copia el token y configúralo como se indica arriba

## Uso

### Uso básico
```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert
```

### Opciones disponibles
```bash
python update.py --help
```

### Ejemplos de uso

#### Actualización estándar
```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose
```

#### Directorio personalizado
```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --target /ruta/personalizada
```

#### Forzar reinstalación
```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --force
```

#### Versión específica
```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --tag v1.2.0
```

#### Patrones personalizados
```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert \
    --zip-pattern "app*.zip" \
    --sha-pattern "app*.sha256"
```

## Funcionamiento

El script sigue estos pasos:

1. **Autenticación**: Lee el token desde variables de entorno o archivo .env
2. **Obtener release**: Consulta la API de GitHub para obtener el release especificado
3. **Verificar versión**: Compara con la versión instalada localmente
4. **Descargar assets**: Descarga el archivo ZIP y SHA256 (si existe)
5. **Verificar integridad**: Valida el checksum SHA256
6. **Extraer e instalar**: Extrae el ZIP y reemplaza archivos existentes
7. **Guardar versión**: Registra la nueva versión instalada
8. **Logging**: Guarda un log detallado de todas las operaciones

## Archivos generados

- **Directorio destino**: Por defecto `~/NFE_Alert` o el especificado con `--target`
- **Archivo de versión**: `.nfe_release_tag` en el directorio destino
- **Logs**: `logs/update-YYYYMMDD-HHMMSS.log`

## Comparación con update.ps1

| Característica | update.ps1 | update.py |
|----------------|------------|-----------|
| Autenticación GitHub | ✅ | ✅ |
| Descarga de releases | ✅ | ✅ |
| Verificación SHA256 | ✅ | ✅ |
| Extracción ZIP | ✅ | ✅ |
| Control de versiones | ✅ | ✅ |
| Logging detallado | ✅ | ✅ |
| Multiplataforma | ❌ (Windows) | ✅ (Python) |
| Dependencias | PowerShell + robocopy | Python + requests |

## Script de ejemplo

Se incluye `example_update.py` que demuestra el uso del script con una interfaz simple.

```bash
python example_update.py
```

## Resolución de problemas

### Error 403 (Forbidden)
- Verifica que el token de GitHub sea válido
- Asegúrate de que el token tenga permisos suficientes
- Para repositorios públicos, el script debería funcionar sin token

### Error de conexión
- Verifica tu conexión a internet
- Comprueba que no haya firewall bloqueando el acceso

### Error de extracción
- Verifica que tengas permisos de escritura en el directorio destino
- Asegúrate de que no haya archivos en uso que no se puedan reemplazar

### Logging
Todos los errores se registran en `logs/update-YYYYMMDD-HHMMSS.log` con información detallada para depuración.

## Desarrollo y pruebas

Para probar el script sin afectar tu instalación:

```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert \
    --target /tmp/test_install --verbose --force
```

## Automatización

Puedes automatizar las actualizaciones usando cron (Linux/macOS) o Task Scheduler (Windows):

```bash
# Ejemplo de cron job (diario a las 02:00)
0 2 * * * cd /ruta/a/nfe_alert && python update.py --owner AR-BPS-TaxTech --repo nfe_alert
```