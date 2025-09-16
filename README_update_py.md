<<<<<<< HEAD
# Python Update Script for NFE Alert

This document describes the Python implementation of the update script (`update.py`), which is a reimplementation of the original PowerShell script (`update.ps1`) with improved portability and flexibility.

## Overview

The Python update script automates the download and installation of NFE Alert releases from GitHub. It provides the same functionality as the PowerShell version but with cross-platform compatibility and improved error handling.

## Features

- **Cross-platform compatibility**: Works on Windows, Linux, and macOS
- **GitHub API integration**: Fetches releases using GitHub's REST API
- **Authentication support**: Supports GitHub tokens for private repositories
- **SHA256 verification**: Verifies download integrity when SHA256 files are available
- **Incremental updates**: Only updates when a new version is available
- **Flexible configuration**: Customizable patterns, directories, and options
- **Comprehensive logging**: Detailed logging with verbose mode support

## Requirements

- Python 3.6 or higher
- `requests` library (usually included in Python installations)
- Internet connection for GitHub API access

## Installation

No special installation is required. The script uses only standard Python libraries and `requests`, which is commonly available.

```bash
# Make the script executable (Unix-like systems)
chmod +x update.py
```

## Usage

### Basic Usage

```bash
# Update from the latest release
python update.py --owner AR-BPS-TaxTech --repo nfe_alert

# Update to a specific tag
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --channel-tag v1.2.3

# Update with custom target directory
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --target /path/to/installation
```

### Advanced Usage

```bash
# Force reinstallation even if up to date
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --force

# Enable verbose logging
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose

# Custom asset patterns
python update.py --owner AR-BPS-TaxTech --repo nfe_alert \
    --zip-name-pattern "custom*.zip" \
    --sha-name-pattern "custom*.sha256"

# Keep temporary files for debugging
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --no-cleanup
```

## Command-Line Arguments

| Argument | Description | Default | Required |
|----------|-------------|---------|----------|
| `--owner` | GitHub repository owner | - | Yes |
| `--repo` | GitHub repository name | - | Yes |
| `--channel-tag` | Release tag to install | `latest` | No |
| `--target` | Target directory for installation | `~/NFE_Alert` | No |
| `--zip-name-pattern` | Pattern to match ZIP asset names | `nfe_alert*.zip` | No |
| `--sha-name-pattern` | Pattern to match SHA256 asset names | `nfe_alert*.zip.sha256` | No |
| `--temp-root` | Root directory for temporary files | System temp | No |
| `--no-cleanup` | Do not clean up temporary files | False | No |
| `--force` | Force reinstallation | False | No |
| `--verbose`, `-v` | Enable verbose logging | False | No |

## Authentication

The script supports GitHub authentication for accessing private repositories or avoiding rate limits.

### Environment Variables

Set one of these environment variables:

```bash
export GITHUB_TOKEN="your_token_here"
# or
export GITHUB_PAT_NFE_UY="your_token_here"
```

### .env File

Create a `.env` file in the script directory or current working directory:

```env
GITHUB_TOKEN=your_token_here
```

The script will automatically detect and use the token. Tokens in `.env` files take precedence over environment variables.

## File Structure

After installation, the target directory will contain:

```
target_directory/
├── .nfe_release_tag          # Version tracking file
├── (extracted release files)
└── ...
```

The `.nfe_release_tag` file contains the currently installed version tag and is used to avoid unnecessary reinstallations.

## Error Handling

The script includes comprehensive error handling for common scenarios:

- **Network errors**: Graceful handling of API failures with informative messages
- **Authentication errors**: Clear messages for token-related issues
- **File system errors**: Proper handling of permission and disk space issues
- **SHA256 mismatches**: Automatic cleanup and clear error reporting

## Logging

The script provides detailed logging at different levels:

- **INFO**: Basic progress information
- **DEBUG**: Detailed operation information (enabled with `--verbose`)
- **ERROR**: Error messages with optional stack traces

## Comparison with PowerShell Version

| Feature | PowerShell | Python | Notes |
|---------|------------|--------|-------|
| Cross-platform | Windows only | All platforms | Python version works everywhere |
| Dependencies | Windows, PowerShell | Python 3.6+ | Minimal requirements |
| Authentication | .env + env vars | .env + env vars | Same mechanism |
| SHA256 verification | Yes | Yes | Same functionality |
| Robocopy equivalent | Robocopy | shutil | Platform-appropriate file operations |
| Error handling | Basic | Comprehensive | Improved error messages |
| Logging | Write-Host | Python logging | Structured logging |

## Examples

### Example 1: Basic Update

```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose
```

Output:
```
2023-XX-XX XX:XX:XX,XXX - INFO - Starting NFE Alert update process...
2023-XX-XX XX:XX:XX,XXX - INFO - Found release: v1.2.3
2023-XX-XX XX:XX:XX,XXX - DEBUG - Found ZIP asset: nfe_alert_v1.2.3.zip
2023-XX-XX XX:XX:XX,XXX - DEBUG - Found SHA256 asset: nfe_alert_v1.2.3.zip.sha256
2023-XX-XX XX:XX:XX,XXX - INFO - Update completed: v1.2.3 → /home/user/NFE_Alert
```

### Example 2: Custom Configuration

```bash
python update.py \
    --owner AR-BPS-TaxTech \
    --repo nfe_alert \
    --channel-tag v1.1.0 \
    --target /opt/nfe_alert \
    --force \
    --verbose
```

### Example 3: With Authentication

```bash
# Set token
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Run update
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose
```

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Likely a private repository or rate limiting
   - Solution: Set up GitHub authentication

2. **No ZIP asset found**: Asset naming doesn't match the pattern
   - Solution: Use custom `--zip-name-pattern`

3. **SHA256 mismatch**: Download corruption or incorrect SHA file
   - Solution: Check network connection and retry

4. **Permission denied**: Insufficient permissions for target directory
   - Solution: Run with appropriate permissions or change target

### Debug Mode

Use `--verbose` to get detailed information about the update process:

```bash
python update.py --owner AR-BPS-TaxTech --repo nfe_alert --verbose
```

## Security Considerations

- Store GitHub tokens securely
- Verify SHA256 checksums when available
- Use HTTPS for all GitHub API communications
- Clean up temporary files after installation

## Migration from PowerShell

To migrate from the PowerShell version:

1. Install Python 3.6+ if not already available
2. Use the same command-line arguments (with Python syntax)
3. Same authentication mechanism (`.env` files and environment variables)
4. Same directory structure and version tracking

The Python version is a drop-in replacement for most use cases.
=======
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
>>>>>>> 9c1c4c59f68c0824cc804a32da7bdc1780085b93
