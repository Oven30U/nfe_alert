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

DEBUG = True
# DEBUG = False

if DEBUG:
    headless_state = False if DEBUG else True
    # headless_state = True  # Para no ver el navegador
    # headless_state = False  # Para ver el navegador
    # pass

# (debug) & (ejecutar_todos_clientes)  ≥ Todos los clientes
# (debug) & (NOT ejecutar_todos_clientes) ≥ Clientes de la lista
# (NOT debug)  ≥ Clientes Productivos
# EJECUTAR_TODOS_CLIENTES = True
EJECUTAR_TODOS_CLIENTES = False

# EJECUTAR_CLIENTES_LISTA = True
EJECUTAR_CLIENTES_LISTA = False
# Criterio de self.client_folder
clientes_si_verificar_config = [
    # "ABBVIE S.A",
    # "ADIDAS ARGENTINA S.A - ARCA",
    # "ADIDAS ARGENTINA S.A - PROVINCIALES",
    # "FACEBOOK ARGENTINA S.R.L",
    # "EDGE ARGENTINA S.R.L",
    "J&J ARGENTINA S.A",
    "JOHNSON & JOHNSON MEDICAL S.A",
    "JANSSEN CILAG FARMACEUTICA S.A",
    # "PFIZER S.R.L - ARCA",
    # "PFIZER S.R.L - PROVINCIALES",
    # "PFIZER S.R.L - SICNEA",
    # "CYANAMID DE ARGENTINA S A SUC BS AS",
    # "ULTRAGENYX ARGENTINA S.R.L",
    # "MAGNETI MARELLI CONJ.DE ESCAPE S.A",
    # "MAGNETI MARELLI REPUESTOS S.A",
]
SIN_DEBUG_EJECUTAR_LISTA = (
    False  # Dejar siempre en False, en True saltea debug y ejecuta la lista de clientes
)

# ENVIAR_CORREO_TEST = True
ENVIAR_CORREO_TEST = False
CORREO_TEST = "lmarinaro@deloitte.com"

# Criterio de self.client_folder
CLIENTES_CON_DOCUMENTACION = [
    "ABBVIE S.A",
    "ADIDAS ARGENTINA S.A - ARCA",
    "ADIDAS ARGENTINA S.A - PROVINCIALES",
    "CYANAMID DE ARGENTINA S A SUC BS AS",
    "EDGE ARGENTINA S.R.L",
    "EUROP ASSISTANCE ARGENTINA S.A",
    "FACEBOOK ARGENTINA S.R.L",
    "J&J ARGENTINA S.A",
    "JANSSEN CILAG FARMACEUTICA S.A",
    "JOHNSON & JOHNSON MEDICAL S.A",
    "MAGNETI MARELLI CONJ.DE ESCAPE S.A",
    "MAGNETI MARELLI REPUESTOS S.A",
    "PFIZER S.R.L - ARCA",
    "PFIZER S.R.L - PROVINCIALES",
    "PFIZER S.R.L - SICNEA",
    "SIMPLOT ARGENTINA S.R.L",
    "ULTRAGENYX ARGENTINA S.R.L",
    "SPOTIFY ARGENTINA S.A",
]

# Criterio de self.client_folder
CLIENTES_EXLUIR_NACIONAL_FCE = [
    "JOHNSON & JOHNSON MEDICAL S.A",
    "J&J ARGENTINA S.A",
    "JANSSEN CILAG FARMACEUTICA S.A",
]


# configurar nombres para el df_final de input.py,
# la key es el nombre del campo [Jurisdiccion] en el archivo input
# el value es el nombre de la clase de python
# También se deben importar en __init__.py
jurisdiccion_clases = {
    "Nacional": "Nacional",
    "SICNEA": "Sicnea",
    "901 CABA": "Agip",
    "902 BUENOS AIRES": "Arba",
    "903 CATAMARCA": "Catamarca",
    "904 CORDOBA": "Cordoba",
    "905 CORRIENTES": "Corrientes",
    "906 CHACO": "Chaco",
    "907 CHUBUT": "Chubut",
    "908 ENTRE RIOS": "EntreRios",
    "909 FORMOSA": "Formosa",
    "910 JUJUY": "Jujuy",
    "911 LA PAMPA": "LaPampa",
    "912 LA RIOJA": "LaRioja",
    "913 MENDOZA": "Mendoza",
    "914 MISIONES": "Misiones",
    "915 NEUQUEN": "Neuquen",
    "916 RIO NEGRO": "RioNegro",
    "917 SALTA": "Salta",
    "918 SAN JUAN": "SanJuan",
    "919 SAN LUIS": "SanLuis",
    "920 SANTA CRUZ": "SantaCruz",
    "921 SANTA FE": "SantaFe",
    "922 SANTIAGO DEL ESTERO": "SantiagoDelEstero",
    "923 TIERRA DEL FUEGO": "TierraDelFuego",
    "924 TUCUMAN": "Tucuman",
}

# configurar nombres para mapa_plot.py y la tabla en mail.py
# la key es el nombre de la clase de python
# el value es el [nombre] en el mapa provincias_argentinas.geojson
mapa_jurisdiccion_clases = {value: key for key, value in jurisdiccion_clases.items()}

link_system = "Estructura-robot/System/"

# link_clientes = f"{link_system}System-Clientes.xlsx"

# Constantes de archivos que corresponden a cada cliente
PATH_ESTRUCTURA_ROBOT = "C:/Users/lmarinaro/Documents/dfe/DFEPW/Estructura-robot"
NOMBRE_ARCHIVO_CLIENTE = "Template_input"
SHEET_ARCHIVO_CLIENTE = "Configuracion"
log_file_path = f"{PATH_ESTRUCTURA_ROBOT}/System/logfile.log"
PATH_HTML_SET_PASS = (
    R"C:/Users/lmarinaro/Documents/dfe/DFEPW/html/mail_plantilla_set_pass.html"
)

# DATABASE_URL = "mssql+pyodbc://TaxTech:T&LTechnologies@ARBAS0228/RPA/Tecnologia?driver=SQL+Server"
DATABASE_URL = "mssql+pyodbc://TaxTech:T%26LTechnologies@ARBAS0228/RPA/Tecnologia?driver=SQL+Server"

LIMITES_REINTENTO = 5
DIAS_VIGENCIA_PASS_ZIP = 90
CORREO_NOTIFICACION_ERROR = "lmarinaro@deloitte.com"

if __name__ == "__main__":
    import asyncio

    from main import main

    kwargs = {
        "debug": DEBUG,
        "enviar_correo_test": ENVIAR_CORREO_TEST,
        "ejecutar_todos_clientes": EJECUTAR_TODOS_CLIENTES,
        "ejecutar_clientes_lista": EJECUTAR_CLIENTES_LISTA,
        "sin_debug_ejecutar_lista": SIN_DEBUG_EJECUTAR_LISTA,
        "clientes_si_verificar_config": clientes_si_verificar_config,
    }

    if "headless_state" in globals():
        kwargs["headless_state"] = headless_state

    # estado_value, correo_enviado_exitosamente = asyncio.run(main(**kwargs))
    estado_value, correo_enviado_exitosamente = asyncio.run(main())

    print(
        f"Estado: {estado_value}, Correo enviado exitosamente: {correo_enviado_exitosamente}"
    )
