# NFE Alert

## Descripción
NFE Alert es una herramienta diseñada para automatizar el procesamiento de datos de clientes y la generación de reportes relacionados con las jurisdicciones fiscales electrónicas. El sistema utiliza Playwright para la automatización de navegadores y Pandas para la manipulación de datos.

## Características principales
- Procesamiento de datos de clientes desde una base de datos o archivo de configuración.
- Automatización de tareas relacionadas con jurisdicciones fiscales.
- Generación de reportes en formato PDF y ZIP.
- Manejo de errores y reintentos automáticos.
- Registro detallado de logs para auditoría y depuración.

## Requisitos
- Python 3.11 o superior.
- Dependencias especificadas en `pyproject.toml`.
- Base de datos configurada (SQLite por defecto).
- Variables de entorno necesarias:
  - `PROCESAMIENTOS_DIARIOS`: Número de procesamientos diarios permitidos.
  - `INTERVALO_ESPERA_MINUTOS`: Intervalo de espera entre iteraciones en minutos.
  - `INPUT_DATA_FROM_DB`: Indica si los datos de entrada provienen de la base de datos (`true` o `false`).
  - `PATH_ESTRUCTURA_ROBOT`: Ruta para la estructura de respaldo.
  - `MODO_CONTINUO`: Indica si el procesamiento debe ejecutarse de forma continua (`true` o `false`).

## Instalación
1. Clona el repositorio:
   ```bash
   git clone https://github.com/AR-BPS-TaxTech/nfe_alert.git
   ```
2. Navega al directorio del proyecto:
   ```bash
   cd nfe_alert
   ```
3. Instala las dependencias:
   ```bash
   uv sync
   ```

## Uso
### Ejecución básica
Para ejecutar el procesamiento una sola vez:
```bash
python main.py
```

### Ejecución continua
Para habilitar el modo continuo, configura la variable de entorno `MODO_CONTINUO` a `true` y ejecuta:
```bash
python main.py
```

### Configuración de variables de entorno
Crea un archivo `.env` en el directorio raíz y define las variables necesarias. Ejemplo:
```
PROCESAMIENTOS_DIARIOS=3
INTERVALO_ESPERA_MINUTOS=30
INPUT_DATA_FROM_DB=true
PATH_ESTRUCTURA_ROBOT=/ruta/a/estructura_robot
MODO_CONTINUO=false
```

## Estructura del proyecto
- `main.py`: Punto de entrada principal del sistema.
- `cliente_processor.py`: Lógica para procesar clientes.
- `config.py`: Configuración del sistema.
- `logger.py`: Configuración y manejo de logs.
- `obtener_datos_clientes/`: Módulo para obtener datos de clientes.
- `functions/`: Funciones auxiliares.
- `tests/`: Pruebas unitarias y de integración.

## Pruebas
Ejecuta las pruebas con:
```bash
pytest
```

## Visualización de Traces de Playwright
Playwright genera traces en archivos ZIP durante la ejecución de pruebas o sesiones de navegador. Para visualizarlos:

1. Instala Playwright (si no está instalado): Ejecuta `pip install playwright` en tu terminal.

2. Ejecuta el comando de visualización:
   - Abre una terminal (en Windows, usa PowerShell o CMD).
   - Navega al directorio donde está el archivo de trace (e.g., `traces/`).
   - Ejecuta: `playwright show-trace <nombre-del-archivo.zip>`
     - Ejemplo: `playwright show-trace trace.zip`
   - Esto abre un visor web en tu navegador predeterminado, donde puedes reproducir la sesión paso a paso, ver capturas de pantalla, logs de red y acciones realizadas.

3. Notas:
   - Asegúrate de que el archivo de trace sea válido (generado con `context.tracing.start()` y `context.tracing.stop()` en tu código).
   - Si usas un entorno virtual, activa el venv antes de ejecutar el comando.
   - Para más detalles, consulta la [documentación oficial de Playwright](https://playwright.dev/python/docs/trace-viewer).

## Generación de Código con Playwright Codegen
Playwright Codegen es una herramienta que permite grabar interacciones con un sitio web y generar automáticamente código Python asíncrono para automatizar esas acciones. Esto es útil para crear o actualizar scripts de automatización para jurisdicciones fiscales.

### Ejemplo de uso
Para generar código:

1. Asegúrate de tener Playwright instalado en tu entorno virtual:
   ```bash
   pip install playwright
   playwright install
   ```

2. Ejecuta el comando de codegen apuntando al portal de Corrientes:
   ```bash
   playwright codegen --target=python-async https://linkalportal.com.ar/
   ```

3. Esto abrirá un navegador controlado por Playwright. Realiza las acciones que deseas automatizar en el sitio web (como iniciar sesión, navegar a secciones específicas, etc.).

4. El código generado se mostrará en la terminal. Puedes copiarlo y adaptarlo para integrar en tus scripts de jurisdicción.

5. Notas:
   - El código generado utiliza la API asíncrona de Playwright (`async`/`await`).
   - Asegúrate de manejar credenciales sensibles de manera segura (usa variables de entorno).
   - Para más opciones de codegen, consulta la [documentación oficial de Playwright](https://playwright.dev/python/docs/codegen).

## Contribuciones
1. Haz un fork del repositorio.
2. Crea una rama para tu funcionalidad o corrección de errores:
   ```bash
   git checkout -b mi-nueva-funcionalidad
   ```
3. Realiza tus cambios y haz commit:
   ```bash
   git commit -m "Agrega nueva funcionalidad"
   ```
4. Sube tus cambios:
   ```bash
   git push origin mi-nueva-funcionalidad
   ```
5. Abre un Pull Request.

## Licencia
Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.
