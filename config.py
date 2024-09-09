"""
Este módulo `config.py` contiene configuraciones globales para el sistema.

Variables:
- `debug`: Booleano que indica si el modo debug está activado. Impacta en el comportamiento de la aplicación, como la visibilidad del navegador y la ejecución de clientes.
- `headless_state`: Booleano que determina si el navegador se ejecuta en modo headless. Depende del valor de `debug`.
- `ejecutar_todos_clientes`: Booleano que indica si se deben ejecutar todos los clientes. Utilizado en `inputs.py` para determinar la lista de clientes a verificar.
- `ejecutar_clientes_lista`: Booleano que indica si se deben ejecutar los clientes de la lista `clientes_si_verificar_config`. Utilizado en `inputs.py` para determinar la lista de clientes a verificar.
- 'sin_debug_ejecutar_lista': Booleano que indica si se deben ejecutar los clientes de la lista `clientes_si_verificar_config` sin importar el valor de `debug`. Utilizado en `inputs.py` para determinar la lista de clientes a verificar.
- `clientes_si_verificar_config`: Lista de nombres de clientes que se deben verificar si `ejecutar_clientes_lista` es `True`. Utilizado en `inputs.py` para filtrar clientes.
- `jurisdiccion_clases`: Diccionario que mapea nombres de jurisdicciones a nombres de clases de Python. Utilizado en `inputs.py` para reemplazar nombres en el DataFrame final.
- `mapa_jurisdiccion_clases`: Diccionario inverso de `jurisdiccion_clases` para el uso en `mapa_plot.py` y `mail.py`.
- `link_system`: Ruta al directorio del sistema.
- `link_clientes`: Ruta al archivo de clientes del sistema.
- `PATH_ESTRUCTURA_ROBOT`: Ruta al directorio de la estructura del robot.
- `log_file_path`: Ruta al archivo de log del sistema.
- `LIMITES_REINTENTO`: Número máximo de reintentos permitidos.
- 'enviar_correo_test': Booleano que indica si se debe enviar un correo de prueba. Utilizado en `main.py` para enviar correos de prueba.

Uso:
Estas variables son importadas y utilizadas en varios módulos del sistema, principalmente en `inputs.py` para la verificación y ejecución de clientes, y en `main.py` para la configuración general del sistema.

Ejemplo de uso:
Para ejecutar el script desde `config.py` se toman los valores de:
    debug y enviar_correo_test
Desde main.py estos dos valores son siempre False, pero desde config.py se pueden cambiar a True para probar el envío de correos y los clientes deseados. No actualiza última vez en System-Clientes.
"""

# DEBUG = True
DEBUG = False

if DEBUG:
    headless_state = False if DEBUG else True
    # headless_state = True  # Para no ver el navegador
    # headless_state = False  # Para ver el navegador

# (debug) & (ejecutar_todos_clientes)  ≥ Todos los clientes
# (debug) & (NOT ejecutar_todos_clientes) ≥ Clientes de la lista
# (NOT debug)  ≥ Clientes Productivos
# EJECUTAR_TODOS_CLIENTES = True
EJECUTAR_TODOS_CLIENTES = False

EJECUTAR_CLIENTES_LISTA = True
# EJECUTAR_CLIENTES_LISTA = False
clientes_si_verificar_config = [
    "FACEBOOK ARGENTINA S.R.L",
    "EDGE ARGENTINA S.R.L",
    # "MAGNETI MARELLI CONJ.DE ESCAPE S.A",
    # "MAGNETI MARELLI REPUESTOS S.A",
    # "NATURA COSMETICOS S.A",
    # "ABBOTT LABORATORIES ARG. S.A",
    # "SIMPLOT ARGENTINA S.R.L",
]
SIN_DEBUG_EJECUTAR_LISTA = False  # Dejar siempre en False, en True saltea debug y ejecuta la lista de clientes

# ENVIAR_CORREO_TEST = True
ENVIAR_CORREO_TEST = False
CORREO_TEST = 'lmarinaro@deloitte.com'

# configurar nombres para el df_final de input.py,
# la key es el nombre del campo [Jurisdiccion] en el archivo input
# el value es el nombre de la clase de python
# También se deben importar en __init__.py
jurisdiccion_clases = {
    "CABA": "Agip",
    "Buenos Aires": "Arba",
    "SICNEA": "Sicnea",
    "La Pampa": "LaPampa",
    "La Rioja": "LaRioja",
    "San Juan": "SanJuan",
    "San Luis": "SanLuis",
    "Santiago del Estero": "SantiagoDelEstero",
    "Entre Ríos": "EntreRios",
    "Río Negro": "RioNegro",
    "Córdoba": "Cordoba",
    "Neuquén": "Neuquen",
    "Tucumán": "Tucuman",
}

# configurar nombres para mapa_plot.py y la tabla en mail.py
# la key es el nombre de la clase de python
# el value es el [nombre] en el mapa provincias_argentinas.geojson
mapa_jurisdiccion_clases = {value: key for key, value in jurisdiccion_clases.items()}

link_system = "Estructura-robot/System/"

link_clientes = f"{link_system}System-Clientes.xlsx"

# Jurisdiccion
PATH_ESTRUCTURA_ROBOT = "C:/Users/lmarinaro/OneDrive - Deloitte (O365D)/Documents/Proyectos/test_robot_framework/dfe/Estructura-robot"
log_file_path = f"{PATH_ESTRUCTURA_ROBOT}/System/logfile.log"

LIMITES_REINTENTO = 5

if __name__ == "__main__":
    import asyncio
    from main import main

    kwargs = {
        'debug': DEBUG,
        'enviar_correo_test': ENVIAR_CORREO_TEST,
        'ejecutar_todos_clientes': EJECUTAR_TODOS_CLIENTES,
        'ejecutar_clientes_lista': EJECUTAR_CLIENTES_LISTA,
        'sin_debug_ejecutar_lista': SIN_DEBUG_EJECUTAR_LISTA,
        'clientes_si_verificar_config': clientes_si_verificar_config
    }

    if 'headless_state' in globals():
        kwargs['headless_state'] = headless_state

    estado_value, correo_enviado_exitosamente = asyncio.run(main(**kwargs))

    print(f"Estado: {estado_value}, Correo enviado exitosamente: {correo_enviado_exitosamente}")
