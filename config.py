DEBUG = True
# DEBUG = False

headless_state = False if DEBUG else True
# headless_state = True  # Para no ver el navegador
# headless_state = False  # Para ver el navegador

# (DEBUG) & (EJECUTAR_TODOS_CLIENTES)  ≥ Todos los clientes
# (DEBUG) & (NOT EJECUTAR_TODOS_CLIENTES) ≥ Clientes de la lista
# (NOT DEBUG)  ≥ Clientes Productivos
EJECUTAR_TODOS_CLIENTES = False
clientes_si_verificar_config = [
    "FACEBOOK ARGENTINA S.R.L",
    "EDGE ARGENTINA S.R.L",
    "MAGNETI MARELLI CONJ.DE ESCAPE S.A",
    "MAGNETI MARELLI REPUESTOS S.A",
    "NATURA COSMETICOS S.A",
    "ABBOTT LABORATORIES ARG. S.A",
    "SIMPLOT ARGENTINA S.R.L",
]

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
    "San Juan": "SanJuan"
}

# configurar nombres para mapa_plot.py y la tabla en mail.py
# la key es el nombre de la clase de python
# el value es el [nombre] en el mapa provincias_argentinas.geojson
# mapa_jurisdiccion_clases = {
#     "Agip": "CABA",
#     "Arba": "Buenos Aires",
#     "RioNegro": "Rio Negro",
#     "EntreRios": "Entre Rios",
#     "Sicnea": "SICNEA",
#     "RioNegro": "Rio Negro",
#     "LaPampa": "La Pampa",
#     "LaRioja": "La Rioja",
# }
mapa_jurisdiccion_clases = {value: key for key, value in jurisdiccion_clases.items()}

link_system = "Estructura-robot/System/"

link_clientes = f"{link_system}System-Clientes.xlsx"

# Jurisdiccion
PATH_ESTRUCTURA_ROBOT = "C:/Users/lmarinaro\OneDrive - Deloitte (O365D)/Documents\Proyectos/test_robot_framework/dfe/Estructura-robot"
log_file_path = f"{PATH_ESTRUCTURA_ROBOT}/System/logfile.log"

if __name__ == "__main__":
    import asyncio
    from main import main

    asyncio.run(main())
