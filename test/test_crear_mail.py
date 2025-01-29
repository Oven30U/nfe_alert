"""
Test manual para la función crear_zip de la clase ClienteProcessor
El objetivo es validar que el formato de los.zip sea compatible con todo extractor de archivos
"""

import glob
import os
from datetime import datetime

import pyzipper

cliente = "cliente_test"
output_folder = "test/assets/test_output_zip"

def crear_zip():
    now = datetime.now()
    fecha_actual = now.strftime("%Y%m%d")
    hora_actual = now.strftime("%H%M")
    zip_name = f"{cliente}_{fecha_actual}_{hora_actual}.zip"
    zip_path = os.path.join(output_folder, zip_name)
    png_files = glob.glob(os.path.join(output_folder, "*.png"))

    pass_zip = "1234"
    with pyzipper.ZipFile(
        zip_path,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.ZIP_CRYPTO,
    ) as zipf:
        zipf.setpassword(pass_zip.encode("utf-8"))
        for file in png_files:
            zipf.write(file, os.path.basename(file))

    return zip_path, zip_name


if __name__ == "__main__":
    zip_path, zip_name = crear_zip()
    print(f"Archivo {zip_name} creado en {zip_path}")
