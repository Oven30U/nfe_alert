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
