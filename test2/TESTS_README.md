# test2 — Suite de tests de NFE Alert (proyecto completo)

Esta carpeta es una suite de tests **independiente del código de la app**
(no modifica nada dentro de `jurisdicciones/`, `cliente_processor.py`, etc.).
Cubre el **proyecto completo**, no sólo las 3 jurisdicciones que tuvieron un
fix reciente (Agip, Nacional, Sicnea): smoke-tests de importación para los
~25 módulos core y las 24 jurisdicciones implementadas, tests unitarios de
la capa de excepciones y de cada jurisdicción "de riesgo", un test
parametrizado que audita las 24 jurisdicciones de una sola vez, y tests de
integración de `ClienteProcessor` contra una DB SQLite real (no mockeada).

## Cómo correrla

No hay script wrapper (`.bat`/`.sh`) porque muchos entornos corporativos
bloquean ejecutar `.bat`. Son 3 comandos directos, parado adentro de
`test2/` (en la terminal de VS Code o la que uses):

```bat
pip install -r requirements-test.txt
mkdir ..\reports 2>nul
pytest -v --html=..\reports\reporte_resultados.html --self-contained-html
```

(en Linux/Mac: `mkdir -p ../reports` en vez de `mkdir ..\reports 2>nul`,
y `--html=../reports/reporte_resultados.html`).

El primer comando instala `pytest`/`pytest-asyncio`/`pytest-html` (ver
`requirements-test.txt`). El reporte queda en
`../reports/reporte_resultados.html` — es decir, en una carpeta `reports/`
hermana de `test2/` (la raíz del checkout de `nfe_alert`), no adentro de
`test2/`. Es autocontenido: se puede mandar por mail o abrir con doble
click, con el detalle de cada test, agrupado y con buscador. Si tu
checkout guarda los reportes en otro lado, apuntá el `--html=...` a esa
ruta directamente.

**Requisito previo:** el entorno de la app (`nfe_alert`) ya tiene que estar
instalado (SQLAlchemy, pandas, Playwright, python-dotenv, etc. — ver
`pyproject.toml`/`uv.lock` de la app). Si no lo está, desde la carpeta
`nfe_alert/` correspondiente: `uv sync` o `pip install -e .`.

Para correr un subconjunto puntual, agregá al final del comando `pytest`:

```bat
-k Agip              REM sólo tests relacionados a Agip
-m known_issue       REM sólo los que documentan bugs conocidos
-m "not known_issue" REM todo MENOS los bugs conocidos
```

## Qué NO corre por defecto

`e2e_live/` pega contra los portales reales de AFIP/ARCA y de cada
jurisdicción provincial, con credenciales reales de clientes. Está
deshabilitada salvo `RUN_LIVE_E2E=true` (ver `e2e_live/README_E2E_LIVE.md`).
**No la actives desde una corrida automática/CI.**

## Estructura

```
test2/
├── conftest.py          # DB de test (SQLite), fixtures compartidas, resuelve
│                         # qué checkout de nfe_alert testear
├── pytest.ini            # markers registrados, testpaths, asyncio_mode
├── requirements-test.txt # pytest, pytest-asyncio, pytest-html
├── smoke/                 # ¿arranca la app? ¿importan todos los módulos?
├── unit/                  # exceptiones, Agip/Nacional/Salta/Sicnea/Neuquen,
│                           # ClienteProcessor, y el test parametrizado que
│                           # cubre las 24 jurisdicciones de una sola vez
├── integration/            # DB real (SQLite) + ClienteProcessor end-to-end
└── e2e_live/                # portales reales, manual, apagado por defecto
```

## Cómo se elige qué copia de nfe_alert testear

Este repo llegó con 3 carpetas (`Agip/`, `Nacional/`, `Sicena/`) que son 3
checkouts **idénticos** del mismo código (mismo `git log`, mismo working
tree — se verificó con `diff -r`, sin diferencias). `test2/conftest.py`
detecta automáticamente el primero que encuentre al lado suyo y lo usa. Si
tenés un layout distinto o querés forzar uno puntual:

```bash
export NFE_ALERT_REPO_ROOT=/ruta/absoluta/a/Nacional/nfe_alert
```

## Bugs reales que esta suite ya documenta (para el dev)

Estos hallazgos surgen de leer el código real de la app contra lo que la
suite ejercita — no son suposiciones. Están marcados en el código de los
tests con `@pytest.mark.known_issue` y, la mayoría, con
`xfail(strict=True)` (el test pasa hoy documentando el bug; el día que se
corrija en la app, ese mismo test empieza a fallar el xfail y hay que
"promoverlo" a test normal).

1. **🔴 Prioridad alta — no es xfail, va a aparecer en ROJO al correr la suite:**
   `jurisdicciones/agip.py`, método `_login`: `raise LoginError from e` le
   falta el argumento obligatorio `cliente`. Cuando fallan tanto "Clave
   Ciudad" como "MiBA", en vez de reportar prolijamente "Credenciales
   inválidas", el proceso revienta con
   `TypeError: LoginError.__init__() missing 1 required positional argument: 'cliente'`.
   Test: `integration/test_agip_login_fallback.py::test_login_lanza_error_si_ambos_metodos_fallan`.
   Fix sugerido: `raise LoginError(self.cliente) from e`.

2. **Timeout de portal informado como "credenciales inválidas"** en Agip,
   Salta, Sicnea y Neuquen: cuando ni el mensaje de error ni el selector de
   éxito aparecen a tiempo (timeout ambiguo), el código de esas 4
   jurisdicciones asume por descarte que son credenciales inválidas. Esto
   hace que un cliente reciba "actualizá tus credenciales" por un simple
   problema de portal caído/lento. Tests dedicados:
   `unit/test_agip_login.py`, `unit/test_salta_timeout_vs_credenciales.py`,
   `unit/test_sicnea_timeout_vs_credenciales.py`,
   `unit/test_neuquen_timeout_vs_credenciales.py`.

3. **`jurisdicciones/sicnea.py::_select_cuit_from_dropdown`**: `DelegacionError`
   no hereda de `LoginError`, así que el `except LoginError: raise` de ese
   método no la atrapa: un `DelegacionError` legítimo (CUIT no delegado)
   también se reempaqueta como `LoginError`, perdiendo la distinción entre
   "no está delegado" y "credenciales inválidas".

4. **`jurisdicciones/nacional.py::_seleccionar_cuit_cliente`**: no hay
   ninguna verificación posterior al click que confirme que ARCA cambió
   efectivamente al CUIT esperado — sólo se confía en que el click funcionó.
   Relacionado al incidente real reportado ("Dolar App ingresó pero se
   quedó con el CUIT de la persona en lugar de la empresa").

5. **Bug de timezone en `cliente_processor.py::filtrar_jurisdicciones_por_login_error`**:
   compara un `datetime` naive (guardado por `actualizar_fecha_login_error`)
   contra uno timezone-aware, lo cual lanza `TypeError` — silenciado por un
   `except Exception` genérico que envuelve todo el método. Efecto
   práctico: el "saltear la jurisdicción por 24hs tras un error de login" y
   el "resetear automáticamente pasadas las 24hs" **no funcionan hoy**,
   aunque el docstring del método los prometa.

Ver `COBERTURA_TIMEOUT_VS_CREDENCIALES.md` para el detalle jurisdicción por
jurisdicción del punto 2.

## Estado de esta entrega

Esta suite fue revisada línea por línea contra el código real de la app
(cada aserción de cada test contra el archivo fuente correspondiente) pero
**no se pudo ejecutar con pytest en este momento** por falta de acceso a
red para instalar dependencias en el entorno donde se preparó esta
entrega. Corré los 3 comandos de la sección "Cómo correrla" para obtener el
`reporte_resultados.html` real con el resultado pass/fail de cada test —
en base a la revisión manual, se espera que la mayoría pase, que los
`known_issue` marcados `xfail(strict=True)` sigan en verde (documentando
los bugs de arriba), y que
`test_login_lanza_error_si_ambos_metodos_fallan` aparezca en rojo (bug #1)
hasta que se corrija `agip.py`.

## Notas operativas confirmadas en corridas reales (Windows, Agip/Nacional/Sicena)

- **No agregues `test2/__init__.py`** (los de `unit/`, `integration/`, `smoke/`, `e2e_live/` sí van, no los toques). Si `test2/` tiene su propio `__init__.py`, pytest intenta importar `conftest.py` como parte de un paquete que incluye el nombre de la carpeta del checkout (ej. `nfe_alert_Nacional.test2.conftest`), lo cual explota con `ModuleNotFoundError: No module named 'nfe_alert_Nacional'` porque esa carpeta no está pensada para importarse como paquete Python.
- Corré pytest apuntando explícitamente a la carpeta, no a secas: `pytest test2 -v --html=reports\reporte_resultados.html --self-contained-html` (parado en la raíz del checkout). Así carga `test2\pytest.ini` correctamente y no colecciona los scripts viejos sueltos del repo (`test_manuales.py`, `tests\test_connection.py`), que no son tests de pytest y tiran `ERROR` de fixture faltante si se cuelan.
- Si instalás `pytest-asyncio` desde `requirements-test.txt` y tenés otro paquete que pide una versión más nueva (ej. `taxteclib>=1.2.0`), corré después `pip install "pytest-asyncio>=1.2.0"` para que quede en una versión que le sirva a ambos.
- `$env:RUN_LIVE_E2E` y `$env:PATH_CREDENCIALES_XLSM` quedan seteados mientras no cierres la terminal de PowerShell — hacé `Remove-Item Env:\RUN_LIVE_E2E -ErrorAction SilentlyContinue` antes de una corrida que no debería incluir `e2e_live`, para no confundir qué contiene cada reporte.
- Confirmado en las 3 ramas (Agip/Nacional/Sicena, que son checkouts idénticos): **103-104 passed en la suite mockeada** (1 failed = bug real de `agip.py::_login`, 4 xfailed = known issues documentados) y, contra los portales reales (`e2e_live`), **125+ passed / 2 failed** (Sicnea y Salta, ambos por bugs ya documentados en este archivo). Si en algún momento una rama te da un resultado distinto a las otras, es señal de que se desincronizaron — investigalo.
