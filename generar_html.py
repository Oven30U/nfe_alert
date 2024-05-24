from string import Template
import os

# from os.path import abspath
import base64
from bs4 import BeautifulSoup
from datetime import datetime


def limpiar_codigo_html(html):

    # Crear un objeto BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Formatear el HTML y eliminar los caracteres de nueva línea
    formatted_html = soup.prettify().replace("\n", "")

    return formatted_html


def convertir_imagen_en_html(image_path):
    # Leer la imagen y convertirla en base64
    with open(image_path, "rb") as image_file:
        encoded_string_img = base64.b64encode(image_file.read()).decode()

    # Usar la cadena base64 como la URL de la imagen en el HTML, por ejemplo src="data:image/png;base64,encoded_string"
    html_content_img = f"data:image/png;base64,{encoded_string_img}"
    return html_content_img


def insertar_tabla_en_html(dataframe, html_plantilla_path, tipo_selector, selector):
    # Convertir el DataFrame a HTML
    df_html = dataframe.to_html(index=False)

    # Crear un objeto BeautifulSoup con el HTML del DataFrame
    soup_df = BeautifulSoup(df_html, "html.parser")

    # Leer el archivo HTML en un objeto BeautifulSoup
    with open(html_plantilla_path, "r", encoding="utf-8") as f:
        contents = f.read()

    soup = BeautifulSoup(contents, "html.parser")

    # Buscar la tabla en el objeto BeautifulSoup original
    table = soup.find("table", {tipo_selector: selector})

    # Get all rows in the table
    rows = table.find_all("tr")

    # If the DataFrame has more rows than the HTML table, add new rows
    if len(dataframe) > len(rows) - 1:  # Subtract 1 because the first row is the header
        for _ in range(len(dataframe) - len(rows) + 1):
            new_row = BeautifulSoup(
                '<tr style="height:17.0pt">'
                + '<td style="width:112.5pt;border:none;border-bottom:solid windowtext 1.0pt;background:#000;padding:0cm 0cm 0cm 0cm;height:17.0pt" width="150"></td>'
                * len(rows[0].find_all("td"))
                + "</tr>",
                "html.parser",
            )
            table.tbody.append(new_row)

    # Reemplazar el contenido de las celdas de la tabla con los datos del DataFrame
    for i, row in enumerate(table.find_all("tr")):
        columns = row.find_all("td")
        if i > 0 and i <= len(dataframe):  # Ignorar la fila de encabezados
            for j, column in enumerate(columns):
                # if j > 0:  # Ignorar la primera columna
                # column.string = dataframe.iloc[i - 1, j - 1]
                column.string = dataframe.iloc[i - 1, j]

                # Comprobar el contenido de las columnas "Notificaciones" y "Screenshot"
                notificaciones = dataframe.iloc[
                    i - 1, dataframe.columns.get_loc("Notificaciones")
                ]
                screenshot = dataframe.iloc[
                    i - 1, dataframe.columns.get_loc("Screenshot")
                ]

                # Establecer el color de fondo en función del contenido de las columnas
                if (
                    "Hay notificaciones" in notificaciones
                    and "Se realizó Screenshot" in screenshot
                ):
                    color = "#62B5E5"  # Notificaciones y Screenshot
                elif (
                    "No hay notificaciones" in notificaciones
                    and "Se realizó Screenshot" in screenshot
                ):
                    color = "#86BC25"  # Sin notificaciones, Screenshot
                elif (
                    "No hay notificaciones" in notificaciones
                    and "No se realizó Screenshot" in screenshot
                ):
                    color = "#D0D0CE"  # No consultada
                elif (
                    "Hay notificaciones" in notificaciones
                    and "No se realizó Screenshot" in screenshot
                ):
                    color = "#53565A"  # Notificaciones, sin Screenshot
                else:
                    color = "#000000"  # Error

                # Replace the background color in the style attribute
                style = column.get("style")
                style = style.replace("background:#000", f"background:{color}")
                column["style"] = style

    # Escribir el contenido del objeto BeautifulSoup de vuelta al archivo HTML
    # with open(html_salida, "w", encoding="utf-8") as f:
    #     f.write(str(soup))

    # Convert the BeautifulSoup object back to a string
    html_modified = str(soup)

    # Return the modified HTML
    return html_modified


def insertar_mapas_en_html(var_imagen_html, var_imagen_html_2, html_plantilla):
    # Leer el archivo HTML
    # with open("html/base_mail.html", "r", encoding="utf-8") as f:
    # with open("html/mail_plantilla.html", "r", encoding="utf-8") as f:
    # with open(html_plantilla, "r", encoding="utf-8") as f:
    #     html_str = f.read()

    # Convertir las rutas de las imágenes a rutas absolutas
    # ruta_imagen_png = abspath(ruta_imagen_png)
    # ruta_imagen_png_2 = abspath(ruta_imagen_png_2)
    # html_mapa_1 = convertir_imagen_en_html(ruta_imagen_png)
    # html_mapa_2 = convertir_imagen_en_html(ruta_imagen_png_2)
    html_plantilla_limpia = limpiar_codigo_html(html_plantilla)
    html_template = Template(html_plantilla_limpia)

    # Marcadores de posición con los valores a reemplazar
    html = html_template.substitute(
        mapa_provincias=var_imagen_html,
        mapa_argentina=var_imagen_html_2,
        # deloitte_logo=abspath("src/deloitte_logo_mail.jpg"),
    )

    # Guardar el HTML final en un archivo
    # with open("Estructura-robot/final_mail.html", "w", encoding="utf-8") as f:
    # with open(html_salida, "w", encoding="utf-8") as f:
    #     f.write(html)

    return html


def reemplazar_contenido_en_html(
    html_input, selector_type, selector_id, nuevo_contenido
):
    # Leer el documento HTML y crear un objeto de BeatifulSoup
    # with open(html_input, "r", encoding="utf-8") as f:
    #     soup = BeautifulSoup(f.read(), "html.parser")

    soup = BeautifulSoup(html_input, "html.parser")

    # Crear el localizador en base al tipo de selector y el identificador del selector
    if selector_type == "id":
        locator = f"#{selector_id}"
    elif selector_type == "class":
        locator = f".{selector_id}"
    else:
        locator = selector_id  # Para los selectores de tipo 'tag', el identificador es suficiente

    # Encontrar un elemento en base al localizador
    element = soup.select_one(locator)

    # Reemplazar el contenido del elemento con el nuevo contenido
    if element:
        element.string = nuevo_contenido
    else:
        print(f"No hay elementos con: {locator}")

    # Write the modified HTML back to the file
    # with open(html_input, "w", encoding="utf-8") as f:
    #     f.write(str(soup))

    # Convert the BeautifulSoup object back to a string
    html_modified = str(soup)

    # Return the modified HTML
    return html_modified


def grabar_html(cliente, cadena_html):
    # Get the current date
    fecha = datetime.today().strftime("%Y%m%d")

    # Create the directory path
    dir_path = os.path.join("Estructura-robot", cliente, "output")

    # Create the directory if it doesn't exist
    os.makedirs(dir_path, exist_ok=True)

    # Create the file name
    html_file_name = f"{cliente}_{fecha}.html"
    html_file_path = os.path.join(dir_path, html_file_name)

    # Write the HTML content to the file
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(cadena_html)

    return html_file_path
