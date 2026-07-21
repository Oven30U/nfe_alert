# Suite de tests de NFE Alert

Esta suite se agregó **sin modificar ningún archivo de la aplicación**
(main.py, cliente_processor.py, jurisdicciones/*, etc.). Todo lo nuevo vive
en `tests/`, `pytest.ini` y `requirements-test.txt`.

## Instalación

```bash
pip install -r requirements-test.txt --break-system-packages
# o, dentro del venv del proyecto:
uv pip install -r requirements-test.txt
playwright install chromium   # sólo si no está instalado
```

## Cómo correr

```bash
# Todo menos lo lento (uso normal / CI en cada push)
pytest -m "not slow"

# Por capa
pytest -m smoke
pytest -m unit
pytest -m integration
pytest -m e2e -m "not slow"

# Los "known_issue": documentan bugs reales encontrados, no fallan (hoy)
pytest -m known_issue

# Corrida completa, incluyendo los e2e que esperan un timeout real de 60-120s
# (pensada para nightly, no para cada push)
pytest
```

`pytest.ini` ya excluye de la colección los scripts manuales viejos que
estaban en `tests/` (`test_aislado_salta.py`, `test_la_pampa.py`,
`test_manual_catamarca.py`, `test_connection.py`): no son tests automatizados
(no tienen asserts, abren un browser headed contra un sitio real, o dependen
de `DrissionPage`/`CloudflareBypasser`, que no está instalado). No se
tocaron ni se borraron, sólo se excluyen de `pytest` vía `addopts` en
`pytest.ini`.

## Estructura

```
tests/
  conftest.py                 fixtures compartidas (DB sqlite de test, env,
                               factories de DataFrames, servidor HTTP local)
  fixtures/
    portal_server.py          servidor HTTP local (ThreadingHTTPServer) que
                               sirve las páginas de tests/fixtures/html/
    html/                     páginas estáticas que simulan los 3 escenarios
                               de login (éxito / credenciales inválidas /
                               timeout-portal caído), genéricas y AFIP-like
  smoke/     imports de todos los módulos, config coherente, la app "prende"
  unit/      lógica pura (excepciones, clasificar_fallo_login, exclusión de
             reintentos), con mocks -> rápidos y sin IO
  integration/  DB SQLite real (sin mocks de SQLAlchemy), sin browser
  e2e/       Playwright real (Chromium headless) contra el servidor local
```

Ningún test pega contra un portal fiscal real ni usa credenciales reales.

---

## El pedido central: credenciales inválidas vs. timeout de portal

Pediste específicamente enfocarse en que a veces aparece "credenciales
inválidas" cuando en realidad la página estaba en timeout. Esto es lo que se
encontró y lo que cubren los tests:

### Lo que el repo ya hace bien (y ahora está cubierto por tests)

`jurisdicciones/jurisdiccion.py` ya tiene el mecanismo correcto:
`LoginTimeoutError` (NO hereda de `LoginError`) y el helper
`clasificar_fallo_login(...)`, que sólo levanta `LoginError` si encuentra un
selector de error explícito en la página; si no encuentra nada, levanta
`LoginTimeoutError`. **Sólo `mendoza.py` usa este mecanismo.**

En `cliente_processor.py`, la diferencia entre ambos tipos de error importa
en 3 lugares, y los 3 están cubiertos por tests:

| Mecanismo | LoginError / LoginErrorAfip | LoginTimeoutError |
|---|---|---|
| `reintentar_errores` | NO se reintenta | SÍ se reintenta |
| `actualizar_fecha_login_error` | Persiste `fecha_login_error` (bloquea la jurisdicción ~24hs y dispara el mensaje "Credenciales inválidas" al cliente) | NO persiste nada |
| `_hay_errores_en_resultados` | Excluido (no cuenta como error técnico) | Sí cuenta como error técnico (genera alerta operativa) |

Tests: `tests/unit/test_login_exceptions.py`,
`tests/unit/test_clasificar_fallo_login.py`,
`tests/unit/test_cliente_processor_estado.py`,
`tests/integration/test_login_error_persistence.py`.

### Bugs reales encontrados mientras se armaban los tests

No se pidió arreglarlos (y no se tocó el código), pero quedaron
documentados con tests `@pytest.mark.known_issue` para que el equipo decida
cuándo priorizarlos. Todos están verificados corriendo el código real (no
son teoría):

**1. Sólo 1 de 24 jurisdicciones usa el mecanismo correcto.**
`grep -l clasificar_fallo_login jurisdicciones/*.py` → sólo `mendoza.py`. El
resto arma su propio manejo de errores de login, con más o menos cuidado.

**2. `jurisdicciones/agip.py` (`_login_clave_ciudad`) — confirmado en vivo
con Playwright real (`tests/e2e/test_e2e_agip_known_issue.py`):**
```python
try:
    await expect(success_locator).to_be_visible(timeout=120000)
except PlaywrightTimeoutError as e:
    raise LoginError(self.cliente) from e
```
`expect(...).to_be_visible(...)` es la API de *aserciones* de Playwright:
ante un timeout levanta `AssertionError`, no `PlaywrightTimeoutError`. Ese
`except` nunca se activa — es código muerto. En la práctica, un timeout ahí
hoy escapa como un `AssertionError` genérico y sin clasificar (no como
"Credenciales inválidas", pero tampoco con un mensaje útil para
diagnosticar). Mismo patrón para chequear en cualquier otro lado del código
que combine `expect(...)` con `except PlaywrightTimeoutError`.

**3. `jurisdicciones/salta.py` y `jurisdicciones/sicnea.py` — detectado por
análisis estático (no se llegó a reproducir en vivo por tiempo, pero las
líneas son concretas):**
```
salta.py:128:  except Exception as e:  -> raise LoginErrorAfip(...)
salta.py:228:  except Exception as e:  -> raise LoginErrorAfip(...)
salta.py:252:  except Exception as e:  -> raise LoginError(...)
salta.py:279:  except Exception as e:  -> raise LoginError(...)
salta.py:369:  except Exception as e:  -> raise LoginError(..., LoginError.SERVICIO_NO_DISPONIBLE)
sicnea.py:225: except Exception as e:  -> raise LoginError(..., f"Failed to select client CUIT: {e}")
```
Un `except Exception` genérico que reempaqueta CUALQUIER error (incluyendo
un timeout de Playwright real) como `LoginError`/`LoginErrorAfip` es
exactamente el patrón que produce el síntoma que reportaste: el portal
tarda o falla técnicamente, y el sistema lo reporta como "Credenciales
inválidas". Recomendación (a futuro, no aplicada): reemplazar esos
`except Exception` puntuales por `clasificar_fallo_login(error_selectors=[...])`,
pasando el/los selectores que confirman un error de credenciales real en
cada portal.

**4. `filtrar_jurisdicciones_por_login_error` tiene un bug de
tz-naive/tz-aware, confirmado con SQLite Y reproducido manualmente con
`datetime.now()` puro (no es un artefacto del entorno de test):**
```python
# actualizar_fecha_login_error graba con datetime.now() -> NAIVE
"now": datetime.now()
...
# filtrar_jurisdicciones_por_login_error compara contra tz-aware
ahora = pd.Timestamp.now(tz='UTC')
diff = ahora - fecha_dt   # TypeError: Cannot subtract tz-naive and tz-aware datetime-like objects
```
Esa excepción queda silenciada por el `except Exception` que envuelve todo
el método. Consecuencia: el "saltear por 24hs y después reintentar solo"
nunca se ejecuta en la práctica — ni marca `Saltar=True`, ni resetea
`fecha_login_error`. Ver `tests/integration/test_login_error_persistence.py`
(clase `TestFiltrarJurisdiccionesPorLoginError`, tests `test_bug_tz_*` vs.
`test_intencion_*` con `xfail(strict=True)`, para que el día que se
corrija el bug esos tests avisen solos).

**5. (Hallazgo menor, portabilidad) `inputs.py`/`main.py` importan
`win32com.client` (pywin32) a nivel de módulo → no se pueden ni importar
fuera de Windows.** Si se quiere correr esta suite en un runner Linux de CI,
ese import debería moverse adentro de la función que realmente lo usa.

**6. (Hallazgo menor, config) `config.py` declara jurisdicciones "Santa Fe"
y "Tierra del Fuego" en `jurisdiccion_clases`, pero no existen las clases
(están documentadas como "sin DFE relevado" en `jurisdicciones/__init__.py`).
Si algún cliente llegara a tener esa jurisdicción cargada, el sistema
rompería con un `AttributeError` sin manejo específico.** Cubierto por
`tests/smoke/test_smoke_imports.py::test_todas_las_clases_de_jurisdiccion_configuradas_existen`.

---

## Notas sobre entorno para correr estos tests

- Se necesitó instalar además de `requirements-test.txt`: `pyminizip`,
  `reportlab`, `pillow`, `beautifulsoup4`/`bs4`, `matplotlib`, `geopandas`,
  `shapely`, `pyproj`, `openpyxl` (ya están en `pyproject.toml` de la app,
  simplemente no estaban instalados en este entorno de análisis).
- La DB de test es SQLite (`$TMPDIR/nfe_alert_test.db`), recreada en cada
  corrida. `obtener_datos_clientes/db.py` lee `DATABASE_URL` al importarse,
  por eso `tests/conftest.py` fija esa variable de entorno ANTES de
  cualquier import de la app.
- El logger singleton (`logger.py`) escribe a disco en el primer
  `Logger.get_logger()`; se redirige a un tmp dir vía `log_file_path` para no
  ensuciar el repo.
