import glob
import os

import winshell


def delete_zip_files_in_backup(directory):
    for root, _, _ in os.walk(directory):
        if os.path.basename(root) == "Backup":
            zip_files = glob.glob(os.path.join(root, "*.zip"))
            for zip_file in zip_files:
                try:
                    os.remove(zip_file)
                except Exception as e:
                    print(f"Error deleting {zip_file}: {e}")


def delete_all_files_in_output(directory):
    for root, _, files in os.walk(directory):
        if os.path.basename(root) == "Output":
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    # print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")


def empty_recycle_bin():
    try:
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        print("Papelera de reciclaje vacia")
    except Exception as e:
        print(f"Error vaciando la papelera: {e}")


if __name__ == '__main__':
    directory_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\Estructura-robot"
    test_path = r"C:\Users\lmarinaro\OneDrive - Deloitte (O365D)\Documents\Proyectos\test_robot_framework\dfe\jurisdicciones\Estructura-robot"
    delete_zip_files_in_backup(directory_path)
    delete_all_files_in_output(directory_path)
    delete_all_files_in_output(test_path)
    empty_recycle_bin()
    print("Archivos eliminados")
