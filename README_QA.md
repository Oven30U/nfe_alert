# Suite QA propuesta para NFE Alert

Esta carpeta agrega únicamente pruebas y configuración de pytest. No modifica
archivos productivos.

## Objetivo principal

Validar que el sistema diferencie correctamente:

1. Credenciales realmente inválidas.
2. Timeout de Playwright o portal sin respuesta.
3. Servicio caído o error técnico.
4. Falta de delegación.
5. Error de login de ARCA/AFIP.

El riesgo detectado en AGIP es que `_login_clave_ciudad()` captura un timeout
esperando la pantalla de éxito y lo transforma en `LoginError`, cuyo mensaje
por defecto es `Credenciales inválidas`. Después, `ClienteProcessor` evita el
reintento y puede guardar `fecha_login_error`. Esto puede bloquear ejecuciones
posteriores aunque las credenciales sean correctas.

## Instalación

Copiar en la raíz de `nfe_alert`:

- `pytest.ini`
- carpeta `tests/`

Dependencias:

```powershell
python -m pip install pytest pytest-asyncio pytest-cov pytest-html
python -m playwright install chromium
```

## Comandos

Smoke:

```powershell
python -m pytest -m smoke -v
```

Unitarios:

```powershell
python -m pytest -m unit -v
```

Integración:

```powershell
python -m pytest -m integration -v
```

Todo excepto E2E real:

```powershell
python -m pytest -m "not live" -v
```

Defectos conocidos:

```powershell
python -m pytest -m known_issue -v
```

Cobertura:

```powershell
python -m pytest -m "unit or integration" `
  --cov=jurisdicciones `
  --cov=cliente_processor `
  --cov-report=term-missing `
  --cov-report=html
```

Reporte HTML:

```powershell
python -m pytest -m "not live" `
  --html=reports/qa_report.html `
  --self-contained-html
```

## E2E real

Los E2E reales están deshabilitados por defecto. Requieren autorización,
conectividad, una cuenta QA y variables de entorno:

```powershell
$env:RUN_LIVE_E2E="true"
$env:E2E_AGIP_INVALID_CUIT="..."
$env:E2E_AGIP_INVALID_PASSWORD="..."
$env:E2E_AGIP_CUIT_CLIENTE="..."
python -m pytest -m "e2e and credentials" -v
```

Para probar timeout debe inducirse desde un ambiente controlado:

```powershell
$env:RUN_LIVE_E2E="true"
$env:E2E_FORCE_AGIP_TIMEOUT="true"
$env:E2E_AGIP_VALID_CUIT="..."
$env:E2E_AGIP_VALID_PASSWORD="..."
$env:E2E_AGIP_CUIT_CLIENTE="..."
python -m pytest -m "e2e and timeout" -v
```

No guardar credenciales en el repositorio, fixtures ni reportes.

## Interpretación QA

- `PASSED`: comportamiento confirmado.
- `FAILED`: regresión o incumplimiento.
- `XFAIL`: defecto conocido reproducido y documentado.
- `XPASS`: el defecto conocido dejó de reproducirse; revisar si fue corregido.
- `SKIPPED`: precondición externa no disponible.
- Error de colección: suite bloqueada, no equivale a test funcional fallido.

Los tests no importan `LoginTimeoutError`, porque esa excepción no forma parte
del contrato actual de `jurisdicciones.jurisdiccion`.
