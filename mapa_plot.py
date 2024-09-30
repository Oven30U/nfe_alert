import geopandas as gpd
import matplotlib.image as mpimg
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

from config import mapa_jurisdiccion_clases


def crear_mapa(df, output_file):

    # Cargar el archivo de geodatos de las provincias de Argentina
    provincias = gpd.read_file("src/provincias_argentinas.geojson")

    # Unir el GeoDataFrame con el DataFrame
    # Cambia "nombre" por "Nombre" en df.set_index
    df["Nombre"] = df["Nombre"].replace(mapa_jurisdiccion_clases)
    merged = provincias.set_index("nombre").join(df.set_index("Nombre"))

    # Reemplazar NaN con False en la columna 'Error'
    # merged["Error"].fillna(False, inplace=True)
    #! // merged["Error"].replace({None: False}, inplace=True)
    #! // merged["Error"] = merged["Error"].replace({None: False})
    merged["Error"] = merged["Error"].replace({None: False}).infer_objects(copy=False)

    # Mapear los valores de string a booleanos
    # merged["Notificaciones"] = (merged["Notificaciones"].map({"Hay notificaciones": True}).fillna(False))
    # Map "Hay notificaciones" to True, fill NA with False and infer objects
    merged["Notificacion"] = (
        merged["Notificacion"]
        .map({"Hay notificaciones": True})
        .fillna(False)
        .infer_objects(copy=False)
    )

    # merged["Screenshot"] = (merged["Screenshot"].map({"Se realizó Screenshot": True}).fillna(False))
    merged["Screenshot"] = (
        merged["Screenshot"]
        .map({"Se realizó Screenshot": True})
        .fillna(False)
        .infer_objects(copy=False)
    )
    # Reemplazar None con False
    # merged["Notificaciones"].replace({None: False}, inplace=True)
    merged["Notificacion"] = merged["Notificacion"].replace({None: False})

    merged["color"] = np.where(
        merged["Error"],
        "#000000",
        np.where(
            (merged["Notificacion"] == False) & (merged["Screenshot"] == False),
            "#D0D0CE",
            np.where(
                merged["Notificacion"] & merged["Screenshot"],
                "#62B5E5",
                np.where(
                    merged["Notificacion"] == False & merged["Screenshot"],
                    "#86BC25",
                    "#53565A",
                ),
            ),
        ),
    )

    # Crear el gráfico de mapa
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    merged.plot(color=merged["color"], ax=ax)

    # Crear un diccionario de colores con los valores de orden correspondientes
    color_order = {"#62B5E5": 1, "#86BC25": 2, "#D0D0CE": 3, "#53565A": 4, "#000000": 5}

    # Crear una nueva columna con los valores de orden
    merged["color_order"] = merged["color"].map(color_order)

    # Ordenar el DataFrame por la columna 'color_order'
    merged = merged.sort_values(by="color_order")

    # Crear elementos de leyenda para el DataFrame
    df_legend_elements = [
        mpatches.Patch(color=row["color"], label=f"{index}")
        for index, row in merged.iterrows()
        if row["Notificacion"] or row["Screenshot"] or row["Error"]
    ]

    # Crear la segunda leyenda
    df_legend = plt.legend(
        handles=df_legend_elements,
        loc="lower right",
        bbox_to_anchor=(1, 0.1),
        prop={"size": 6},
    )

    # Agregar la segunda leyenda al plot
    ax.add_artist(df_legend)

    # Crear un LegendElement para cada color
    legend_elements = [
        mpatches.Patch(color="#62B5E5", label="Notificaciones y Screenshot"),
        mpatches.Patch(color="#86BC25", label="Sin notificaciones, Screenshot"),
        mpatches.Patch(color="#D0D0CE", label="No consultada"),
        mpatches.Patch(color="#53565A", label="Notificaciones, sin Screenshot"),
        mpatches.Patch(color="#000000", label="Error"),
    ]

    # Agregar la leyenda de colores al plot
    legend = ax.legend(
        handles=legend_elements,
        loc="lower right",
        bbox_to_anchor=(1, 0),
        prop={"size": 6},
    )
    ax.add_artist(legend)

    # Cargar la imagen
    img = mpimg.imread("src/deloitte_black.jpg")

    # Crear un OffsetImage, sin bordes
    imagebox = OffsetImage(img, zoom=0.1)

    # Crear una AnnotationBbox
    ab = AnnotationBbox(
        imagebox,
        (0, 1),
        box_alignment=(0, 0),
        xycoords="axes fraction",
        boxcoords="offset points",
        pad=0,
        frameon=False,
    )

    # Agregar la AnnotationBbox al plot
    ax.add_artist(ab)

    # Centrar el mapa
    minx, miny, maxx, maxy = merged.total_bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    # quita los ejes
    ax.axis("off")

    # Guardar el gráfico como una imagen
    plt.savefig(output_file, bbox_extra_artists=(legend, df_legend))
    # plt.savefig(
    # output_file, bbox_extra_artists=(legend, df_legend), bbox_inches="tight"
    # )


def crear_mapa_argentina(df, output_file):

    # Crear una copia del DataFrame antes de modificarlo
    df_nacional = df[df["Nombre"] == "Nacional"].copy()

    # Convertir las columnas a booleanos
    df_nacional["Notificacion"] = (
        df_nacional["Notificacion"] == "Hay notificaciones"
    )
    df_nacional["Screenshot"] = df_nacional["Screenshot"] == "Se realizó Screenshot"

    # Reemplazar NaN con False en la columna 'Error'
    # df_nacional["Error"].fillna(False, inplace=True)
    # //df_nacional["Error"].replace({None: False}, inplace=True)
    # df_nacional["Error"].replace({None: False}, inplace=True)
    df_nacional["Error"] = df_nacional["Error"].replace({None: False})

    # Todo reemplazar para evitar advertencia
    # df_nacional["Error"] = df_nacional["Error"].astype('boolean')
    # df_nacional["Error"].fillna(False, inplace=True)

    # Asignar colores
    df_nacional["color"] = np.where(
        df_nacional["Error"],
        "#000000",
        np.where(
            (~df_nacional["Notificacion"]) & (~df_nacional["Screenshot"]),
            "#D0D0CE",
            np.where(
                df_nacional["Notificacion"] & df_nacional["Screenshot"],
                "#62B5E5",
                np.where(
                    (~df_nacional["Notificacion"]) & df_nacional["Screenshot"],
                    "#86BC25",
                    "#53565A",
                ),
            ),
        ),
    )

    # Read the geojson file
    gdf = gpd.read_file("src/argentina.geo.json")

    # Get the color for 'Nacional' from df_nacional
    # color = df_nacional.loc[df_nacional["Nombre"] == "Nacional", "color"].iloc[0]
    color = (
        df_nacional.loc[df_nacional["Nombre"] == "Nacional", "color"].iloc[0]
        if not df_nacional.loc[df_nacional["Nombre"] == "Nacional", "color"].empty
        else "#D0D0CE"
    )

    # Crear el gráfico de mapa
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    gdf.plot(color=color, ax=ax)

    # Crear un LegendElement para cada color
    legend_elements = [
        mpatches.Patch(color="#62B5E5", label="Notificaciones y Screenshot"),
        mpatches.Patch(color="#86BC25", label="Sin notificaciones, Screenshot"),
        mpatches.Patch(color="#D0D0CE", label="No consultada"),
        mpatches.Patch(color="#53565A", label="Notificaciones, sin Screenshot"),
        mpatches.Patch(color="#000000", label="Observaciones"),
    ]

    # Agregar la leyenda de colores al plot
    legend = ax.legend(
        handles=legend_elements,
        loc="lower right",
        bbox_to_anchor=(1, 0),
        prop={"size": 6},
    )
    ax.add_artist(legend)

    # Crear un diccionario de colores con los valores de orden correspondientes
    color_order = {"#62B5E5": 1, "#86BC25": 2, "#D0D0CE": 3, "#53565A": 4, "#000000": 5}

    # Crear una nueva columna con los valores de orden
    df_nacional["color_order"] = df_nacional["color"].map(color_order)

    # Ordenar el DataFrame por la columna 'color_order'
    df_nacional = df_nacional.sort_values(by="color_order")

    # Crear elementos de leyenda para el DataFrame
    df_legend_elements = [mpatches.Patch(color=color, label="Nacional")]

    # Crear la segunda leyenda
    df_legend = plt.legend(
        handles=df_legend_elements,
        loc="lower right",
        bbox_to_anchor=(1, 0.1),
        prop={"size": 6},
    )

    # Agregar la segunda leyenda al plot
    ax.add_artist(df_legend)

    # Cargar la imagen
    img = mpimg.imread("src/deloitte_black.jpg")

    # Crear un OffsetImage, sin bordes
    imagebox = OffsetImage(img, zoom=0.1)

    # Crear una AnnotationBbox
    ab = AnnotationBbox(
        imagebox,
        (0, 1),
        box_alignment=(0, 0),
        xycoords="axes fraction",
        boxcoords="offset points",
        pad=0,
        frameon=False,
    )

    # Agregar la AnnotationBbox al plot
    ax.add_artist(ab)

    # quita los ejes
    ax.axis("off")

    # plt.show()
    # Guardar el gráfico como una imagen
    plt.savefig(output_file, bbox_extra_artists=(legend, df_legend))


# #Todo - En lugar de esto reemplazar los merges de df's en mapas
# merged["Error"].fillna(False, inplace=True)

# # Haz esto
# merged["Error"] = merged["Error"].fillna(False)

# # Y en lugar de esto
# merged["Notificaciones"].replace({None: False}, inplace=True)

# # Haz esto
# merged["Notificaciones"] = merged["Notificaciones"].replace({None: False})
