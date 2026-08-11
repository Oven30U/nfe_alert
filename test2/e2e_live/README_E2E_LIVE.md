# E2E vivo — login real contra los 24 portales fiscales

⚠️ **Esta suite pega contra portales reales de AFIP/ARCA y rentas provinciales, con
credenciales reales de clientes reales.** No es una suite para CI. Es para correr
manualmente, a propósito, cuando querés verificar que las credenciales cargadas siguen
sirviendo o que el login de una jurisdicción puntual sigue funcionando contra el sitio real.

## Por qué no la corrí yo

No ejecuté ni un solo test de esta carpeta contra los portales reales. Corrí únicamente:
validación de sintaxis, la carga del `.xlsm` (sin imprimir usuario/password en ningún
momento), y un dry-run con la clase `Agip` mockeada (sin red real) para confirmar que el
armado de argumentos, el llamado a `procesar_jurisdiccion()` y el registro de resultados
funcionan de punta a punta. Ejecutar logins reales contra 24 portales de gobierno con
credenciales de producción, desde una máquina que esos portales no reconocen como el origen
habitual del robot, es un riesgo real de bloqueo de cuenta / alerta de fraude que le
corresponde asumir a quien opera el sistema, no a un análisis automatizado corriendo desde
un entorno de terceros. Corré esto desde tu propia infraestructura (la misma desde la que
corre el robot en producción, o una lo más parecida posible).

## Qué falta que completes vos

**El `.xlsm` no tiene columna `cuit_cliente`** (el CUIT del contribuyente a consultar,
distinto del CUIT de login cuando quien loguea es un estudio contable delegado — es el caso
de AGIP vía MiBA y probablemente ARBA). Sin ese dato, el test asume por defecto
`cuit_cliente_input = usuario` con un aviso en pantalla, lo cual **puede ser incorrecto**
para esas jurisdicciones. Si lo tenés, pasalo así:

```bash
export CUIT_CLIENTE_OVERRIDES_JSON='{"Agip": "30xxxxxxxxx", "Arba": "30xxxxxxxxx"}'
```

Sólo hace falta para las jurisdicciones donde el usuario que loguea no es el mismo
contribuyente que se quiere consultar. Si no estás seguro, correlo primero para 1-2
jurisdicciones y revisá el `hay_notificacion`/screenshot resultante antes de asumir que
está bien para las 24.

## Setup

```bash
# 1. Nunca subas el .xlsm a git. Agregalo a .gitignore si no está.
echo "*.xlsm" >> .gitignore   # si ya tenés reglas de xlsx, revisá que esto no choque

# 2. Variables de entorno obligatorias
export RUN_LIVE_E2E=true
export PATH_CREDENCIALES_XLSM="/ruta/absoluta/a/NFE_Alert_-_Mapeo_de_Credenciales_para_Test.xlsm"

# 3. Opcionales
export HEADLESS_E2E_LIVE=true        # false para ver el browser (debug puntual)
export CUIT_CLIENTE_OVERRIDES_JSON='{"Agip": "..."}'   # ver arriba
```

## Cómo correr

```bash
# TODAS las jurisdicciones (24, uso poco frecuente / manual, tarda varios minutos)
pytest tests/e2e_live/ -v

# Una sola jurisdicción puntual (lo más común: verificar que una credencial sigue viva)
pytest tests/e2e_live/ -v -k Agip

# Varias puntuales
pytest tests/e2e_live/ -v -k "Agip or Arba or Nacional"
```

Sin `RUN_LIVE_E2E=true`, **todo** se skipea automáticamente (incluso si corrés `pytest`
a secas desde la raíz y esta carpeta queda incluida sin querer).

## Qué valida cada test, en detalle

Por cada jurisdicción con credenciales en el `.xlsm`:

1. Instancia la clase real (`jurisdicciones.<Clase>`) con Playwright real, headless por defecto.
2. Corre el flujo real y completo tal como lo ejecuta producción:
   login → `consultar_notificaciones()` → `buscar_notificacion()` → `tomar_screenshot()` →
   cierre de navegador — todo esto ya encapsulado en
   `Jurisdiccion.procesar_jurisdiccion()`, sin reinventar ninguna lógica de scraping.
3. **Assert duro (hace fallar el test):** el portal no debe rechazar las credenciales
   (`LoginError` / `LoginErrorAfip`). Esta es la señal más importante que te puede dar esta
   suite: "¿esta credencial todavía sirve?".
4. **No hace fallar el test** (se reporta, no se bloquea la corrida): errores técnicos
   tolerados como portal caído, selector cambiado, timeout de screenshot
   (`ConsultarNotificacionesError`, `BuscarNotificacionError`, `TomarScreenshotError`,
   `DelegacionError`) — son ruido esperable de un e2e contra sitios reales de gobierno.
5. Al final de la corrida completa, se escribe `tests/e2e_live/REPORTE_ULTIMA_CORRIDA.md`
   con una tabla: jurisdicción, resultado, tipo de error, si hubo notificación, si se tomó
   screenshot, duración. **Ese archivo tampoco contiene credenciales**, sólo resultados.

## Por qué NO envía mails

Esta suite nunca instancia `ClienteProcessor` ni llama `enviar_email`/`enviar_correo`: sólo
ejercita `Jurisdiccion.procesar_jurisdiccion()`, que ni siquiera tiene acceso a esa lógica.
Como cinturón de seguridad adicional, `conftest.py` parchea `smtplib.SMTP`/`SMTP_SSL` y
`mail.enviar_correo` para que exploten si algo los llegara a invocar por error.

## Manejo de las credenciales — reglas que sigue este código

- El `.xlsm` se lee en tiempo de ejecución desde la ruta de `PATH_CREDENCIALES_XLSM`, nunca
  hardcodeada en el código.
- Ningún test, fixture ni log imprime usuario/password. El reporte final
  (`REPORTE_ULTIMA_CORRIDA.md`) sólo tiene resultados, no credenciales.
- Recomendación fuerte: el `.xlsm` no debería vivir en el repo ni en ningún sistema sin
  control de acceso — considerá moverlo a un vault/secret manager si esta suite se va a usar
  de forma recurrente, y dejar sólo la ruta (o una referencia) en la variable de entorno.

## Riesgos operativos a tener en cuenta

- **Rate limiting / bloqueo de cuenta:** correr las 24 jurisdicciones seguidas es 24 logins
  reales en poco tiempo. Si notás CAPTCHAs o bloqueos temporales después de correr esto,
  espaciá las corridas (`-k` para subconjuntos) en vez de correr todo junto muy seguido.
  El propio código ya modela `LoginError.CAPTCHA_DETECTADO` para AFIP — si aparece, es una
  señal de que el portal está viendo esto como tráfico sospechoso.
- **No la metas en un pipeline de CI/CD automático.** Es exactamente lo que este README
  intenta evitar con el gating de `RUN_LIVE_E2E`.
- **Ventana de fechas chica a propósito:** `rango_fechas` en `conftest.py` usa los últimos 7
  días para minimizar la carga de la consulta sobre cada portal.
