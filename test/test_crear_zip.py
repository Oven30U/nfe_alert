import glob
import os
from datetime import datetime
import pyminizip

cliente = "cliente_test"
output_folder = "test/assets/test_output_zip"
compression_level = 5  # 1-9 (1 = fastest, 9 = best)


def crear_zip():
    now = datetime.now()
    fecha_actual = now.strftime("%Y%m%d")
    hora_actual = now.strftime("%H%M")
    zip_name = f"{cliente}_{fecha_actual}_{hora_actual}.zip"
    zip_path = os.path.join(output_folder, zip_name)
    png_files = glob.glob(os.path.join(output_folder, "*.png"))

    # Arc-names sin ruta completa para que queden en el root
    # arc_names = [os.path.basename(f) for f in png_files]

    # Comprime todos los .png en un solo zip
    # compress_multiple(srcfiles, prefixs, zipfile, password, compress_level, progress)
    pyminizip.compress_multiple(
        png_files,
        [],
        # arc_names,
        zip_path,
        "1234",  # password
        compression_level,
        # None  # progress (None if not used)
    )

    return zip_path, zip_name


if __name__ == "__main__":
    test_zip_path, test_zip_name = crear_zip()
    print(f"Archivo {test_zip_name} creado en {test_zip_path}")