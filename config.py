from typing import Dict

jurisdiccion_clases: Dict[str, str] = {
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
