"""
Este módulo `config.py` contiene configuraciones globales para el sistema.

Variables:
- `DEBUG`: Booleano que indica si el modo debug está activado. Impacta en el comportamiento de la aplicación, como la visibilidad del navegador y la ejecución de clientes.
- `headless_state`: Booleano que determina si el navegador se ejecuta en modo headless. Depende del valor de `DEBUG`.
- `EJECUTAR_TODOS_CLIENTES`: Booleano que indica si se deben ejecutar todos los clientes. Utilizado en `inputs.py` para determinar la lista de clientes a verificar.
- `EJECUTAR_CLIENTES_LISTA`: Booleano que indica si se deben ejecutar los clientes de la lista `clientes_si_verificar_config`. Utilizado en `inputs.py` para determinar la lista de clientes a verificar.
- `clientes_si_verificar_config`: Lista de nombres de clientes que se deben verificar si `EJECUTAR_CLIENTES_LISTA` es `True`. Utilizado en `inputs.py` para filtrar clientes.
- `jurisdiccion_clases`: Diccionario que mapea nombres de jurisdicciones a nombres de clases de Python. Utilizado en `inputs.py` para reemplazar nombres en el DataFrame final.
- `mapa_jurisdiccion_clases`: Diccionario inverso de `jurisdiccion_clases` para el uso en `mapa_plot.py` y `mail.py`.
- `link_system`: Ruta al directorio del sistema.
- `link_clientes`: Ruta al archivo de clientes del sistema.
- `PATH_ESTRUCTURA_ROBOT`: Ruta al directorio de la estructura del robot.
- `log_file_path`: Ruta al archivo de log del sistema.
- `LIMITES_REINTENTO`: Número máximo de reintentos permitidos.

Uso:
Estas variables son importadas y utilizadas en varios módulos del sistema, principalmente en `inputs.py` para la verificación y ejecución de clientes, y en `main.py` para la configuración general del sistema.

Ejemplo de uso:
Para ejecutar el script desde `config.py` se toman los valores de:
    DEBUG y ENVIAR_CORREO_TEST
Desde main.py estos dos valores son siempre False, pero desde config.py se pueden cambiar a True para probar el envío de correos y los clientes deseados. No actualiza última vez en System-Clientes.
"""

DEBUG = True
# DEBUG = False


headless_state = False if DEBUG else True
# headless_state = True  # Para no ver el navegador
# headless_state = False  # Para ver el navegador

# (DEBUG) & (EJECUTAR_TODOS_CLIENTES)  ≥ Todos los clientes
# (DEBUG) & (NOT EJECUTAR_TODOS_CLIENTES) ≥ Clientes de la lista
# (NOT DEBUG)  ≥ Clientes Productivos
EJECUTAR_TODOS_CLIENTES = True
# EJECUTAR_TODOS_CLIENTES = False

EJECUTAR_CLIENTES_LISTA = True
# EJECUTAR_CLIENTES_LISTA = False
clientes_si_verificar_config = [
    # "FACEBOOK ARGENTINA S.R.L",
    "EDGE ARGENTINA S.R.L",
    # "MAGNETI MARELLI CONJ.DE ESCAPE S.A",
    # "MAGNETI MARELLI REPUESTOS S.A",
    # "NATURA COSMETICOS S.A",
    # "ABBOTT LABORATORIES ARG. S.A",
    # "SIMPLOT ARGENTINA S.R.L",
]

ENVIAR_CORREO_TEST = True
# ENVIAR_CORREO_TEST = False
CORREO_TEST = 'lmarinaro@deloitte.com'

# configurar nombres para el df_final de input.py,
# la key es el nombre del campo [Jurisdiccion] en el archivo input
# el value es el nombre de la clase de python
# También se deben importar en __init__.py
jurisdiccion_clases = {
      "CABA": "Agip",
    "Buenos Aires": "Arba",
    "Rio Negro": "RioNegro",
    "Entre Rios": "EntreRios",
    "SICNEA": "Sicnea",
    "Rio Negro": "RioNegro",
    "La Pampa": "LaPampa",
    "La Rioja": "LaRioja",
    "San Juan": "SanJuan",
    "San Luis": "SanLuis",
    "Santiago del Estero": "SantiagoDelEstero",
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

LIMITES_REINTENTO = 15

if __name__ == "__main__":
    import asyncio
    from main import main

    asyncio.run(main(DEBUG=DEBUG, ENVIAR_CORREO_TEST=ENVIAR_CORREO_TEST, headless_state=headless_state))
